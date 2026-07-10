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
import socket
import sys

ports = [(8020, "backend"), (5555, "frontend")]
blocked = []

for port, label in ports:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        blocked.append((port, label))
    finally:
        sock.close()

if blocked:
    for port, label in blocked:
        print(f"[run.sh] Port {port} already in use ({label}).", file=sys.stderr)
    print("[run.sh] Stop the existing process or free the port, then retry.", file=sys.stderr)
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
