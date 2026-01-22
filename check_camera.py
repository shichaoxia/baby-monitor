import cv2
import sys


def check_cameras(max_to_test=5):
    print("------------------------------------------")
    print("🔍 Scanning for available camera devices...")
    print(
        "Tip: Click on the window and press 'q' to exit the current camera preview and proceed to the next test."
    )
    print("------------------------------------------")

    available_indices = []

    for index in range(max_to_test):
        cap = cv2.VideoCapture(index)

        # Some optimization settings for Windows
        if sys.platform == "win32":
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

        if cap.isOpened():
            # Try to read a frame to confirm the device is not just "on" but also "streaming"
            ret, frame = cap.read()
            if ret:
                available_indices.append(index)
                print(f"✅ Index [{index}]: Device available.")

                # Pop up a window to display the feed
                window_name = f"Camera Index {index} - Press 'q' to next"
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Annotate the index number on the frame
                    cv2.putText(
                        frame,
                        f"Index: {index}",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2,
                    )

                    cv2.imshow(window_name, frame)

                    # Press 'q' to exit the current preview
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                cv2.destroyWindow(window_name)
            else:
                print(f"⚠️ Index [{index}]: Device is on but cannot capture frames.")

            cap.release()
        else:
            print(f"❌ Index [{index}]: Device not found.")

    print("------------------------------------------")
    if available_indices:
        print(f"🎉 Scan finished. Recommended indices are: {available_indices}")
        print(
            "Please change cv2.VideoCapture(index) in main.py to your selected number."
        )
    else:
        print("🚨 No available cameras found. Please check permissions or connections.")
    print("------------------------------------------")


if __name__ == "__main__":
    check_cameras()
