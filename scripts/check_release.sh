#!/bin/bash
# Run from any directory. Tests use disposable storage via tests/conftest.py.
set -euo pipefail
APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_ROOT/backend"
python3 -m pytest tests -q
cd "$APP_ROOT/frontend"
./node_modules/.bin/tsc
./node_modules/.bin/vite build --configLoader runner
