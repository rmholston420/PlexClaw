    #!/usr/bin/env bash
    set -euo pipefail

    echo "== repo =="
    pwd

    echo
    echo "== python =="
    python3 -c 'import sys; print(sys.executable)'

    echo
    echo "== sdk import =="
    python3 - <<'PY2'
import sys
try:
    import claude_agent_sdk
    print("claude_agent_sdk: OK")
    print("version:", getattr(claude_agent_sdk, "__version__", "unknown"))
except Exception as e:
    print("claude_agent_sdk: FAIL")
    print(repr(e))
    raise
PY2

    echo
    echo "== env =="
    env | grep -E 'ANTHROPIC|OLLAMA|VLLM|PLEXCLAW' | sort || true

    echo
    echo "== ollama reachability =="
    curl -fsS "${OLLAMA_BASE_URL:-http://127.0.0.1:11434}/api/tags" | head -c 1200 || {
      echo
      echo "Ollama check failed"
      exit 1
    }
    echo

    echo
    echo "== vllm reachability =="
    curl -fsS "${VLLM_BASE_URL:-http://127.0.0.1:30000}/v1/models" | head -c 1200 || true
    echo

    echo
    echo "== PlexClaw health =="
    curl -fsS http://127.0.0.1:8020/health | head -c 1200 || {
      echo
      echo "PlexClaw backend is not responding on 8020"
      exit 1
    }
    echo

    echo
    echo "== target files =="
    grep -n "ClaudeSDKClient\|mock_mode\|ANTHROPIC_BASE_URL\|OLLAMA_BASE_URL\|VLLM_BASE_URL\|PLEXCLAW_OLLAMA_MODEL\|PLEXCLAW_VLLM_MODEL"       app/runtime_sdk.py app/config.py pyproject.toml || true
