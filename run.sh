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


FRONTEND_TMP_DIR="$(mktemp -d)"
export FRONTEND_TMP_DIR

python - <<'PYFRONTEND'
from pathlib import Path
import hashlib
import os
import shutil

src = Path("frontend")
dst = Path(os.environ["FRONTEND_TMP_DIR"])

shutil.copytree(src, dst, dirs_exist_ok=True)

bridge = dst / "sdk-bridge-client.js"
index = dst / "index.html"

digest = hashlib.sha256(bridge.read_bytes()).hexdigest()[:12]
html = index.read_text()
html = html.replace("sdk-bridge-client.js?v=DEV", f"sdk-bridge-client.js?v={digest}")
index.write_text(html)
print(f"[run.sh] frontend cache-bust hash: {digest}")
PYFRONTEND

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
  rm -rf "$FRONTEND_TMP_DIR" 2>/dev/null || true
}
trap cleanup EXIT

cd "$FRONTEND_TMP_DIR"
