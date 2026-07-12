# PlexClaw


PlexClaw is a browser-native GUI for **Claude Code** and the **Claude Agent SDK**.

It is designed to expose Claude-native sessions, permissions, tools, runtime state, repo context, and useful local LLM settings as clearly and completely as possible in a modern browser interface. While the UI may borrow visual ideas from products like Perplexity Computer, PlexClaw is ultimately optimized for Claude Code and Claude Agent SDK workflows first.

## Product direction

PlexClaw aims to be:

- A full-featured browser GUI for Claude Code and Claude Agent SDK.
- A high-visibility control surface for useful local and self-hosted LLM settings.
- A repo-aware coding workspace for multi-session, tool-driven, browser-based development.
- A future embeddable plugin surface for Rigpa-LMS.

## Design principles

- Claude-native fidelity first; avoid hiding useful Claude Code or Agent SDK capabilities.
- Browser UX should enhance Claude workflows, not replace them with unrelated abstractions.
- Expose useful runtime state clearly: model, cwd, provider route, permission mode, tool state, and session status.
- Prefer an interface optimized for coding sessions, approvals, diffs, archives, and repo operations over one optimized only for generic chat.

## Architecture

- `app/main.py`: FastAPI backend with session, archive, replay, and WebSocket routes.
- `app/runtime_sdk.py`: Claude SDK runtime wrapper, multi-turn live session ownership, interrupt handling, archive passthroughs, and mock fallback.
- `app/event_store.py`: Append-only SQLite event log for replay and filtered event queries.
- `app/normalizer.py`: Maps runtime events into stable protocol envelopes.
- `app/archive_normalizer.py`: Converts variable archive metadata into a stable canonical shape.
- `/plexclaw-ui-canonical.html`: Backward-compat redirect route to the main UI.
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
2. Start your local model runtime, preferably Ollama on port 11434; vLLM on port 30000 is supported as a backup.
3. Run:
   - `bash run.sh`
4. Open:
   - `http://127.0.0.1:8020/` (primary UI)
  - `http://127.0.0.1:8020/plexclaw-ui-canonical.html` (legacy redirect)

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
- `run.sh` performs a fail-fast preflight check for port 8020 before launching.
- The local test gate runs automatically on `git push` through `.githooks/pre-push`.

## Current status

- 109 tests passing locally as of July 2026.
- Mock runtime fallback, WebSocket session flow, protocol mismatch handling, launcher port checks, launcher shell contract, runtime routing metadata, and tool-search UI semantics are all covered by tests.

## Session-aware filesystem routing

PlexClaw’s filesystem API now supports an optional live `session_id`, allowing backend filesystem browsing and reads to resolve relative to the active session `cwd` instead of only the process startup directory.

Filesystem behavior notes:

- `GET /api/fs/browse`, `GET /api/fs/read`, and `GET /api/fs/git-roots` accept an optional `session_id`.
- When a valid live session is supplied, the filesystem jail root is derived from that session’s working directory.
- The frontend browser now passes the active `session_id` for cwd browsing and Git root discovery, so the UI follows the active session context.
- Legacy `FS_ROOT` compatibility remains in place for tests and non-session fallback behavior.

## Local model configuration

PlexClaw is intended to run local-first, with Ollama as the primary provider and vLLM as the backup.

Configuration behavior:

- `OLLAMA_BASE_URL` defaults to `http://127.0.0.1:11434`.
- `VLLM_BASE_URL` defaults to `http://127.0.0.1:30000`.
- `PLEXCLAW_OLLAMA_MODEL` sets the default Ollama model for new sessions.
- `PLEXCLAW_VLLM_MODEL` sets the default vLLM model when the provider is switched to vLLM.
- `GET /api/providers` exposes both local provider routes and their discovered model lists.

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
- The top bar now also shows the session working directory and runtime mode, and the helper text under that panel explicitly marks it as the source of truth when model replies speculate about environment details.
- Raw tool input is hidden in the transcript UI and omitted from normalized `tool.started` events, reducing accidental leakage of prompt or filesystem details into replay, search, and copy flows.
- Runtime diagnostics are available at both `/api/diag/runtime` and `/api/runtime/diag`.


## Competitive feature targets

PlexClaw should selectively match or exceed the strongest ideas from existing Claude Code and Agent SDK UIs:

- Session browser primitives: list, search, resume, rename, tag, fork, archive, export.
- Parallel live sessions with clear busy/waiting/idle status.
- Strong permission UX with visible Claude SDK mode and approval tracing.
- Repo-aware coding affordances such as diffs, file context, worktree/project awareness, and touched-file visibility.
- Useful local LLM controls including provider route, base URL, model selection, and runtime inspection.
- A frontend architecture that can evolve from standalone app to Rigpa-LMS plugin.

