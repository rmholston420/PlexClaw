from app.runtime_sdk import _tool_search_env


def test_tool_search_env_empty_when_mode_missing():
    assert _tool_search_env(None) == {}


def test_tool_search_env_sets_enable_tool_search():
    assert _tool_search_env("false") == {"ENABLE_TOOL_SEARCH": "false"}
    assert _tool_search_env("auto") == {"ENABLE_TOOL_SEARCH": "auto"}
