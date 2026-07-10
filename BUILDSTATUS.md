TITLE PlexClaw Build Progress - Runtime routing, tool search, and docs alignment

- Runtime routing and tool-search UI semantics are now implemented and documented across operator docs, release notes, and agent guidance.
- `README.md` now reflects the current 86-test state and includes a dedicated `Runtime routing & tool search` section covering provider switcher behavior, provider route metadata, tool-search state, and tool mode selector semantics.
- `CHANGELOG.md` version `0.2.0` now records centralized runtime configuration, grouped top-bar runtime metadata, and the explicit tool mode selector states.
- `AGENTS.md` now explains how runtime routing relates to Claude Agent SDK session ownership, provider routing, tool-search behavior, hook-ready runtime extension points, and archive/replay semantics for agents.
- Frontend and backend coverage now includes provider routing, create-session response parity, tool-search env control, runtime metadata rendering, replay/runtime state separation, per-tab session/replay preservation, archive replay normalization, and trusted-host/CORS config behavior.
- Local quality gate remains green at 86 passing tests, enforced on `git push` via the repo-tracked pre-push hook.
