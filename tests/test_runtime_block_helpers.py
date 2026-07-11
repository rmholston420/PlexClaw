from __future__ import annotations

from types import SimpleNamespace

from app.runtime_sdk import (
    _block_attr,
    _block_type,
    _coerce_tool_result_output,
    _iter_message_blocks,
    build_effective_system_prompt,
)


def test_iter_message_blocks_list_content():
    msg = SimpleNamespace(content=[1, 2, 3])
    assert list(_iter_message_blocks(msg)) == [1, 2, 3]


def test_iter_message_blocks_non_list_content():
    msg = SimpleNamespace(content="hello")
    assert list(_iter_message_blocks(msg)) == []


def test_iter_message_blocks_none_content():
    msg = SimpleNamespace(content=None)
    assert list(_iter_message_blocks(msg)) == []


def test_iter_message_blocks_missing_content_attr():
    class Obj:
        pass

    assert list(_iter_message_blocks(Obj())) == []


def test_block_type_dict_with_type():
    assert _block_type({"type": "text"}) == "text"


def test_block_type_dict_without_type():
    assert _block_type({}) is None


def test_block_type_object_with_type_attr():
    assert _block_type(SimpleNamespace(type="tool_result")) == "tool_result"


def test_block_type_object_without_type_attr():
    assert _block_type(SimpleNamespace()) is None


def test_block_attr_dict_present():
    assert _block_attr({"x": 1}, "x") == 1


def test_block_attr_dict_missing_default_none():
    assert _block_attr({}, "x") is None


def test_block_attr_dict_missing_with_default():
    assert _block_attr({}, "x", "fallback") == "fallback"


def test_block_attr_object_present():
    assert _block_attr(SimpleNamespace(x=1), "x") == 1


def test_block_attr_object_missing_default_none():
    assert _block_attr(SimpleNamespace(), "x") is None


def test_block_attr_object_missing_with_default():
    assert _block_attr(SimpleNamespace(), "x", "fallback") == "fallback"


def test_coerce_tool_result_output_single_text_block_unwraps():
    content = [{"type": "text", "text": "hello"}]
    assert _coerce_tool_result_output(content) == "hello"


def test_coerce_tool_result_output_multi_block_passthrough():
    content = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
    assert _coerce_tool_result_output(content) == content


def test_coerce_tool_result_output_single_non_text_block_passthrough():
    content = [{"type": "json", "value": 1}]
    assert _coerce_tool_result_output(content) == content


def test_coerce_tool_result_output_non_list_passthrough():
    assert _coerce_tool_result_output("hello") == "hello"


def test_coerce_tool_result_output_empty_list_passthrough():
    assert _coerce_tool_result_output([]) == []


def test_coerce_tool_result_output_text_block_missing_text_key_passthrough():
    content = [{"type": "text"}]
    assert _coerce_tool_result_output(content) == content


def test_build_effective_system_prompt_without_cwd():
    prompt = build_effective_system_prompt("Base prompt", None)
    assert prompt == "Base prompt"
    assert "Runtime grounding" not in prompt


def test_build_effective_system_prompt_with_cwd():
    prompt = build_effective_system_prompt("Base prompt", "/tmp/repo")
    assert "Base prompt" in prompt
    assert "Runtime grounding" in prompt
    assert "/tmp/repo" in prompt


def test_build_effective_system_prompt_empty_cwd_treated_as_falsy():
    prompt = build_effective_system_prompt("Base prompt", "")
    assert prompt == "Base prompt"
