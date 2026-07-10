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
- `run.sh` now auto-enables repo-tracked hooks for the current clone when needed.
- `run.sh` now fails fast with clear messages when ports 8020 or 5555 are already occupied.
- CI now validates shell entrypoints and hook bootstrap in addition to Ruff and pytest.

### Quality
- 53 tests passing locally at release cut.
