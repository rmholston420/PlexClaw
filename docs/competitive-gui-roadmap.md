# Competitive GUI roadmap

## Goal

Identify the strongest ideas from existing Claude Code and Claude Agent SDK GUIs, then selectively adopt the features that improve PlexClaw’s usefulness as a Claude-native, local-LLM-aware, browser-based coding environment.

## Key references

### Claude Cookbook session browser
Useful primitives:
- list sessions
- read session metadata
- rename sessions
- tag sessions
- fork sessions

Why it matters:
- provides the cleanest canonical SDK-native model for session browsing and archive behavior

### Claude Code Crew / claude-code-ui
Useful ideas:
- multi-session operational UX
- Git worktree-oriented organization
- richer browser app architecture
- real-time session state visibility
- stronger multi-pane coding workflow

Why it matters:
- shows the likely frontend direction for a more advanced PlexClaw UI

### cui
Useful ideas:
- permission grant UX
- archive and resume flows
- fork/session management
- slash command and file autocomplete
- diff-oriented coding workflow
- simultaneous streaming

Why it matters:
- best current reference for a coding-centric Claude browser UI

### Lightweight browser session/history viewers
Useful ideas:
- fast archive browsing
- search/filter/share flows
- simple viewing modes for past sessions

Why it matters:
- useful for PlexClaw archive UX and replay usability

## Features PlexClaw should prioritize

### Priority 1
- full Claude-native permission mode exposure
- session browser parity: list, search, rename, tag, fork, resume, archive
- runtime metadata clarity: provider, base URL, model, cwd, permission mode, tool mode
- useful local LLM settings exposure

### Priority 2
- parallel live sessions with clear status indicators
- richer approval tracing and tool activity visibility
- diff/touched-file visibility
- better command input UX including slash and file completion

### Priority 3
- repo/worktree-aware orchestration
- stronger multi-pane operational layout
- plugin-friendly embeddable frontend modules for Rigpa-LMS
- enhanced archive browsing, search, and sharing

## Product rule

PlexClaw should copy behaviors that make Claude Code workflows clearer, faster, or more controllable.

It should not copy UI patterns just because another tool looks modern.

## Architecture implication

As PlexClaw adopts more of these features, the frontend should move toward a componentized architecture with separate modules for:
- sessions
- transcript/timeline
- approvals
- runtime controls
- provider/local LLM settings
- archive browsing
- repo/project context

