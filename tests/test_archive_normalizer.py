from app.archive_normalizer import normalize_session, normalize_session_list


def test_archive_normalizer_dict():
    raw = {
        "session_id": "abc",
        "name": "My Session",
        "description": "summary",
        "tag": "fastapi",
        "updatedAt": "2026-01-01T00:00:00Z",
        "rootSessionId": "root1",
        "num_messages": 4,
        "model_name": "claude-sonnet-4-5",
    }
    result = normalize_session(raw)
    assert result["id"] == "abc"
    assert result["title"] == "My Session"
    assert result["root_session_id"] == "root1"
    assert result["message_count"] == 4


def test_archive_list_sorted_desc_updated():
    items = [
        {"id": "a", "updated_at": "2025-01-01T00:00:00Z"},
        {"id": "b", "updated_at": "2026-01-01T00:00:00Z"},
    ]
    result = normalize_session_list(items)
    assert [x["id"] for x in result] == ["b", "a"]
