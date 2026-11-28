#!/bin/bash
# Measure reference clips already in the inbox. Does not download study sources.
# Daily schedule, 02:30 UTC (08:00 Asia/Calcutta):
#   30 2 * * * /data/developer/oonex/video-generation-tool/scripts/audit_reference_inbox.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/backend/logs"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="python3"
fi
export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" -m app.services.reference_study >>"$ROOT/backend/logs/reference-study.log" 2>&1
