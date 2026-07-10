# PlexClaw

PlexClaw is a local browser-based coding workstation modeled after the PlexClaw interaction style and backed by a FastAPI + WebSocket bridge for Claude Code sessions.

## Architecture

- `app/main.py`: FastAPI backend with session, archive, replay, and WebSocket routes.
- `app/runtime_sdk.py`: Claude SDK runtime wrapper, multi-turn live session ownership, interrupt handling, archive passthroughs, and mock fallback.
- `app/event_store.py`: Append-only SQLite event log for replay and filtered event queries.
- `app/normalizer.py`: Maps runtime events into stable protocol envelopes.
- `app/archive_normalizer.py`: Converts variable archive metadata into a stable canonical shape.
- `frontend/plexclaw-ui-canonical.html`: PlexClaw-style static browser UI.
- `frontend/sdk-bridge-client.js`: Browser client, replay renderer, archive controls, and tool block rendering.

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
