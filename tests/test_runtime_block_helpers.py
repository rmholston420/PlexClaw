"""Unit tests for private helper functions in app/runtime_sdk.py.

Covers:
  - _iter_message_blocks with list content, non-list content, missing attr
  - _block_type for dict blocks and attribute-based blocks
  - _block_attr for dict blocks, attribute-based blocks, missing keys/attrs
  - _coerce_tool_result_output single-text unwrap and passthrough cases
  - build_effective_system_prompt with and without cwd
"""
from __future__ import annotations

from types import SimpleNamespace

from app.runtime_sdk import (
    _block_attr,
    _block_type,
    _coerce_tool_result_output,
    _iter_message_blocks,
    build_effective_system_prompt,
)


# ---------------------------------------------------------------------------
# _iter_message_blocks
# ---------------------------------------------------------------------------

def test_iter_message_blocks_list_content():
    msg = SimpleNamespace(content=["a", "b", "c"])
    assert list(_iter_message_blocks(msg)) == ["a", "b", "c"]


def test_iter_message_blocks_non_list_content_returns_empty():
    msg = SimpleNamespace(content="plain string")
    assert list(_iter_message_blocks(msg)) == []


def test_iter_message_blocks_none_content_returns_empty():
    msg = SimpleNamespace(content=None)
    assert list(_iter_message_blocks(msg)) == []


def test_iter_message_blocks_no_content_attr_returns_empty():
    msg = SimpleNamespace()  # no .content at all
    assert list(_iter_message_blocks(msg)) == []


def test_iter_message_blocks_empty_list():
    msg = SimpleNamespace(content=[])
    assert list(_iter_message_blocks(msg)) == []


# ---------------------------------------------------------------------------
# _block_type
# ---------------------------------------------------------------------------

def test_block_type_from_dict():
    assert _block_type({"type": "text"}) == "text"


def test_block_type_from_dict_missing_key():
    assert _block_type({}) is None


def test_block_type_from_object():
    block = SimpleNamespace(type="tool_use")
    assert _block_type(block) == "tool_use"


def test_block_type_from_object_missing_attr():
    block = SimpleNamespace()
    assert _block_type(block) is None


# ---------------------------------------------------------------------------
# _block_attr
# ---------------------------------------------------------------------------

def test_block_attr_from_dict_present_key():
    assert _block_attr({"id": "x1"}, "id") == "x1"


def test_block_attr_from_dict_missing_key_returns_default():
    assert _block_attr({}, "id", "MISSING") == "MISSING"


def test_block_attr_from_dict_default_is_none():
    assert _block_attr({}, "id") is None


def test_block_attr_from_object_present_attr():
    block = SimpleNamespace(tool_use_id="t42")
    assert _block_attr(block, "tool_use_id") == "t42"


def test_block_attr_from_object_missing_attr_returns_default():
    block = SimpleNamespace()
    assert _block_attr(block, "missing", "fallback") == "fallback"


def test_block_attr_from_object_default_is_none():
    block = SimpleNamespace()
    assert _block_attr(block, "nope") is None


# ---------------------------------------------------------------------------
# _coerce_tool_result_output
# ---------------------------------------------------------------------------

def test_coerce_single_text_block_unwraps_to_string():
    content = [{"type": "text", "text": "hello"}]
    assert _coerce_tool_result_output(content) == "hello"


def test_coerce_multi_block_list_is_passthrough():
    content = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
    assert _coerce_tool_result_output(content) is content


def test_coerce_single_non_text_block_is_passthrough():
    content = [{"type": "image", "source": "data"}]
    assert _coerce_tool_result_output(content) is content


def test_coerce_non_list_is_passthrough():
    assert _coerce_tool_result_output("raw string") == "raw string"
    assert _coerce_tool_result_output(None) is None
    assert _coerce_tool_result_output(42) == 42


def test_coerce_empty_list_is_passthrough():
    content: list = []
    assert _coerce_tool_result_output(content) is content


def test_coerce_text_block_without_text_key_is_passthrough():
    content = [{"type": "text"}]  # missing "text" key
    result = _coerce_tool_result_output(content)
    # The text key is absent, so the dict has no "text" — passthrough
    # The implementation returns item.get("text") which is None;
    # but the outer condition checks "text" in item, so this passes through.
    assert result is content


# ---------------------------------------------------------------------------
# build_effective_system_prompt
# ---------------------------------------------------------------------------

def test_build_effective_system_prompt_without_cwd():
    prompt = build_effective_system_prompt("You are a helper.", None)
    assert prompt.strip() == "You are a helper."


def test_build_effective_system_prompt_with_cwd_contains_cwd():
    prompt = build_effective_system_prompt("Base prompt.", "/home/user/project")
    assert "/home/user/project" in prompt


def test_build_effective_system_prompt_with_cwd_contains_base():
    prompt = build_effective_system_prompt("Base prompt.", "/tmp/repo")
    assert "Base prompt." in prompt


def test_build_effective_system_prompt_with_empty_cwd_string():
    """Empty string cwd is falsy — treated same as None (no grounding block)."""
    prompt = build_effective_system_prompt("Base.", "")
    assert "Runtime grounding" not in prompt


def test_build_effective_system_prompt_cwd_grounding_label():
    prompt = build_effective_system_prompt("Base.", "/workspace")
    assert "Runtime grounding" in prompt
