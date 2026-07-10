from __future__ import annotations

from pathlib import Path


def test_frontend_runtime_badge_and_labels_present() -> None:
    html = Path("frontend/plexclaw-ui-canonical.html").read_text()
    js = Path("frontend/sdk-bridge-client.js").read_text()

    # Static smoke test: badge element and runtime-mode helper exist.
    assert 'id="runtime-mode-label"' in html
    assert "function setRuntimeMode(mockMode)" in js
    assert "Mock session ready" in js
    assert "Live session ready" in js
