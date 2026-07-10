# Changelog

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

### Quality
- 106 tests passing locally as of July 2026.
