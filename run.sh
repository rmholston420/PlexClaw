#!/usr/bin/env bash
set -euo pipefail

if [ -f ".githooks/pre-push" ]; then
  CURRENT_HOOKS_PATH="$(git config --local --get core.hooksPath || true)"
  if [ "$CURRENT_HOOKS_PATH" != ".githooks" ]; then
    echo "[run.sh] Git hooks not configured for this clone."
    echo "[run.sh] Enabling repo-tracked hooks via scripts/setup-git-hooks.sh"
    bash scripts/setup-git-hooks.sh
  fi
fi

python - <<'PYPORT'
import sys

from app.port_check import blocked_ports, format_blocked_ports

blocked = blocked_ports()
if blocked:
    for line in format_blocked_ports(blocked):
        print(line, file=sys.stderr)
    sys.exit(1)
PYPORT

python -m uvicorn app.main:app --host 127.0.0.1 --port 8020 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

cd frontend
python -m http.server 5555 --bind 127.0.0.1
