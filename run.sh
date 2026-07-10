#!/usr/bin/env bash
set -euo pipefail

python -m uvicorn app.main:app --host 127.0.0.1 --port 8020 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

cd frontend
python -m http.server 5555 --bind 127.0.0.1
