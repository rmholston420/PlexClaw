# PlexClaw frontend architecture direction

## Goal

PlexClaw should evolve toward the most effective browser GUI for Claude Code and Claude Agent SDK workflows, not merely imitate another product's layout.

## Product target

The frontend should optimize for:

- Claude-native sessions and archives
- Live transcript and tool-event streaming
- Permission and approval control
- Repo and worktree context
- Local/self-hosted LLM routing and settings
- Future embeddability as a Rigpa-LMS plugin

## Near-term approach

Keep improving the current frontend while feature velocity remains high.

Prioritize:
- Claude SDK permission mode fidelity
- Session browser polish
- Local LLM settings exposure
- Runtime metadata clarity
- Tool approval and activity visibility

## Migration trigger

Move to a more advanced component frontend when one or more of these become true:

- feature work is slowed by single-file frontend complexity
- transcript, approvals, settings, and archive state become difficult to reason about
- embedding into Rigpa-LMS requires clearer component boundaries
- multi-session and repo/worktree UX outgrow the current DOM structure

## Target architecture

Recommended long-term direction:

- React + TypeScript frontend
- feature modules for sessions, transcript, runtime controls, approvals, archives, and provider settings
- shared state store for live session/runtime data
- embeddable shell for standalone PlexClaw and Rigpa-LMS plugin mode
- FastAPI/WebSocket backend retained as Claude bridge and runtime layer

## Competitive references to study

Useful ideas to adapt for PlexClaw:

- Claude Cookbook session browser patterns
- Claude Code Crew / claude-code-ui multi-session operational UX
- cui-style permission, archive, and diff-oriented coding workflow
- lightweight browser history/session viewers for search and sharing
