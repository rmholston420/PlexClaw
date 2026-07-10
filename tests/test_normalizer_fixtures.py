from app.normalizer import (
    normalize_assistant_completed,
    normalize_text_delta,
    normalize_tool_completed,
    normalize_tool_started,
)


def test_text_delta_fixture():
    evt = normalize_text_delta('s1', 1, 'hello')
    assert evt.type == 'assistant.delta'
    assert evt.payload['text'] == 'hello'


def test_tool_fixture():
    evt = normalize_tool_started('s1', 2, 't1', 'bash', {'cmd': 'ls'})
    assert evt.type == 'tool.started'
    assert evt.payload['tool_name'] == 'bash'

    evt2 = normalize_tool_completed('s1', 3, 't1', 'bash', 'done')
    assert evt2.type == 'tool.completed'


def test_assistant_completed_fixture():
    evt = normalize_assistant_completed('s1', 4)
    assert evt.type == 'assistant.completed'
    assert evt.payload['stop_reason'] == 'end_turn'
