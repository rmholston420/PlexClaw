from __future__ import annotations

from pathlib import Path


def test_frontend_runtime_badge_and_labels_present() -> None:
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/sdk-bridge-client.js").read_text()

    # Static smoke test: badge element and runtime-mode helper exist.
    assert 'id="runtime-mode-label"' in html
    assert "function setRuntimeMode(mockMode)" in js
    assert "Mock session ready" in js
    assert "Live session ready" in js


def test_frontend_provider_reason_meta_present() -> None:
    html = Path("frontend/index.html").read_text()
    assert 'id="provider-reason-meta"' in html


def test_frontend_runtime_meta_is_progressively_disclosed() -> None:
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/sdk-bridge-client.js").read_text()

    assert 'id="runtime-meta-toggle"' in html
    assert 'Claude session details' in html
    assert 'id="runtime-meta-panel"' in html
    assert 'Attach one UTF-8 text file up to 200KB' in html
    assert 'Attached context files' in html
    assert "function setRuntimeMetaExpanded(expanded)" in js
    assert "function bindRuntimeMetaToggle()" in js
