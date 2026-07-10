# CLAUDE.md

## Scope
- PlexClaw is a Perplexity-style UI around Claude Code and local/mock runtimes.
- Keep changes small, reversible, and easy to verify.

## Commands
- Activate env: `. .venv/bin/activate`
- Launch app: `bash run.sh`
- Backend URL: `http://127.0.0.1:8020`
- Frontend URL: `http://127.0.0.1:5555/plexclaw-ui-canonical.html`
- Lint: `ruff check .`
- Full test suite: `pytest -q`
- Hook bootstrap: `bash scripts/setup-git-hooks.sh`
- Shell validation: `bash -n run.sh && bash -n scripts/setup-git-hooks.sh && bash -n .githooks/pre-push`

## Repo rules
- Treat session metadata fields like `mock_mode` and `model` as API/UI contract surface.
- Keep live and replayed session metadata aligned when behavior changes.
- Preserve launcher fail-fast behavior around ports 8020 and 5555 unless the task explicitly changes it.
- Do not rename public fields, commands, or ports without updating docs and consumers.

## Docs updates
- Update `CHANGELOG.md` for user-visible behavior changes.
- Update `README.md` when setup, run flow, ports, hooks, or troubleshooting changes.

## Verification
- Run the narrowest useful check first, then broader checks only as needed.
- For Python changes, start with targeted `pytest` where possible, then `pytest -q`.
- For launcher or hook changes, run shell validation and confirm hook bootstrap behavior.

## Handoff
- Report what changed.
- Report exact commands run.
- Report any unverified paths clearly.

