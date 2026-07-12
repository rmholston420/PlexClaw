@AGENTS.md

# PlexClaw — Claude Code Project Memory

## What this repo is
PlexClaw is a browser-native GUI for Claude Code and the Claude Agent SDK.
It exposes Claude sessions, tool streams, permissions, runtime state,
archive/replay, and local LLM routing as a fully interactive web UI.

## Stack
- Backend: FastAPI + Uvicorn on port 8020 (app/)
- Frontend: Vanilla JS / HTML served from frontend/
- SDK bridge: app/runtime_sdk.py owns all ClaudeSDKClient instances
- Event store: SQLite append-only log via app/event_store.py
- Hooks: app/hooks.py — extend here for tool interception and policy

## Key environment variables
| Variable | Purpose | Default |
|---|---|---|
| ANTHROPIC_API_KEY | Required for cloud Claude sessions | none |
| ANTHROPIC_BASE_URL | Override for local LLM backends | api.anthropic.com |
| ANTHROPIC_AUTH_TOKEN | Local-only: any non-empty string | none |
| OLLAMA_BASE_URL | Ollama server URL | http://127.0.0.1:11434 |
| VLLM_BASE_URL | vLLM server URL | http://127.0.0.1:30000 |
| PLEXCLAW_OLLAMA_MODEL | Default Ollama model name | qwen3:latest |
| PLEXCLAW_VLLM_MODEL | Default vLLM model name | Qwen/Qwen3-Coder-30B-A3B-Instruct |
| PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS | Session GC timeout | 1800 |

## Running locally
```
. .venv/bin/activate
bash run.sh
# Open http://127.0.0.1:8020
```

## Startup checks
run.sh fails fast if ports 8020 or 5555 are already bound.
The SDK falls back to MOCK MODE if claude-agent-sdk is not installed —
sessions still work but use the echo-back mock, not real Claude.

## Core conventions (from AGENTS.md)
- Filesystem routes must pass session_id so cwd resolves from the session jail.
- Cloud model defaults live only in app/provider_defaults.py — never duplicate.
- Keep REST, WebSocket, frontend cards, and replay metadata aligned when
  changing provider or session schema fields.
- mock_mode and model are frontend-visible contract fields — treat as API surface.
- Do not edit generated or unrelated files as cleanup.

## Claude Code local configuration
PlexClaw expects Claude Code CLI and the Claude Agent SDK to share one configuration surface.
Prefer project-local `.claude/settings.local.json` for non-secret defaults and `.env` for operator overrides.
For local Anthropic-compatible backends, keep `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`,
and the default model mapping variables aligned between Claude Code, the SDK, and PlexClaw.

