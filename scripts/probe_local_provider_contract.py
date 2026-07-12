import json
import os
import urllib.request


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, r.read().decode("utf-8", "replace")


ollama = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
vllm = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:30000").rstrip("/")

print("## Ollama /api/tags")
try:
    status, body = fetch(f"{ollama}/api/tags")
    print(status)
    print(body[:2000])
except Exception as e:
    print("ERROR", repr(e))

print("\n## vLLM /v1/models")
try:
    status, body = fetch(f"{vllm}/v1/models")
    print(status)
    print(body[:2000])
except Exception as e:
    print("ERROR", repr(e))

print("\n## Expected local env")
keys = [
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "OLLAMA_BASE_URL",
    "VLLM_BASE_URL",
    "PLEXCLAW_OLLAMA_MODEL",
    "PLEXCLAW_VLLM_MODEL",
]
print(json.dumps({k: os.getenv(k) for k in keys}, indent=2))
