from __future__ import annotations

from pathlib import Path


def test_frontend_runtime_badge_and_labels_present() -> None:
    html = Path("frontend/plexclaw-ui-canonical.html").read_text()
    js = Path("frontend/sdk-bridge-client.js").read_text()

    assert 'id="runtime-mode-label"' in html
    assert "function setRuntimeMode(mockMode)" in js
    assert "Mock session ready" in js
    assert "Live session ready" in js
    assert "if (data.model) state.model = data.model;" in js
    assert "if (data.provider) state.provider = data.provider;" in js
    assert "if (typeof data.mock_mode === 'boolean') setRuntimeMode(data.mock_mode);" in js
