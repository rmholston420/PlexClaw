

TITLE PlexClaw Build Progress - Session metadata & tab state

- Session create responses now expose `mock_mode` and `model`, matching the runtime session object and the `session.created` lifecycle event payload.
- The frontend bridge client consumes `mock_mode` and `model` from the create-session response so UI state is driven by authoritative backend metadata rather than inferred defaults.
- A replay lifecycle test now asserts that the replayed `session.created` system message includes a boolean `mock_mode` field and a model value that matches the initial create response.
- A frontend contract test now proves that `syncStateToActiveTab()` snapshots current session, replay mode, model, provider, attachments, and terminal state into the active tab object.
- A complementary frontend contract test verifies that `syncActiveTabToState()` restores `state.sessionId` and `state.replayMode` from the selected tab, preserving each tab’s own live or replay identity.
- The tab chrome status dot is covered by test, ensuring it reflects whether a tab has a bound session via `tab.sessionId` (`connected` vs `disconnected`).
- Local quality gate remains green at 57 passing tests, including backend session metadata parity, frontend bootstrap behavior, replay semantics, and tab-state preservation, with enforcement on `git push` via the repo pre-push hook.
