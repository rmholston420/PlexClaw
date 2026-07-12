#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f ".venv/bin/activate" ]]; then
  . .venv/bin/activate
fi

echo
echo "== Claude / PlexClaw local routing doctor =="

python - <<'PY'
import importlib
import os
from pathlib import Path

print("\n[python packages]")
for name in ["claude_agent_sdk", "fastapi", "uvicorn"]:
    try:
        m = importlib.import_module(name)
        print(f"{name}: OK ({getattr(m, '__file__', 'built-in')})")
    except Exception as e:
        print(f"{name}: FAIL -> {e}")

print("\n[plexclaw sdk]")
from app.runtime_sdk import _SDK_AVAILABLE
print("SDK available:", _SDK_AVAILABLE)

print("\n[env]")
keys = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "PLEXCLAW_OLLAMA_MODEL",
    "OLLAMA_BASE_URL",
    "VLLM_BASE_URL",
]
for k in keys:
    v = os.getenv(k)
    if not v:
        print(f"{k}=<unset>")
    elif "KEY" in k or "TOKEN" in k:
        print(f"{k}=<set:{len(v)} chars>")
    else:
        print(f"{k}={v}")

print("\n[project files]")
for p in [Path(".claude/settings.local.json"), Path(".claude/settings.local.json.example"), Path(".env.example")]:
    print(f"{p}: {'present' if p.exists() else 'missing'}")
PY
