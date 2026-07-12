# PlexClaw — Open-Source GUI Cannibalization Audit

> Generated July 2026. Maps every major open-source Claude Code / Agent SDK GUI against PlexClaw's current feature set and identifies the highest-value code to port.

---

## The Landscape — Five Repos Worth Cannibalizing

### 1. CloudCLI / claudecodeui
- **Repo**: https://github.com/siteboon/claudecodeui
- **Stack**: React 18 + Vite (frontend), Node.js + Express + WebSocket (backend)
- **Stars**: 5.8k | **License**: GPL-3.0
- **Key features**: Responsive desktop/mobile PWA, integrated shell terminal via WebSocket, CodeMirror file editor with syntax highlighting, Git explorer (stage/commit/branch switch), multi-CLI routing (Claude Code / Cursor CLI / Codex), TaskMaster AI kanban integration, session persistence via SQLite.

### 2. Claudia
- **Repo**: https://github.com/getAsterisk/claudia
- **Stack**: React 18 + TypeScript + Vite 6 (frontend), Rust + Tauri 2 (backend), SQLite (rusqlite), shadcn/ui + Tailwind CSS v4
- **Stars**: 14.2k | **License**: AGPL-3.0
- **Key features**: Desktop native app (not web-only), CC Agents system (custom system-prompt agents + background execution + execution history), Usage Analytics Dashboard (cost/token breakdown by model/project/date + visual charts), MCP Server Management UI (add/test/import from Claude Desktop), Timeline & Checkpoints (branching session versioning + diff viewer + fork from checkpoint), CLAUDE.md editor with live preview.

### 3. sugyan/claude-code-webui
- **Repo**: https://github.com/sugyan/claude-code-webui
- **Stack**: Deno + TypeScript (backend), React (frontend)
- **Stars**: ~800 | **License**: MIT
- **Key features**: Minimal, clean web chat interface for Claude Code CLI; real-time streaming via Server-Sent Events; multi-session support; clean separation of SSE streaming from UI state.

### 4. vultuk/claude-code-web
- **Repo**: https://github.com/vultuk/claude-code-web
- **Stack**: Node.js, React
- **Stars**: ~400 | **License**: MIT
- **Key features**: Multi-session web interface; lightweight process management for Claude Code; REST + WebSocket hybrid pattern.

### 5. davila7/claude-code-templates
- **Repo**: https://github.com/davila7/claude-code-templates (`npx claude-code-templates@latest --chats`)
- **Stack**: Node.js, React
- **Stars**: ~300 | **License**: MIT
- **Key features**: Real-time conversation visualizer showing tool call details; "Show details" per-tool expansion; runs entirely on local machine with privacy guarantee; zero-install via `npx`.

### 6. Anthropic claude-agent-sdk demos
- **Repo**: https://github.com/anthropics/claude-agent-sdk-typescript (official demos subdirectory)
- **Stack**: React + Express + WebSocket, TypeScript
- **License**: Apache-2.0 (Anthropic)
- **Key features**: Simple Chat App — full WebSocket streaming conversation loop; Research Agent — multi-agent orchestration with subagent coordination; AskUserQuestion HTML preview cards — renders option previews as styled HTML mockups instead of plain text; Resume Generator — multi-source web-search + structured doc assembly agent.

---

## PlexClaw Current Capabilities (v0.2.0)

PlexClaw already has:
- FastAPI backend on port 8020, WebSocket streaming, stable protocol envelope `0.2.0`
- Tool stream rendering (tool.started / tool.delta / tool.completed) with expandable blocks
- Interrupt + session continuity
- SQLite-backed replayable event store
- Session archive browser with resume/fork/lineage grouping
- Rename, tag, search, sort on sessions
- Archive normalizer
- Full design token system (fluid type, OKLCH palette, dark/light toggle, SVG logo)
- Provider routing (Anthropic cloud / Ollama / vLLM via `ANTHROPIC_BASE_URL`)
- Tool-search mode selector
- 109 passing tests

---

## Gap Analysis — What PlexClaw Lacks

| Feature | Source | Priority |
|---|---|---|
| Git Explorer (stage/commit/branch) | CloudCLI | HIGH — power-user daily driver |
| CodeMirror file editor (in-session editing) | CloudCLI | HIGH — essential for agentic edit/review loop |
| CC Agents system (custom system-prompt agents + background execution + history) | Claudia | HIGH — core differentiator |
| Usage Analytics Dashboard (cost + token breakdown + charts) | Claudia | HIGH — mandatory for local LLM vs cloud cost awareness |
| Timeline & Checkpoints (branch/fork/diff viewer) | Claudia | HIGH — unique value; no other web UI has this |
| MCP Server Management UI | Claudia | MEDIUM — PlexClaw uses MCP but lacks visual management |
| CLAUDE.md editor with live preview | Claudia | MEDIUM — quality-of-life |
| Per-tool "Show details" expansion (full tool call forensics) | claude-code-templates | MEDIUM — PlexClaw has tool blocks but not deep forensics |
| AskUserQuestion HTML preview cards | Anthropic demos | MEDIUM — when `previewFormat: "html"` is used |
| PWA / Add-to-Home-Screen | CloudCLI | LOW — PlexClaw is local-only |
| TaskMaster AI kanban integration | CloudCLI | LOW — optional project management layer |

