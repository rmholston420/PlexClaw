from __future__ import annotations

import types

from app import runtime_sdk as runtime


def test_iter_message_blocks_returns_content_list():
    message = types.SimpleNamespace(content=[{"type": "text"}, {"type": "tool_use"}])

    blocks = list(runtime._iter_message_blocks(message))

    assert blocks == [{"type": "text"}, {"type": "tool_use"}]


def test_iter_message_blocks_returns_empty_for_non_list():
    message = types.SimpleNamespace(content="not-a-list")

    blocks = list(runtime._iter_message_blocks(message))

    assert blocks == []


def test_block_type_prefers_dict_key():
    block = {"type": "tool_result"}

    assert runtime._block_type(block) == "tool_result"


def test_block_type_uses_attribute_when_not_dict():
    block = types.SimpleNamespace(type="text")

    assert runtime._block_type(block) == "text"


def test_block_attr_prefers_dict_key():
    block = {"tool_use_id": "t-1"}

    assert runtime._block_attr(block, "tool_use_id") == "t-1"


def test_block_attr_uses_attribute_when_not_dict():
    block = types.SimpleNamespace(tool_use_id="t-2")

    assert runtime._block_attr(block, "tool_use_id") == "t-2"


def test_block_attr_returns_default_when_missing():
    block_dict = {}
    block_obj = types.SimpleNamespace()

    assert runtime._block_attr(block_dict, "missing", default="fallback") == "fallback"
    assert runtime._block_attr(block_obj, "missing", default="fallback") == "fallback"


def test_coerce_tool_result_output_extracts_single_text_block():
    content = [{"type": "text", "text": "hello world"}]

    out = runtime._coerce_tool_result_output(content)

    assert out == "hello world"


def test_coerce_tool_result_output_leaves_non_matching_content_unchanged():
    multi = [
        {"type": "text", "text": "one"},
        {"type": "text", "text": "two"},
    ]
    wrong_type = [{"type": "json", "text": "data"}]
    missing_text = [{"type": "text"}]
    not_list = {"type": "text", "text": "hello"}
    empty_list: list = []

    assert runtime._coerce_tool_result_output(multi) is multi
    assert runtime._coerce_tool_result_output(wrong_type) is wrong_type
    assert runtime._coerce_tool_result_output(missing_text) is missing_text
    assert runtime._coerce_tool_result_output(not_list) is not_list
    assert runtime._coerce_tool_result_output(empty_list) is empty_list
