# PlexClaw Build Progress

All 10 slices from the build spec are implemented and committed, with additional post-slice hardening and cleanup landed afterward.

## Completed

- **Slice 1** — FastAPI backend on port 8020, static frontend on port 5555, stable protocol envelope `0.2.0`, live session creation, WebSocket prompt streaming
- **Slice 2** — Tool stream rendering: `tool.started` / `tool.delta` / `tool.completed` normalizer + expandable tool blocks
- **Slice 3** — Interrupts and session continuity: `POST /api/sessions/{id}/interrupt`, drain-after-interrupt pattern, per-session `ClaudeSDKClient` + async lock
- **Slice 4** — Replayable event store: SQLite-backed append-only log, `GET /api/sessions/{id}/events` (filterable), `GET /api/sessions/{id}/replay`
- **Slice 5** — Archived session browser: SDK passthroughs for `list_sessions`, `get_session_info`, `get_session_messages`; sidebar with click-to-resume
- **Slice 6** — Resume, fork, lineage grouping: `resume_session_id` + `fork_session` in session creation; sidebar lineage groups with expand/collapse
- **Slice 7** — Rename, tag, search, sort: `rename_session()` / `tag_session()` passthroughs; sidebar search input; sort by recent/title/tag/root
- **Slice 8** — Archive normalizer: `archive_normalizer.py` canonical shape (`id`, `title`, `summary`, `tag`, `created_at`, `updated_at`, `cwd`, `root_session_id`, `message_count`, `model`, `raw`)
- **Slice 9** — PlexClaw-style frontend polish: full design token system (fluid type, 4px spacing, OKLCH palette), dark/light toggle, SVG logo, Lucide icons, tool blocks with color-coded icons and running shimmer, markdown-lite assistant output renderer, user message bubbles, auto-resize textarea, inline rename/tag inputs (no `prompt()`), model selector, animated connection status dot, resizable sidebar with toggle, empty-archive state, mobile-responsive layout
- **Slice 10** — Tests, CI, `pyproject.toml`, `run.sh`, README

## Post-slice: Mock Mode (implemented)

- **`app/mock_sdk.py`** — `MockSDKClient` that mirrors the real `ClaudeSDKClient` interface: `connect()`, `query()`, `receive_response()`, `interrupt()`, `close()`
- **`runtime_sdk.py`** updated — `create_session` no longer raises `RuntimeError` when the SDK is missing; instead a `MockSDKClient` is used transparently
- **`submit_prompt`** streams token-by-token mock text through the identical normalizer pipeline, so all UI streaming paths (assistant.delta, assistant.completed) are exercised
- The `session.created` system message includes `"mock_mode": true` so the frontend can surface a warning badge
- **`tests/test_mock_sdk.py`** — async unit coverage for token streaming, echo content, interrupt, stop reason, and mock-mode banner behavior

## Post-slice: Provider routing & tool search (July 2026)

- Provider selection in the frontend routes sessions through Anthropic-compatible backends (cloud, Ollama, vLLM) via `ANTHROPIC_BASE_URL`, matching Claude Code’s environment-variable model.
- Session creation supports per-session tool-search env control via `tool_search_mode`, returning `provider_base_url`, `tool_search_mode`, and `tool_search_active` in both REST create-session responses and WebSocket lifecycle metadata.
- The PlexClaw top bar shows grouped runtime routing metadata, including the effective provider route and current tool-search state for the active session.
- Switching providers with an active live session clears that session context, updates tab state, and emits a system message prompting the user to start a new session on the new route.
- Frontend/runtime semantics coverage includes provider metadata rendering, create-session response parity, tool-search selector wiring, tool-search state clearing on provider change, replay/runtime state separation, and per-tab state preservation.

## Post-slice: Docs alignment (July 2026)

- `README.md` documents the runtime routing and tool-search UI; the repo now validates at 109 passing tests.
- `CHANGELOG.md` version `0.2.0` now records centralized runtime configuration, grouped runtime metadata, and explicit tool mode selector states.
- `AGENTS.md` now documents how runtime routing interacts with agent sessions, providers, hooks, tool-search behavior, and archive/replay semantics.

## Recent hardening

- Filesystem routes now support a per-session jail root derived from the active session `cwd` while preserving legacy `FS_ROOT` and `_safe_path()` compatibility for tests and existing helpers.
- Cloud provider models now support a `PLEXCLAW_CLOUD_MODELS` environment override, with test coverage for default behavior, explicit override, and empty-entry normalization.
- Unused `WebSocketManager.send_to()` alias was removed after repo-wide verification confirmed no call sites.

## Quality status

- **109 tests passing**
- Mock SDK fallback is implemented and covered by unit tests
- WebSocket happy-path session flow is covered
- WebSocket protocol mismatch rejection is covered
- Provider routing, tool-search env behavior, frontend runtime metadata rendering, and replay/runtime separation are covered
- Archive replay normalization and create-session response parity are covered
- Launcher port preflight is extracted into `app/port_check.py` and covered
- `run.sh` shell contract is covered by regression tests
- Repo-tracked pre-push hook is versioned under `.githooks/pre-push`

## Launcher behavior

- `frontend/index.html` is the single canonical UI entrypoint; `plexclaw-ui-canonical.html` is a backward-compat redirect shim
- `run.sh` auto-enables repo-tracked hooks for the current clone when needed
- `run.sh` fails fast with a clear error if port 8020 or 5555 are already occupied
- `scripts/setup-git-hooks.sh` can be run manually to configure `core.hooksPath` to `.githooks`

## Quick start

```bash
bash run.sh
```

Backend: [http://127.0.0.1:8020](http://127.0.0.1:8020)
Frontend root: [http://127.0.0.1:5555](http://127.0.0.1:5555)
Canonical UI: [http://127.0.0.1:5555/plexclaw-ui-canonical.html](http://127.0.0.1:5555/plexclaw-ui-canonical.html)
