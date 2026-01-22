#!/bin/bash

# Exit on any error
set -e

echo "------------------------------------------------"
echo "👶 Baby Monitor: AI System Setup (macOS/Linux)"
echo "------------------------------------------------"

# 1. Check for uv
if ! command -v uv &>/dev/null; then
    echo "🔍 uv not found. Installing the modern Python manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
else
    echo "✅ uv is already installed."
fi

# 2. Sync environment based on pyproject.toml
echo "📦 Syncing project dependencies..."
uv sync

# 3. Download the Gesture Recognition Model
MODEL_FILE="gesture_recognizer.task"
if [ ! -f "$MODEL_FILE" ]; then
    echo "🤖 Downloading AI model (MediaPipe)..."
    curl -L -o $MODEL_FILE "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
else
    echo "✅ AI model file already exists."
fi

# 4. Initialize .env file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    echo "BARK_KEYS=your_key_1,your_key_2" >.env
    echo "APP_ENV=DEV" >>.env
    echo "⚠️  ACTION REQUIRED: Please edit the .env file and add your Bark API keys."
else
    echo "✅ .env file already exists."
fi

echo "------------------------------------------------"
echo "🎉 Setup complete!"
echo "🚀 Run the app with: uv run main.py"
echo "------------------------------------------------"
