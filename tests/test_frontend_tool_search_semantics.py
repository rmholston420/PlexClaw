from pathlib import Path


def test_tool_runtime_meta_is_rendered():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "toolRuntimeMeta" in text
    assert "Tools: off (custom route)" in text
    assert "Tools: default" in text
    assert "tool_search_mode" in text
    assert "tool_search_active" in text


def test_tool_search_state_is_cleared_on_provider_change():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "state.toolSearchMode = null;" in text
    assert "state.toolSearchActive = null;" in text
    assert "tool_search_mode: state.toolSearchMode" in text
