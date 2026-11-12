#!/bin/bash
# Stop Resolve AI Editing Companion (ports from start_companion.sh)

for PORT in 8003 5174 8002; do
  PIDS=$(lsof -ti ":$PORT" 2>/dev/null || fuser -k "$PORT/tcp" 2>/dev/null)
  if [ -n "$PIDS" ]; then
    echo "Stopping processes on port $PORT: $PIDS"
    kill $PIDS 2>/dev/null || true
    sleep 1
    # force if still alive
    STILL=$(lsof -ti ":$PORT" 2>/dev/null)
    if [ -n "$STILL" ]; then
      kill -9 $STILL 2>/dev/null || true
      echo "Force-killed port $PORT"
    fi
  else
    echo "Nothing on port $PORT"
  fi
done

# catch orphaned uvicorn / vite if ports already freed
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo "Done."
