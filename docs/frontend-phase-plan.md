# PlexClaw frontend phase plan

## Goal

Turn PlexClaw into the most effective browser GUI for Claude Code and Claude Agent SDK workflows, while also exposing useful local LLM controls and preparing for future Rigpa-LMS plugin embedding.

## Phase 1 — Claude-native control fidelity

### Objectives
- expose Claude SDK permission modes clearly and accurately
- separate Claude-native permission mode from PlexClaw approval UX
- make runtime metadata a reliable source of truth
- expose useful local LLM settings already supported by the backend/runtime

### Deliverables
- Claude SDK permission mode selector with correct labels and persistence
- runtime metadata cards for provider route, base URL, model, cwd, runtime mode, and tool mode
- clearer local-provider settings surface for cloud, Ollama, vLLM, and custom Anthropic-compatible routes
- cleaned-up UI copy that consistently distinguishes Claude runtime state from PlexClaw UI behavior

### Exit criteria
- users can tell exactly how a session is configured at a glance
- permission changes behave predictably and are visible in the UI
- local-model routing state is inspectable without reading environment files

## Phase 2 — Session browser and archive depth

### Objectives
- make sessions a first-class browser primitive
- match the most useful session-management patterns from Claude-native tools
- improve replay and archive usability

### Deliverables
- session browser with search, filter, rename, tag, resume, fork, and export
- improved archive cards with stronger status and metadata summaries
- better replay controls and archive navigation
- clearer mapping between live sessions and archived sessions

### Exit criteria
- browsing and resuming past work is fast and reliable
- session state feels like a core part of the product, not an auxiliary feature

## Phase 3 — Coding workflow UX

### Objectives
- optimize the GUI for coding, not generic chat
- make tool use, file context, and code changes easier to inspect
- improve multi-session productivity

### Deliverables
- richer tool activity timeline and approval trace display
- diff or touched-file visibility where practical
- better prompt input ergonomics, such as slash-style actions and file-aware context helpers
- stronger multi-session status indicators and active-task visibility

### Exit criteria
- the interface helps users manage real coding work across multiple sessions
- tool actions and code changes are easier to understand than in a raw terminal stream

## Phase 4 — Frontend modularization

### Objectives
- reduce complexity from the current single-file frontend structure
- prepare the UI for long-term maintainability and faster iteration
- create clean boundaries for later embedding

### Deliverables
- modularized frontend structure, likely React + TypeScript
- separate feature modules for sessions, transcript, approvals, runtime controls, archives, and provider settings
- central client-side state model for session and runtime updates
- preserved FastAPI + WebSocket backend bridge

### Exit criteria
- frontend feature work is easier and safer
- state-heavy UI behavior is easier to reason about and test
- the UI is no longer bottlenecked by monolithic DOM scripting

## Phase 5 — Rigpa-LMS plugin mode

### Objectives
- make PlexClaw embeddable as a Rigpa-LMS plugin
- support both standalone and host-integrated operation

### Deliverables
- embeddable app shell
- host integration points for auth, routing, and container layout
- plugin-safe configuration and runtime boundaries
- documentation for standalone mode versus Rigpa-LMS mode

### Exit criteria
- PlexClaw can run both as its own app and as an embedded product surface
- host integration does not require redesigning the core UI

## Ongoing standards

Across all phases:

- keep Claude Code and Claude Agent SDK fidelity as the priority
- expose useful local LLM settings whenever they are safe and operationally meaningful
- prefer features that improve real coding workflows over features that only imitate another UI
- keep the product visually polished, but let workflow clarity drive the interface
