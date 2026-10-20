#!/bin/bash
# Startup script for Resolve AI Editing Companion
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Local-first captions defaults (EC2 / Podcast). Override any var before running this script.
export WHISPER_DEVICE="${WHISPER_DEVICE:-auto}"
export WHISPER_COMPUTE_TYPE="${WHISPER_COMPUTE_TYPE:-float16}"
export FFMPEG_VIDEO_ENCODER="${FFMPEG_VIDEO_ENCODER:-auto}"
export TRANSLATION_BACKEND="${TRANSLATION_BACKEND:-auto}"
export LOCAL_TRANSLATION_MODEL="${LOCAL_TRANSLATION_MODEL:-facebook/nllb-200-distilled-600M}"
export AUTO_PRODUCE_MODE="${AUTO_PRODUCE_MODE:-captions_only}"
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
export LOG_FORMAT="${LOG_FORMAT:-json}"

echo "Starting DaVinci Resolve Companion Backend (Port 8003)..."
echo "  AUTO_PRODUCE_MODE=$AUTO_PRODUCE_MODE  WHISPER_DEVICE=$WHISPER_DEVICE  TRANSLATION_BACKEND=$TRANSLATION_BACKEND"
cd "$SCRIPT_DIR/backend"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8003 &
BACKEND_PID=$!

echo "Starting DaVinci Resolve Companion Frontend (Port 5174)..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo "============================================================"
echo "🎬 Resolve AI Companion is LIVE at: http://localhost:5174"
echo "Backend API & DaVinci Bridge at:   http://localhost:8003"
echo "Press CTRL+C to terminate both servers."
echo "============================================================"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
