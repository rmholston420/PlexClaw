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

def test_describe_hook_event_session_interrupted():
    assert (
        describe_hook_event("session.interrupted", {"reason": "user_interrupt"})
        == "Stop observed (user_interrupt)."
    )


def test_describe_hook_event_assistant_completed():
    assert (
        describe_hook_event("assistant.completed", {"stop_reason": "end_turn"})
        == "Assistant completed with stop reason: end_turn."
    )


def test_describe_hook_event_tool_permission_required():
    assert (
        describe_hook_event("tool.permission_required", {"tool_name": "bash"})
        == "PermissionRequest observed for bash."
    )


def test_describe_hook_event_tool_permission_decided():
    assert (
        describe_hook_event(
            "tool.permission_decided",
            {"tool_name": "read_file", "decision": "approve"},
        )
        == "PermissionDecision observed for read_file: approve."
    )


def test_describe_hook_event_tool_completed():
    assert (
        describe_hook_event("tool.completed", {"tool_name": "grep"})
        == "Tool completed: grep."
    )


def test_describe_hook_event_system_message_with_text():
    assert (
        describe_hook_event(
            "system.message",
            {"level": "warn", "text": "Run interrupted by user"},
        )
        == "Notification (warn): Run interrupted by user"
    )


def test_describe_hook_event_system_message_without_text():
    assert (
        describe_hook_event("system.message", {"level": "info"})
        == "Notification observed (info)."
    )


def test_describe_hook_event_session_failed():
    assert (
        describe_hook_event("session.failed", {})
        == "Session failure observed."
    )

