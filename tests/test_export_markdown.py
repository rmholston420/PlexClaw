from app.main import _render_session_markdown


def test_render_session_markdown_prefers_final_tool_input_from_tool_delta():
    events = [
        {
            "type": "tool.started",
            "payload": {"tool_id": "t1", "tool_name": "bash", "tool_input": {}},
        },
        {
            "type": "tool.delta",
            "payload": {"tool_id": "t1", "tool_input": {"cmd": "ls -la"}},
        },
        {
            "type": "tool.completed",
            "payload": {"tool_id": "t1", "tool_name": "bash", "output": "done"},
        },
    ]

    md = _render_session_markdown("s1", events)

    assert "## Tool: bash" in md
    assert '"cmd": "ls -la"' in md
    assert "## Tool Output: bash" in md
    assert "done" in md
