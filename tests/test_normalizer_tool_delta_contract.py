from __future__ import annotations

from app.normalizer import normalize_tool_delta


def test_tool_delta_can_carry_partial_text():
    evt = normalize_tool_delta("s1", 2, "t1", "chunk")
    assert evt.type == "tool.delta"
    assert evt.payload["tool_id"] == "t1"
    assert evt.payload["partial"] == "chunk"


def test_tool_delta_payload_can_be_extended_for_tool_input():
    evt = normalize_tool_delta("s1", 3, "t1", "")
    evt.payload["tool_input"] = {"cmd": "ls"}
    assert evt.payload["tool_input"] == {"cmd": "ls"}
