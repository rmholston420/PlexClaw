# SDK Bridge Patch Notes

This frontend binds only to the normalized bridge protocol version `0.2.0`.
It intentionally avoids depending on raw Claude SDK message object shapes.

## Frontend assumptions

- Every event arrives in a stable envelope with `type`, `session_id`, `seq`, `payload`, and `protocol_version`.
- Replay events are rendered through the exact same event handler as live WebSocket events.
- Archive rows are normalized server-side into a canonical shape.

## UI behaviors implemented

- Live session creation
- WebSocket streaming
- Assistant delta rendering
- Tool block rendering with expandable state
- Interrupt action
- Replay mode banner
- Archive browser with search, sort, lineage grouping, continue, fork, rename, tag, and replay controls
- Enter to send, Shift+Enter for newline
