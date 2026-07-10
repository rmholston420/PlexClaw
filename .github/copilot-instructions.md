# GitHub Copilot instructions

Use `AGENTS.md` in the repository root as the primary source of truth for:
- setup and run commands,
- lint and test commands,
- workflow expectations,
- documentation update rules,
- repo conventions,
- handoff format.

When editing this repository:
- follow the commands and conventions in `AGENTS.md`,
- prefer minimal, task-scoped diffs,
- update `CHANGELOG.md` and `README.md` when user-visible behavior or operator workflow changes,
- treat frontend-visible contract fields such as `mock_mode` and `model` as sensitive API/UI surface,
- preserve launcher fail-fast behavior around ports 8020 and 5555 unless the task explicitly changes it.

If more specific Copilot instructions are added later under `.github/instructions/`, treat this file as the global baseline.
