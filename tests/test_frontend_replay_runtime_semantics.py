from __future__ import annotations

from pathlib import Path


def test_frontend_replay_ui_keeps_runtime_and_replay_state_distinct() -> None:
    html = Path("frontend/plexclaw-ui-canonical.html").read_text()
    js = Path("frontend/sdk-bridge-client.js").read_text()

    # Replay UI affordances exist in the canonical frontend.
    assert 'id="replay-banner"' in html
    assert 'id="exit-replay"' in html

    # Replay mode is tracked separately from runtime mode.
    assert "function setReplayMode(on)" in js
    assert "state.replayMode = on;" in js
    assert "el.replayBanner.classList.toggle('visible', on);" in js

    # Opening a fresh tab clears both replay state and runtime badge state.
    assert "state.replayMode = false;" in js
    assert "setRuntimeMode(null);" in js

    # Live session creation still derives runtime state from authoritative mock_mode.
    assert (
        "if (typeof data.mock_mode === 'boolean') "
        "setRuntimeMode(data.mock_mode);"
    ) in js
