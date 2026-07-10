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

## Runtime routing and agents

PlexClaw is built around Claude Agent SDK sessions and a hook-ready runtime, so the new runtime routing UI is intentionally wired to how agents, subagents, tools, and skills execute.

### Agent sessions and provider routing

- Each live browser session owns exactly one ClaudeSDKClient instance plus a lock, matching the build spec’s guidance for multi-turn continuity and safe interrupt handling.
- The session schema keeps `provider` in the contract even when only Claude cloud is used initially, so PlexClaw can route agents through alternate backends or bridges later without redesigning the frontend.
- The runtime routing card in the top bar reflects this provider choice:
  - Cloud routes represent the default Claude Agent SDK-hosted sessions.
  - Local routes (for example, Ollama or vLLM) represent alternate providers that still speak the same normalized protocol and agent hooks.

### Agents, subagents, tools, and skills

- Agent and subagent activity is normalized into the same stable event envelope used for assistant messages and tools:
  - text blocks become `assistant.delta` and `assistant.completed`,
  - tool use becomes `tool.started`, `tool.delta`, and `tool.completed`,
  - runtime exceptions become `session.failed`,
  - policy and audit hooks can emit `system.message`.
- This keeps the transcript and replay flows consistent even as agents and subagents call diverse tools or skills behind the scenes.
- The tool-search card in the top bar summarizes how aggressively the runtime will invoke tools and agents:
  - Default tools — use provider-specific defaults from the backend environment.
  - Auto tools / Auto tools 5% — allow experimental tool search and agent invocations in automatic modes.
  - Tools enabled / Tools disabled — reflect explicit per-session overrides in the runtime environment.

### Hook-ready runtime

- PlexClaw ships a `hooks.py` module from the start, as required by the build spec, so agent hooks have a dedicated extension seam for:
  - tool calls,
  - session lifecycle events,
  - stop conditions and interrupts,
  - subagent events,
  - audit, approval, and policy.
- Hooks can log, emit `system.message`, or enforce runtime policy without exposing raw SDK objects to the browser, because all events are normalized at the bridge boundary.

### Archive and replay for agents

- The append-only event store records normalized agent activity (including tool use and system messages) alongside assistant deltas, using a stable envelope with `session_id`, `seq`, `type`, `payload`, and `protocol_version`.
- Archived sessions can be resumed or forked with agent state intact, and replay uses stored normalized events instead of re-querying Claude.
- Lineage grouping in the sidebar makes agent-driven forks structurally visible: `Continue` resumes the original agent lineage, while `Fork` starts a distinct agent branch with its own session and tools.

