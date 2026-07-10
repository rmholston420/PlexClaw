# AGENTS.md

## Commands
- Activate env: `. .venv/bin/activate`
- Run app: `bash run.sh`
- Bootstrap hooks: `bash scripts/setup-git-hooks.sh`
- Lint: `ruff check .`
- Test all: `pytest -q`
- Validate shell entrypoints: `bash -n run.sh && bash -n scripts/setup-git-hooks.sh && bash -n .githooks/pre-push`

## External references
- Setup and run flow: `README.md`
- Release notes: `CHANGELOG.md`
- Python and tool config: `pyproject.toml`
- CI source of truth: `.github/workflows/ci.yml`
- Launcher behavior: `run.sh`

## Conventions
- Keep diffs minimal and task-scoped.
- Follow existing response shapes and naming near the edited code.
- Treat `mock_mode` and `model` as frontend-visible contract fields.
- Keep replayed session lifecycle metadata aligned with live session metadata.
- Preserve fail-fast startup checks for ports 8020 and 5555 unless intentionally changing them.
- Do not edit generated or unrelated files as cleanup.

## Workflow
- Read the relevant files before editing.
- Prefer targeted validation before full-suite validation.
- Update `CHANGELOG.md` and `README.md` when user-visible behavior or operator workflow changes.
- If hooks or launcher behavior changes, verify both the script path and the documented workflow.

## Handoff
- Summarize the change in 1 to 3 bullets.
- List exact verification commands run.
- State any gaps or unverified behavior explicitly.
