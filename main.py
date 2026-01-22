import cv2
import mediapipe as mp
import threading
import time
import os
import sys
import logging
import subprocess
import platform
import httpx
from queue import Queue, Empty
from collections import deque, Counter
from urllib.parse import quote
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ================= Configuration =================
_raw_keys = os.getenv("BARK_KEYS", "")
BARK_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]

MODEL_FILENAME = "gesture_recognizer.task"
AUDIO_FILENAME = "success.m4a"

AREA_THRESHOLD = 0.15
WINDOW_SIZE = 8
TARGET_FPS = 10

GESTURE_MAP = {
    "Closed_Fist": "😴Sleeping",
    "Open_Palm": "👀aWake",
    "Thumb_Up": "🍼Feeding",
    "Victory": "💩Diaper",
}
# ==========================================


def setup_logger():
    mode = os.getenv("APP_ENV", "DEV").upper()
    logger = logging.getLogger("BabyMonitor")
    level = logging.INFO if mode == "PROD" else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logger


logger = setup_logger()


class BabyMonitorApp:
    def __init__(self):
        self.running = True
        self.frame_queue = Queue(maxsize=1)
        self.active_state = "None"
        self.window = deque(maxlen=WINDOW_SIZE)
        self.system = platform.system()  # Get system name: 'Darwin' (Mac) or 'Windows'

        self.http_client = httpx.Client(timeout=5.0)
        self.cap = cv2.VideoCapture(0)

        # If on Windows, initialize the pygame audio engine
        if self.system == "Windows":
            os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
            from pygame import mixer

            self.mixer = mixer
            self.mixer.init()
            logger.debug("Windows audio engine (pygame) is ready")

        base_path = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(base_path, MODEL_FILENAME)
        self.audio_path = os.path.join(base_path, AUDIO_FILENAME)

        # Initialize MediaPipe
        if not os.path.exists(self.model_path):
            logger.critical(f"Missing model file: {self.model_path}")
            sys.exit(1)

        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
        )
        self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)

    def _play_audio_async(self):
        """Cross-platform asynchronous audio playback logic"""

        def _play():
            if not os.path.exists(self.audio_path):
                logger.warning(f"Audio file not found: {self.audio_path}")
                return

            try:
                if self.system == "Darwin":  # macOS
                    subprocess.run(["afplay", self.audio_path])
                elif self.system == "Windows":  # Windows
                    sound = self.mixer.Sound(self.audio_path)
                    sound.play()
                else:
                    logger.warning(
                        f"Audio playback is not supported on the current system {self.system}"
                    )
            except Exception as e:
                logger.error(f"Playback failed: {e}")

        threading.Thread(target=_play, daemon=True).start()

    def _push_to_bark(self, title, content):
        def _send():
            if not BARK_KEYS:
                return
            safe_title, safe_content = quote(title), quote(content)
            for key in BARK_KEYS:
                try:
                    url = f"https://api.day.app/{key}/{safe_title}/{safe_content}"
                    self.http_client.get(
                        url, params={"group": "BabyMonitor", "isArchive": 1}
                    )
                except Exception as e:
                    logger.error(f"Push to {key[:5]}*** failed: {e}")

        threading.Thread(target=_send, daemon=True).start()

    def _camera_worker(self):
        interval = 1.0 / TARGET_FPS
        while self.running:
            start = time.time()
            ret, frame = self.cap.read()
            if ret:
                if not self.frame_queue.empty():
                    self.frame_queue.get_nowait()
                self.frame_queue.put(frame)
            # Dynamically sleep to maintain frame rate
            time.sleep(max(0, interval - (time.time() - start)))

    def _inference_worker(self):
        logger.info(f"🚀 System started on {self.system} (accounts: {len(BARK_KEYS)})")
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1.0)
            except Empty:
                continue

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
            )
            result = self.recognizer.recognize(mp_image)

            raw_res = "None"
            if result.gestures and result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                x_c = [lm.x for lm in landmarks]
                y_c = [lm.y for lm in landmarks]
                area = (max(x_c) - min(x_c)) * (max(y_c) - min(y_c))

                logger.debug(
                    f"AI Detection: {result.gestures[0][0].category_name}, Area: {area:.4f}"
                )

                if area > AREA_THRESHOLD:
                    raw_res = result.gestures[0][0].category_name

            self.window.append(raw_res)
            if len(self.window) == WINDOW_SIZE:
                most_common, count = Counter(self.window).most_common(1)[0]
                stable_now = most_common if count >= WINDOW_SIZE * 0.75 else "None"

                if stable_now in GESTURE_MAP and stable_now != self.active_state:
                    self.active_state = stable_now
                    now_str = time.strftime("%Y-%m-%d %H:%M")
                    full_msg = f"{now_str} {GESTURE_MAP[stable_now]}"

                    logger.info(f"✅ {full_msg}")
                    self._play_audio_async()
                    self._push_to_bark("Baby Care Record", full_msg)
                elif stable_now == "None":
                    self.active_state = "None"

    def cleanup(self):
        self.running = False
        logger.info("Shutting down system...")
        self.http_client.close()
        if self.cap.isOpened():
            self.cap.release()
        if self.recognizer:
            self.recognizer.close()
        if self.system == "Windows":
            self.mixer.quit()
        logger.info("👋 Exited safely.")

    def run(self):
        threading.Thread(
            target=self._camera_worker, name="CamThread", daemon=True
        ).start()
        threading.Thread(
            target=self._inference_worker, name="AIThread", daemon=True
        ).start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()


if __name__ == "__main__":
    BabyMonitorApp().run()
