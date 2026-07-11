from __future__ import annotations

import builtins
import importlib
import sys

import app


def test_runtime_sdk_import_fallback_when_claude_agent_sdk_missing(monkeypatch):
    real_import = builtins.__import__
    original_runtime_sdk = sys.modules.get("app.runtime_sdk")
    original_app_attr = getattr(app, "runtime_sdk", None)

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "claude_agent_sdk" or name.startswith("claude_agent_sdk."):
            raise ImportError("forced missing claude_agent_sdk for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    sys.modules.pop("app.runtime_sdk", None)
    if hasattr(app, "runtime_sdk"):
        delattr(app, "runtime_sdk")

    imported = importlib.import_module("app.runtime_sdk")
    try:
        assert imported._SDK_AVAILABLE is False
        assert imported.sdk is None
        assert imported.StreamEvent is None
        assert imported.AssistantMessage is None
        assert imported.ResultMessage is None
        assert imported.ClaudeAgentOptions is None
        assert imported.ClaudeSDKClient is None
        assert imported._sdk_list_sessions is None
        assert imported._sdk_get_session_info is None
        assert imported._sdk_get_session_messages is None
        assert imported._sdk_rename_session is None
        assert imported._sdk_tag_session is None
    finally:
        sys.modules.pop("app.runtime_sdk", None)
        if original_runtime_sdk is not None:
            sys.modules["app.runtime_sdk"] = original_runtime_sdk
            app.runtime_sdk = original_runtime_sdk
        elif original_app_attr is not None:
            app.runtime_sdk = original_app_attr
