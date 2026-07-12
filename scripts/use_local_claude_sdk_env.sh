#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cp .env.example.local .env
echo "Wrote .env for local Claude Agent SDK mode"
python scripts/doctor_claude_sdk.py
