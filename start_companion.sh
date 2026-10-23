#!/bin/bash
# Startup script for Resolve AI Editing Companion
# Durable logs by default — do not depend on an interactive SSH TTY.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_DIR="$SCRIPT_DIR/backend"
LOG_DIR="${LOG_DIR:-$BACKEND_DIR/logs}"
mkdir -p "$LOG_DIR"

# App + uvicorn loggers write here via SafeRotatingFileHandler (see logging_setup.py).
# Override: LOG_FILE=/var/log/resolve-companion.log  or  LOG_FILE= to disable file sink.
export LOG_FILE="${LOG_FILE:-$LOG_DIR/companion.log}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Shell / process stdout+stderr (bootstrap messages, uncaught prints) — separate from LOG_FILE.
BACKEND_CONSOLE_LOG="${BACKEND_CONSOLE_LOG:-$LOG_DIR/uvicorn-console.log}"
FRONTEND_CONSOLE_LOG="${FRONTEND_CONSOLE_LOG:-$LOG_DIR/frontend-console.log}"

BACKEND_PORT="${BACKEND_PORT:-8003}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"

echo "Starting DaVinci Resolve Companion Backend (Port ${BACKEND_PORT})..."
echo "  LOG_FILE=$LOG_FILE"
echo "  console -> $BACKEND_CONSOLE_LOG"
cd "$BACKEND_DIR"
# Redirect away from the controlling terminal so detach/SSH hangup cannot
# turn every access-log line into OSError: [Errno 5] Input/output error.
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
  >>"$BACKEND_CONSOLE_LOG" 2>&1 &
BACKEND_PID=$!

echo "Starting DaVinci Resolve Companion Frontend (Port ${FRONTEND_PORT})..."
cd "$SCRIPT_DIR/frontend"
nohup npm run dev -- --port "$FRONTEND_PORT" >>"$FRONTEND_CONSOLE_LOG" 2>&1 &
FRONTEND_PID=$!

echo "============================================================"
echo "Resolve AI Companion is LIVE at: http://localhost:${FRONTEND_PORT}"
echo "Backend API & DaVinci Bridge at:   http://localhost:${BACKEND_PORT}"
echo "App log file:  $LOG_FILE"
echo "Backend console: $BACKEND_CONSOLE_LOG"
echo "Press CTRL+C to terminate both servers."
echo "============================================================"

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait
