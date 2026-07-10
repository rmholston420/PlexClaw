---
applyTo:
  - "*.py"
  - "app/**/*.py"
  - "scripts/**/*.py"
  - "tests/**/*.py"
---

# Python instructions

When editing Python files in this repository:

## Tools and commands
- Use `ruff check .` to lint Python code.
- Use `pytest -q` to run the unit test suite.
- Prefer running targeted `pytest` (specific test files) first when changing a narrow area.

## Conventions
- Keep diffs minimal and task-scoped.
- Follow existing patterns in nearby code for async handling, logging, error messages, and response shapes.
- Treat session lifecycle code and metadata fields such as `mock_mode` and `model` as part of the public contract.
- Keep live session and replayed session metadata aligned when behavior changes.

## Verification
- For changes under `app/`, run at least:
  - `ruff check .`
  - `pytest -q`
- For changes to launcher-related Python helpers, also verify `bash run.sh` still passes its preflight checks.
- For test changes under `tests/`, ensure new tests are stable and deterministic.

## Documentation
- Update `CHANGELOG.md` if behavior changes are user-visible.
- Update `README.md` when setup, run flow, ports, hooks, or troubleshooting behavior changes.
