import cv2
import mediapipe as mp
import threading
import time
import os
import sys
import logging
import httpx
import platform
import subprocess  # Added for native system calls
from queue import Queue, Empty
from collections import deque, Counter
from urllib.parse import quote
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ================= Configuration =================
_raw_keys = os.getenv("BARK_KEYS", "")
BARK_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]

CAMERA_INDEX = 1  # Update based on check_camera.py results
MODEL_FILENAME = "gesture_recognizer.task"
AUDIO_FILENAME = "success.mp3"

AREA_THRESHOLD = 0.15  # Minimum hand area to trigger
WINDOW_SIZE = 8         # Number of frames for stability window
TARGET_FPS = 10         # Frame rate limit for camera capture

GESTURE_MAP = {
    "Closed_Fist": "😴Sleeping",
    "Open_Palm": "👀Awake",
    "Thumb_Up": "🍼Feeding",
    "Victory": "💩Diaper",
}
# =================================================

def setup_logger():
    """Initialize logger based on LOG_LEVEL in .env"""
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level_str, logging.INFO)
    logger = logging.getLogger("BabyMonitor")

    if level <= logging.DEBUG:
        log_format = "%(asctime)s [%(levelname)s] [%(threadName)s] %(filename)s:%(lineno)d - %(message)s"
    else:
        log_format = "%(asctime)s [%(levelname)s] %(message)s"

    logging.basicConfig(level=level, format=log_format, datefmt="%H:%M:%S")
    logger.info(f"Logger initialized with level: {log_level_str}")
    return logger

logger = setup_logger()

class BabyMonitorApp:
    def __init__(self):
        self.running = True
        self.frame_queue = Queue(maxsize=1)
        self.active_state = "None"
        self.window = deque(maxlen=WINDOW_SIZE)
        self.system = platform.system()

        self.http_client = httpx.Client(timeout=5.0)
        self.cap = cv2.VideoCapture(CAMERA_INDEX)

        # Setup audio path
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.audio_path = os.path.join(base_path, AUDIO_FILENAME)

        if not os.path.exists(self.audio_path):
            logger.warning(f"⚠️ Audio file not found: {self.audio_path}")

        # Initialize MediaPipe Gesture Recognizer
        self.model_path = os.path.join(base_path, MODEL_FILENAME)
        if not os.path.exists(self.model_path):
            logger.critical(f"Missing model file: {self.model_path}")
            sys.exit(1)

        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
        )
        self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)

    def _play_audio_async(self):
        """Plays audio using native system commands to avoid SDL conflicts"""
        def _play():
            if not os.path.exists(self.audio_path):
                return

            try:
                if self.system == "Darwin":  # macOS
                    # afplay is built-in and supports mp3/m4a
                    subprocess.run(["afplay", self.audio_path], check=True)
                elif self.system == "Windows": # Windows
                    # Use PowerShell for native audio playback
                    ps_cmd = f"(New-Object System.Media.SoundPlayer '{self.audio_path}').PlaySync()"
                    subprocess.run(["powershell", "-c", ps_cmd], check=True, capture_output=True)
            except Exception as e:
                logger.error(f"❌ Native audio playback failed: {e}")

        # Run in a separate thread to prevent blocking AI inference
        threading.Thread(target=_play, daemon=True).start()

    def _push_to_bark(self, title, content):
        """Asynchronous multi-account push notifications via Bark"""
        def _send():
            if not BARK_KEYS:
                logger.warning("⚠️ BARK_KEYS is empty. Skipping notification.")
                return

            safe_title, safe_content = quote(title), quote(content)

            for key in BARK_KEYS:
                short_key = f"{key[:5]}***"
                start_time = time.perf_counter()

                try:
                    url = f"https://api.day.app/{key}/{safe_title}/{safe_content}"
                    logger.debug(f"🌐 [Push] Requesting {short_key}...")

                    response = self.http_client.get(
                        url, params={"group": "BabyMonitor", "isArchive": 1}
                    )
                    latency = (time.perf_counter() - start_time) * 1000

                    if response.status_code == 200:
                        logger.info(f"🚀 Push sent to {short_key} (Status: 200)")
                        logger.debug(f"⏱️ Latency: {latency:.2f}ms")
                    else:
                        logger.error(f"❌ Push failed for {short_key} | Status: {response.status_code}")
                except Exception as e:
                    logger.error(f"⚠️ Push Error ({short_key}): {type(e).__name__}")

        threading.Thread(target=_send, daemon=True).start()

    def _camera_worker(self):
        """Thread for camera frame acquisition (throttled to TARGET_FPS)"""
        interval = 1.0 / TARGET_FPS
        while self.running:
            start = time.time()
            ret, frame = self.cap.read()
            if ret:
                # Keep only the most recent frame
                if not self.frame_queue.empty():
                    try: self.frame_queue.get_nowait()
                    except Empty: pass
                self.frame_queue.put(frame)
            time.sleep(max(0, interval - (time.time() - start)))

    def _inference_worker(self):
        """Thread for AI gesture recognition logic"""
        logger.info(f"🧠 System running on {self.system}. Push accounts: {len(BARK_KEYS)}")
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1.0)
            except Empty:
                continue

            # Convert frame for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = self.recognizer.recognize(mp_image)

            raw_res = "None"
            if result.gestures and result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                x_coords = [lm.x for lm in landmarks]
                y_coords = [lm.y for lm in landmarks]
                area = (max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords))

                logger.debug(f"AI Detected: {result.gestures[0][0].category_name}, Area: {area:.4f}")

                if area > AREA_THRESHOLD:
                    raw_res = result.gestures[0][0].category_name

            # Debouncing logic using a stability window
            self.window.append(raw_res)
            if len(self.window) == WINDOW_SIZE:
                most_common, count = Counter(self.window).most_common(1)[0]
                stable_now = most_common if count >= WINDOW_SIZE * 0.75 else "None"

                if stable_now in GESTURE_MAP and stable_now != self.active_state:
                    self.active_state = stable_now
                    now_str = time.strftime("%Y-%m-%d %H:%M")
                    full_msg = f"{now_str} {GESTURE_MAP[stable_now]}"

                    logger.info(f"✅ Event: {full_msg}")
                    self._play_audio_async()
                    self._push_to_bark("Baby Care Record", full_msg)
                elif stable_now == "None":
                    self.active_state = "None"

    def cleanup(self):
        """Release resources and shut down threads"""
        self.running = False
        logger.info("Shutting down system...")
        self.http_client.close()
        if self.cap.isOpened():
            self.cap.release()
        if self.recognizer:
            self.recognizer.close()
        logger.info("👋 System exited safely.")

    def run(self):
        """Start worker threads and wait for interruption"""
        threading.Thread(target=self._camera_worker, name="CamThread", daemon=True).start()
        threading.Thread(target=self._inference_worker, name="AIThread", daemon=True).start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()

if __name__ == "__main__":
    app = BabyMonitorApp()
    app.run()
