#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "error: Python executable not found at $PYTHON_BIN" >&2
  echo "hint: create the virtualenv first, or run with PYTHON_BIN=/path/to/python" >&2
  exit 1
fi

echo "[validate] Using: $PYTHON_BIN"
"$PYTHON_BIN" -m ruff check .
"$PYTHON_BIN" -m pytest -q
