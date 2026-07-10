# PlexClaw Build Progress

Implemented from the build spec as a runnable vertical-slice baseline:

- FastAPI backend on port 8020
- Static frontend on port 5555
- Stable protocol envelope `0.2.0`
- Live session creation
- WebSocket prompt streaming
- Append-only SQLite event store and replay endpoints
- Archive endpoints and canonical metadata normalization
- Sidebar archive browser with search, sort, lineage grouping, continue, fork, rename, tag, and replay controls
- Interrupt route and runtime plumbing
- Tests, CI, run script, and README

This repo currently uses a mock streaming fallback if the real Claude Code SDK package is not installed.
