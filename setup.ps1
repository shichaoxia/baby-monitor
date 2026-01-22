
Write-Host "------------------------------------------------" -ForegroundColor Cyan
Write-Host "👶 Baby Monitor: AI System Setup (Windows)" -ForegroundColor Cyan
Write-Host "------------------------------------------------" -ForegroundColor Cyan

# 1. Check for uv
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "🔍 uv not found. Installing..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
} else {
    Write-Host "✅ uv is already installed."
}

# 2. Sync dependencies
Write-Host "📦 Syncing project dependencies..." -ForegroundColor Gray
uv sync

# 3. Download the AI model
$ModelFile = "gesture_recognizer.task"
if (!(Test-Path $ModelFile)) {
    Write-Host "🤖 Downloading AI model..." -ForegroundColor Gray
    Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task" -OutFile $ModelFile
} else {
    Write-Host "✅ AI model file already exists."
}

# 4. Initialize .env file
if (!(Test-Path ".env")) {
    "BARK_KEYS=your_key_1,your_key_2`nAPP_ENV=DEV" | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "📝 .env template created."
    Write-Host "⚠️  ACTION REQUIRED: Edit the .env file to add your Bark API keys." -ForegroundColor Yellow
} else {
    Write-Host "✅ .env file already exists."
}

Write-Host "------------------------------------------------" -ForegroundColor Green
Write-Host "🎉 Setup complete! Run with: uv run main.py" -ForegroundColor Green
