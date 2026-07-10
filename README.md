# PlexClaw

Current release: `0.2.0`

PlexClaw is a local browser-based coding workstation modeled after the PlexClaw interaction style and backed by a FastAPI + WebSocket bridge for Claude Code sessions.

## Architecture

- `app/main.py`: FastAPI backend with session, archive, replay, and WebSocket routes.
- `app/runtime_sdk.py`: Claude SDK runtime wrapper, multi-turn live session ownership, interrupt handling, archive passthroughs, and mock fallback.
- `app/event_store.py`: Append-only SQLite event log for replay and filtered event queries.
- `app/normalizer.py`: Maps runtime events into stable protocol envelopes.
- `app/archive_normalizer.py`: Converts variable archive metadata into a stable canonical shape.
- `frontend/plexclaw-ui-canonical.html`: PlexClaw-style static browser UI.
- `frontend/sdk-bridge-client.js`: Browser client, replay renderer, archive controls, and tool block rendering.
- `app/port_check.py`: Launcher port preflight helper used by `run.sh`.
- `.githooks/pre-push`: Repo-tracked pre-push test gate.
- `scripts/setup-git-hooks.sh`: One-time local hook bootstrap for fresh clones.

## Git hooks

After cloning, enable the repo-tracked pre-push hook once:

```bash
bash scripts/setup-git-hooks.sh
```

This configures `core.hooksPath` to use `.githooks`, so every `git push` runs `pytest -q` locally before publishing.

## Quick start

1. Install dependencies:
   - `python -m pip install -e .[dev]`
2. Optional: install and configure the Claude Agent SDK / API credentials for live use.
3. Run:
   - `bash run.sh`
4. Open:
   - `http://127.0.0.1:5555/plexclaw-ui-canonical.html`

## Backend routes

- `GET /health`
- `POST /api/sessions`
- `GET /api/sessions/{id}/events`
- `GET /api/sessions/{id}/replay`
- `POST /api/sessions/{id}/interrupt`
- `POST /api/sessions/{id}/model/{model}`
- `GET /api/archive/sessions`
- `GET /api/archive/sessions/{id}`
- `GET /api/archive/sessions/{id}/messages`
- `POST /api/archive/sessions/{id}/rename`
- `POST /api/archive/sessions/{id}/tag`
- `WS /ws/{id}`

## Development notes

- The bridge exposes protocol version `0.2.0`.
- The frontend consumes only normalized protocol events and canonical archive metadata.
- If the Claude SDK is unavailable, the runtime uses a mock streaming mode so the UI remains runnable.
- `run.sh` auto-configures repo-tracked Git hooks for the current clone when needed.
- `run.sh` performs a fail-fast preflight check for ports 8020 and 5555 before launching.
- The local test gate runs automatically on `git push` through `.githooks/pre-push`.

## Current status

- 86 tests passing locally as of July 2026.
- Mock runtime fallback, WebSocket session flow, protocol mismatch handling, launcher port checks, launcher shell contract, runtime routing metadata, and tool-search UI semantics are all covered by tests.

## Runtime routing & tool search

PlexClaw’s top bar exposes the effective runtime routing and tool-search state, so you can see how your session is executed at a glance.

Runtime UI elements:

- Provider switcher — choose the active provider (cloud, Ollama, vLLM, etc.).
- Provider route card — shows the effective route for the current provider, for example:
  - Cloud (default route) when using the built-in cloud backend.
  - Ollama via http://127.0.0.1:11434 when routed to a local Ollama instance.
- Tool search card — summarizes tool-search behavior for the session:
  - Default tools — use backend defaults for this provider.
  - Auto tools / Auto tools 5% — enable experimental tool search in auto modes.
  - Tools enabled — tools are explicitly enabled for the session.
  - Tools disabled — tools are explicitly or implicitly disabled.

Tool mode selector:

- The Tool mode dropdown controls how aggressively PlexClaw uses tools:
  - Default — defer to backend defaults for the active provider.
  - Off — disable tool search for the session.
  - Auto — allow the runtime to use tool search automatically.
  - Auto 5% — enable tool search in a small fraction of turns for testing.
  - On — force tools to be considered on every turn.
- Changes take effect immediately and are reflected in the Tool search card.

Backend configuration:

- Provider base URLs, CORS, allowed hosts, and tool-search defaults are centralized in the backend.
- The frontend runtime section renders directly from this centralized state, so the UI stays in sync with environment configuration.
