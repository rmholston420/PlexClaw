# PlexClaw Build Progress

All 10 slices from the build spec are implemented and committed.

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
- **`tests/test_mock_sdk.py`** — five async unit tests covering token streaming, echo content, interrupt, stop_reason, and mock-mode banner

## Mock mode

The app fully starts and is usable without `claude-agent-sdk`. Sessions are created, prompts are streamed back as echo responses with a prominent ⚠️ mock-mode banner. Set `ANTHROPIC_API_KEY` and `pip install claude-agent-sdk` to activate real Claude Code sessions.

## Quick start

```bash
bash run.sh
```

Backend: http://127.0.0.1:8020  
Frontend: http://127.0.0.1:5555