---

## Cannibalization Plan — What to Port and How

### PORT 1: Git Explorer (from CloudCLI)

**What to take**: The `GitExplorer` React component and its backend `/api/git/*` Express routes.

- CloudCLI's Git Explorer calls `git status`, `git diff`, `git add`, `git commit`, `git branch`, `git checkout` as child processes and streams results back.
- **Port strategy**: Re-implement the Express routes as FastAPI endpoints in `app/routes/git.py`. Use Python's `subprocess` (already used for Claude Code process management) to shell out to `git`. Wire the React component into PlexClaw's sidebar panel system.
- **PlexClaw integration point**: `frontend/index.html` sidebar tabs — add a "Git" tab alongside the existing session archive panel.
- **Files to create**: `app/routes/git.py`, `tests/test_git_routes.py`, frontend `GitExplorer` component in `frontend/src/components/`.

```bash
# Inspect CloudCLI git routes before porting
git clone https://github.com/siteboon/claudecodeui.git /tmp/claudecodeui
grep -r 'git' /tmp/claudecodeui/server/ --include='*.js' -l
```

### PORT 2: CodeMirror File Editor (from CloudCLI)

**What to take**: The file tree + CodeMirror editor panel with syntax highlighting and live file save.

- CloudCLI uses CodeMirror 6 (`@codemirror/view`, `@codemirror/lang-*` packages). Its backend exposes `GET /api/files?path=` and `PUT /api/files` routes.
- **Port strategy**: PlexClaw already has a filesystem jail (`app/routes/` with `_safe_path()`). Add `GET /api/fs/file` and `PUT /api/fs/file` endpoints to the existing `app/routes/filesystem.py`. Port the CodeMirror component directly — it's pure frontend, framework-agnostic.
- **PlexClaw integration point**: New "Files" sidebar tab; opens in a right-panel split view alongside the chat.

### PORT 3: CC Agents System (from Claudia)

**What to take**: The agent definition schema, agent library storage, and background execution model.

- Claudia stores agents as SQLite rows: `(id, name, icon, system_prompt, model, file_read, file_write, network_access)`. Execution spawns a separate process per agent run and logs to an `agent_runs` table.
- **Port strategy**: Add `app/models/agent.py` (SQLAlchemy model), `app/routes/agents.py` (CRUD + execute), and a frontend `AgentLibrary` component. The background execution model maps directly to PlexClaw's existing `ClaudeSDKClient` per-session pattern — each agent run is just a session with a fixed system prompt and a pre-configured `allowed_tools` list.
- **Files to create**: `app/models/agent.py`, `app/routes/agents.py`, `tests/test_agents.py`, frontend `AgentBuilder` + `AgentLibrary` components.

### PORT 4: Usage Analytics Dashboard (from Claudia)

**What to take**: The token/cost aggregation queries and the chart components.

- Claudia reads token usage from its SQLite event store and groups by `model`, `project`, `date`. It renders with Recharts (React).
- **Port strategy**: PlexClaw's event store (`app/event_store.py`) already appends every `assistant.completed` event which includes `usage` metadata (input_tokens, output_tokens, cache_read_tokens) from the Claude SDK. Add `GET /api/analytics` endpoint that runs aggregation queries on the events table. Add a `UsageDashboard` React component using Chart.js (already in the PlexClaw skill stack) for cost/token breakdown.
- **Model cost table**: Maintain a `CLAUDE_PRICING` dict in `app/config.py` (cost per million input/output tokens per model) and multiply against token counts.
- **Files to create**: `app/routes/analytics.py`, `tests/test_analytics.py`, frontend `UsageDashboard` component.

### PORT 5: Timeline & Checkpoints (from Claudia)

**What to take**: The checkpoint creation, visual timeline, and diff viewer.

