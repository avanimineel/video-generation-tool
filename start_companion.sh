#!/bin/bash
# Startup script for Resolve AI Editing Companion
# Prefer in-process LOG_FILE FileHandler — do not rely on shell redirect alone.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_DIR="$SCRIPT_DIR/backend"
LOG_DIR="${LOG_DIR:-$BACKEND_DIR/logs}"
mkdir -p "$LOG_DIR"

# Prefer project venv so system python3 (often 3.9 without deps) is not used.
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/.venv/bin/activate"
  PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python3" ]]; then
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/.venv/bin/activate"
  PYTHON="$SCRIPT_DIR/.venv/bin/python3"
else
  PYTHON="${PYTHON:-python3}"
  echo "WARNING: No .venv found at $SCRIPT_DIR/.venv — using $PYTHON"
  echo "  Create one: python3.11 -m venv .venv && .venv/bin/pip install fastapi 'uvicorn[standard]' ..."
fi

# Local-first captions defaults (EC2 / Podcast). Override any var before running this script.
export WHISPER_DEVICE="${WHISPER_DEVICE:-auto}"
export WHISPER_COMPUTE_TYPE="${WHISPER_COMPUTE_TYPE:-float16}"
export FFMPEG_VIDEO_ENCODER="${FFMPEG_VIDEO_ENCODER:-auto}"
export TRANSLATION_BACKEND="${TRANSLATION_BACKEND:-auto}"
export LOCAL_TRANSLATION_MODEL="${LOCAL_TRANSLATION_MODEL:-facebook/nllb-200-distilled-600M}"
export AUTO_PRODUCE_MODE="${AUTO_PRODUCE_MODE:-captions_only}"
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
export LOG_FORMAT="${LOG_FORMAT:-json}"

# Prefer /var/log/resolve-companion.log when writable (matches EC2 operators).
if [ -z "${LOG_FILE+x}" ]; then
  if { [ -w /var/log/resolve-companion.log ] 2>/dev/null; } || \
     { [ ! -e /var/log/resolve-companion.log ] && [ -w /var/log ] 2>/dev/null; }; then
    export LOG_FILE="/var/log/resolve-companion.log"
  else
    export LOG_FILE="$LOG_DIR/companion.log"
  fi
fi

# Console capture for bootstrap / uncaught prints ONLY — keep this separate
# from LOG_FILE so shell redirect cannot amplify logging handleError floods.
BACKEND_CONSOLE_LOG="${BACKEND_CONSOLE_LOG:-$LOG_DIR/uvicorn-console.log}"
FRONTEND_CONSOLE_LOG="${FRONTEND_CONSOLE_LOG:-$LOG_DIR/frontend-console.log}"

BACKEND_PORT="${BACKEND_PORT:-8003}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"

# Default: disable uvicorn access logger (main source of Errno 5 spam when a
# StreamHandler emit fails and handleError writes into a redirected log file).
# Set UVICORN_ACCESS_LOG=1 to enable; access lines then go through the safe
# FileHandler from logging_setup.py (not a fragile duplicate stream).
UVICORN_EXTRA_ARGS=()
if [ "${UVICORN_ACCESS_LOG:-0}" != "1" ]; then
  UVICORN_EXTRA_ARGS+=(--no-access-log)
fi

echo "Starting DaVinci Resolve Companion Backend (Port ${BACKEND_PORT})..."
echo "  python=$PYTHON"
echo "  LOG_FILE=$LOG_FILE"
echo "  UVICORN_ACCESS_LOG=${UVICORN_ACCESS_LOG:-0} (0 => --no-access-log)"
echo "  AUTO_PRODUCE_MODE=$AUTO_PRODUCE_MODE  WHISPER_DEVICE=$WHISPER_DEVICE  TRANSLATION_BACKEND=$TRANSLATION_BACKEND"
echo "  console -> $BACKEND_CONSOLE_LOG (not LOG_FILE)"
cd "$BACKEND_DIR"

# Documented invoke (same flags):
#   LOG_FILE=/var/log/resolve-companion.log \
#   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --no-access-log
nohup "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
  "${UVICORN_EXTRA_ARGS[@]}" \
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
