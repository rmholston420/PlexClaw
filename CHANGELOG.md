# Changelog

## 0.3.0 - 2026-07-12

### Added
- Git explorer workstation: branch list, branch switch/create, staged/unstaged summaries, and unified diff inspection wired to the active session repo.
- Filesystem explorer workstation: session-aware directory browser with inline text preview panel bound to the active session working directory.
- MCP control plane: Claude Desktop MCP server inventory, command-path testing, enabled/disabled toggles, and add/delete controls surfaced in the runtime UI.

### Changed
- Runtime meta panel now includes MCP control-plane status alongside provider routing, tool-search state, session cwd, and runtime mode to keep orchestration details visible in one place.
- Session-aware filesystem routes now drive both Git explorer and filesystem explorer panes, so browser UX follows the active session jail root rather than only the process startup directory.

### Hardening
- Git explorer actions (branch checkout/create and commit) now refresh status and branch lists atomically to keep frontend state aligned with the underlying repo.
- MCP config I/O continues to use atomic writes to the standard Claude Desktop config path, and UI operations respect the existing config layout instead of introducing a new format.


## 0.2.0 - 2026-07-10

### Added
- Mock Claude SDK fallback so the app runs without `claude-agent-sdk`.
- WebSocket contract coverage for happy-path session flow and protocol mismatch handling.
- Repo-tracked pre-push hook under `.githooks/pre-push`.
- One-command hook bootstrap via `scripts/setup-git-hooks.sh`.
- Launcher port preflight helper in `app/port_check.py`.
- Launcher shell contract and port-preflight regression tests.

### Changed
- Session create responses now return `mock_mode` and `model`, so the frontend can show which runtime is active and whether it is running in mock mode.
- Replayed session lifecycle events now include `mock_mode` and `model`, keeping archived streams aligned with live session metadata for tooling and UI.
- `run.sh` now auto-enables repo-tracked hooks for the current clone when needed.
- `run.sh` now fails fast with clear messages when ports 8020 or 5555 are already occupied.
- CI now validates shell entrypoints and hook bootstrap in addition to Ruff and pytest.
- Runtime configuration is now centralized for provider routing, tool-search defaults, allowed origins, and allowed hosts.
- The frontend top bar now shows grouped runtime routing metadata, including provider route and tool-search state.
- The frontend runtime panel now also shows the active session working directory and runtime mode, with helper text that marks the panel as the authoritative source for environment state.
- The transcript UI now hides raw tool input, and normalized `tool.started` events no longer retain `tool_input` payloads.
- Runtime diagnostics are now reachable at both `/api/diag/runtime` and `/api/runtime/diag`.
- The runtime system prompt now includes grounding rules that explicitly forbid inventing placeholder paths or unobserved environment details.
- The tool mode selector now exposes Default, Off, Auto, Auto 5%, and On states with immediate runtime metadata refresh.

### Hardening
- Filesystem routes now support session-aware jail roots derived from the active live session `cwd`, and the frontend now passes `session_id` to filesystem browsing and Git root endpoints.
- Cloud model defaults now support the `PLEXCLAW_CLOUD_MODELS` environment override and are centralized in `app/provider_defaults.py` so provider responses and schema defaults share one source of truth.
- Test isolation is now consolidated through `tests/conftest.py`, and redundant per-file autouse reset fixtures were removed.
- Removed the unused `WebSocketManager.send_to()` alias after repo-wide verification confirmed no call sites.
- Deleted the duplicate `BUILDSTATUS.md` file and kept `BUILD_STATUS.md` as the canonical project status document.

### Quality
- 109 tests passing locally as of July 2026.