- Claudia's checkpoint system (in `src-tauri/src/checkpoint/`) snapshots the entire project directory as a git stash-like operation plus metadata. Its frontend renders a branching tree with `fork` and `restore` actions.
- **Port strategy**: PlexClaw already has `fork_session` and lineage grouping (Slice 6). Extend this:
  1. Add `POST /api/sessions/{id}/checkpoint` — writes a named snapshot of the session's `cwd` file tree into the event store as a `checkpoint.created` event with a manifest of file hashes.
  2. Add `GET /api/sessions/{id}/checkpoints` and `POST /api/sessions/{id}/checkpoints/{checkpoint_id}/restore`.
  3. Add a diff viewer: `GET /api/sessions/{id}/checkpoints/{a}/diff/{b}` returns a unified diff between two checkpoint manifests.
  4. Frontend: extend the existing lineage tree in the sidebar to show checkpoint markers inline on the timeline.
- **Files to modify/create**: `app/routes/checkpoints.py`, `app/checkpoint_store.py`, `tests/test_checkpoints.py`, frontend timeline component enhancement.

### PORT 6: MCP Server Management UI (from Claudia)

**What to take**: The MCP server registry UI component and Claude Desktop config importer.

- Claudia reads/writes `~/.claude/claude_desktop_config.json` (the standard MCP config location). Its UI shows server name, command, args, env vars, and a "Test Connection" button.
- **Port strategy**: PlexClaw sessions already accept MCP config via `ANTHROPIC_BASE_URL` env routing. Add `GET /api/mcp/servers`, `POST /api/mcp/servers`, `DELETE /api/mcp/servers/{name}` that read/write `~/.claude/claude_desktop_config.json`. Add an `MCPManager` frontend panel.
- **Files to create**: `app/routes/mcp.py`, `tests/test_mcp.py`, frontend `MCPManager` component.

### PORT 7: Tool Call Forensics (from claude-code-templates)

**What to take**: The per-tool "Show details" expansion showing exact tool input/output JSON.

- PlexClaw's tool blocks already show `tool.started` / `tool.completed` events. What's missing is the raw JSON forensics panel.
- **Port strategy**: The event store already appends full `tool.completed` payloads. In the frontend `ToolBlock` component, add a "Show raw" toggle that renders the full `tool_input` and `tool_output` JSON in a CodeMirror JSON viewer (using the same CodeMirror instance from PORT 2).
- **Files to modify**: `frontend/src/components/ToolBlock` (or equivalent in `frontend/index.html`).

---

## Implementation Sequence

Order by impact-to-effort ratio for PlexClaw's Python/FastAPI architecture:

1. **Tool Call Forensics** — 1 day, frontend-only, no backend changes needed
2. **Usage Analytics** — 2 days, queries already-existing event store data
3. **Git Explorer** — 2 days, clean Python subprocess + new sidebar tab
4. **CC Agents System** — 3 days, new SQLAlchemy model + routes + frontend
5. **CodeMirror File Editor** — 2 days, frontend-heavy, minimal backend (FS routes exist)
6. **MCP Server Management UI** — 2 days, reads/writes existing config file
7. **Timeline & Checkpoints** — 3 days, extends existing fork/lineage system

**Total estimated effort**: ~15 development days for full cannibalization.

---

## License Compatibility

| Repo | License | Can port code into PlexClaw? | Notes |
|---|---|---|---|
| CloudCLI (claudecodeui) | GPL-3.0 | ✅ Yes (PlexClaw is also open-source) | Must keep GPL-3.0 attribution on ported files |
| Claudia | AGPL-3.0 | ✅ Yes (open-source use) | AGPL requires source disclosure if served over network — PlexClaw is local-only, so this is satisfied |
| sugyan/claude-code-webui | MIT | ✅ Yes, unrestricted | |
| vultuk/claude-code-web | MIT | ✅ Yes, unrestricted | |
| davila7/claude-code-templates | MIT | ✅ Yes, unrestricted | |
| Anthropic SDK demos | Apache-2.0 | ✅ Yes | Apache-2.0 is compatible with all of the above |

---

## Quick-Start Commands

```bash
# Clone all source repos for inspection
git clone https://github.com/siteboon/claudecodeui.git /tmp/claudecodeui
git clone https://github.com/getAsterisk/claudia.git /tmp/claudia
git clone https://github.com/sugyan/claude-code-webui.git /tmp/claude-code-webui
git clone https://github.com/davila7/claude-code-templates.git /tmp/claude-code-templates
git clone https://github.com/anthropics/claude-agent-sdk-typescript.git /tmp/agent-sdk-demos

# Inspect Claudia's checkpoint system (highest-value unique feature)
ls /tmp/claudia/src-tauri/src/checkpoint/

# Inspect CloudCLI's git routes
grep -r 'router\.' /tmp/claudecodeui/server/ --include='*.js' | grep git

# Inspect Claudia's agent model (SQLite schema)
grep -A 30 'CREATE TABLE' /tmp/claudia/src-tauri/src/commands/agents.rs

# Inspect Claudia's usage analytics queries
grep -r 'token\|usage\|cost' /tmp/claudia/src-tauri/src/ --include='*.rs' -l
```
