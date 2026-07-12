from app.hooks import (
    HookContext,
    describe_hook_event,
    hook_system_message,
)


def test_describe_hook_event_session_start():
    assert (
        describe_hook_event("session.start", {})
        == "Hook observed session start."
    )


def test_describe_hook_event_session_end():
    assert (
        describe_hook_event("session.end", {})
        == "Hook observed session end."
    )


def test_describe_hook_event_pre_tool():
    assert (
        describe_hook_event("pre_tool", {"tool_name": "bash"})
        == "Hook observed pre-tool event for bash."
    )


def test_describe_hook_event_post_tool_fallback():
    assert (
        describe_hook_event("post_tool", {"tool": "read"})
        == "Hook observed post-tool event for read."
    )


def test_hook_system_message_shape():
    ctx = HookContext("s1", "pre_tool", {"tool_name": "grep"})
    payload = hook_system_message(ctx)
    assert payload["kind"] == "hook.event"
    assert payload["event_type"] == "pre_tool"
    assert "grep" in payload["message"]
    assert payload["payload"] == {"tool_name": "grep"}
