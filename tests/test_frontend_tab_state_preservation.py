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
    assert "status-dot ${isConnected ? 'connected' : 'disconnected'}" in js


def test_tab_switching_preserves_per_tab_connection_telemetry_contract() -> None:
   js = Path("frontend/sdk-bridge-client.js").read_text()

   assert "connections: 0," in js
   assert "idleSeconds: 0," in js
   assert "tab.connections = state.connections || 0;" in js
   assert "tab.idleSeconds = state.idleSeconds || 0;" in js
   assert "state.connections = tab.connections || 0;" in js
   assert "state.idleSeconds = tab.idleSeconds || 0;" in js
   assert "const isConnected = (tab.connections || 0) > 0;" in js
   assert (
      "btn.title = `Connections: ${tab.connections || 0} • Idle: "
      "${idleLabel}s`;"
  ) in js
