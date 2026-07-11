from pathlib import Path


def test_tool_search_selector_is_present_in_ui():
    html = Path("frontend/index.html").read_text()
    assert 'id="tool-search-select"' in html
    assert 'Tool search: Default' in html
    assert 'Tool search: Off' in html
    assert 'Tool search: Auto' in html
    assert 'Tool search: Auto 5%' in html
    assert 'Tool search: On' in html


def test_tool_search_selector_is_wired_to_session_state():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "toolSearchSelect" in text
    assert "state.toolSearchMode = el.toolSearchSelect?.value || null;" in text
    assert "el.toolSearchSelect.value = state.toolSearchMode || '';" in text
    assert "el.toolSearchSelect?.addEventListener('change'" in text
