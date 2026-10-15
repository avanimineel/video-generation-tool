#!/bin/bash
# Startup script for Resolve AI Editing Companion
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting DaVinci Resolve Companion Backend (Port 8003)..."
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
