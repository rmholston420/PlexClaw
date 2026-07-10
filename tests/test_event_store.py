from app.event_store import DB_PATH, append_event, init_db, query_events


def test_event_store_append_and_query(tmp_path, monkeypatch):
    monkeypatch.setattr('app.event_store.DB_PATH', tmp_path / 'events.db')
    init_db()
    append_event('s1', 1, 'assistant.delta', {'text': 'hello'})
    append_event('s1', 2, 'assistant.completed', {'stop_reason': 'end_turn'})

    rows = query_events('s1')
    assert len(rows) == 2
    assert rows[0]['payload']['text'] == 'hello'


def test_event_store_filters(tmp_path, monkeypatch):
    monkeypatch.setattr('app.event_store.DB_PATH', tmp_path / 'events.db')
    init_db()
    append_event('s1', 1, 'assistant.delta', {'text': 'a'})
    append_event('s1', 2, 'tool.started', {'tool_id': '1'})
    append_event('s1', 3, 'assistant.delta', {'text': 'b'})

    rows = query_events('s1', event_type='assistant.delta', since_seq=1)
    assert len(rows) == 1
    assert rows[0]['seq'] == 3
