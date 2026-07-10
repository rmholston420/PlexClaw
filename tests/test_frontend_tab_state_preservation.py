from __future__ import annotations

from pathlib import Path


def test_tab_switching_preserves_per_tab_session_and_replay_state_contract() -> None:
    js = Path("frontend/sdk-bridge-client.js").read_text()

    # Tab system exists.
    assert "tabs: []" in js
    assert "activeTabId: null" in js
    assert "function currentTab()" in js
    assert "function syncStateToActiveTab()" in js
    assert "function syncActiveTabToState()" in js

    # Global state tracks active session and replay status.
    assert "sessionId: null" in js
    assert "replayMode: false" in js

    # Current global state is written into the active tab before switching away.
    assert "tab.sessionId = state.sessionId;" in js
    assert "tab.replayMode = state.replayMode;" in js

    # Switching to a tab restores session identity and replay state from that tab.
    assert "state.sessionId = tab.sessionId;" in js
    assert "state.replayMode = !!tab.replayMode;" in js

    # Tab chrome reflects whether that tab has a session attached.
    assert "status-dot ${tab.sessionId ? 'connected' : 'disconnected'}" in js
