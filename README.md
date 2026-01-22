# 🍼 Baby Monitor: AI Gesture-Based Caregiving Logger

A cross-platform monitoring tool that uses computer vision to log baby care activities. By making specific hand gestures in front of the camera, caregivers can trigger instant logs, local audio feedback, and remote push notifications to multiple **Bark** accounts.

---

## ✨ Key Features

- **⚡ High Performance**: Built with `uv` and multi-threading. AI inference and camera capture run independently for zero lag.
- **🎯 Smart Recognition**: Detects 4 specific gestures with area-threshold filtering to prevent false positives from background movement.
- **🔇 Background Optimized**: Designed for 24/7 use with 10 FPS throttling to keep CPU usage and temperature low on devices like MacBook Air.
- **🔔 Multi-Channel Feedback**:
  - **Local**: Instant audio confirmation (macOS `afplay` / Windows `pygame`).
  - **Remote**: Push notifications to multiple iOS devices via Bark.
- **🔒 Privacy Minded**: All AI processing is local. Secrets are stored in `.env`.

---

## 🛠️ Quick Start

### 1. Prerequisite: Install `uv`

If you don't have the `uv` package manager yet:

- **macOS/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

### 2. Automatic Setup

Run the setup script for your platform to download the AI model and sync dependencies:

- **macOS**: `chmod +x setup.sh && ./setup.sh`
- **Windows**: Run `setup.ps1` in PowerShell.

---

## 🔍 Camera Configuration

If you have multiple cameras (built-in vs. USB), use the utility script to find the correct index:

```bash
uv run check_camera.py

```

After identifying the index, update `main.py`:

```python
self.cap = cv2.VideoCapture(YOUR_INDEX)

```

---

## ⚙️ Configuration (.env)

Edit the `.env` file in the project root:

- `BARK_KEYS`: Add your Bark device keys (comma-separated for multiple users).
- `APP_ENV`:
- `DEV`: Shows detailed debug info (hand area, raw AI output).
- `PROD`: Clean logs, optimized for daily background use.

---

## 🖐️ Gesture Reference

| Gesture | Action | Example Notification |
| --- | --- | --- |
| **Thumb_Up (👍)** | **Nursing** | `2026-01-22 15:30 🍼Feeding` |
| **Victory (✌️)** | **Diaper Change** | `2026-01-22 15:35 💩Diaper` |
| **Closed_Fist (✊)** | **Baby Asleep** | `2026-01-22 15:40 😴Sleeping` |
| **Open_Palm (🖐️)** | **Baby Awake** | `2026-01-22 15:45 👀Awake` |

---

## 🚀 Running the System

### Production Mode (Recommended)

Minimal logs, best for daily use:

- **macOS**: `APP_ENV=PROD uv run main.py`
- **Windows**: `$env:APP_ENV="PROD"; uv run main.py`

### Debug Mode

To calibrate hand area thresholds:

```bash
uv run main.py

```

---

## 📂 File Structure

- `main.py`: The heart of the system (AI & Logic).
- `check_camera.py`: Camera diagnostic tool.
- `pyproject.toml`: Project dependency manifest.
- `gesture_recognizer.task`: MediaPipe AI Model (auto-downloaded).
- `success.m4a`: Audio feedback file.
