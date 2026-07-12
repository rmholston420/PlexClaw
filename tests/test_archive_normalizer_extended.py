from __future__ import annotations

from app.archive_normalizer import normalize_session, normalize_session_list


class SessionObj:
    def __init__(self):
        self.session_id = "obj-1"
        self.summary = "Object summary"
        self.custom_title = "Custom object title"
        self.last_modified = 1700000000
        self.created_at = 1600000000
        self.cwd = "/tmp/work"
        self.tag = "blue"
        self.first_prompt = "hello"
        self.git_branch = "main"
        self.file_size = 123
        self.rootSessionId = "ignored-on-object"
        self.root_session_id = "root-1"
        self.messageCount = 99
        self.message_count = 5
        self.model_name = "claude-x"


class BrokenAttrSession:
    @property
    def summary(self):
        raise RuntimeError("boom")

    @property
    def custom_title(self):
        raise RuntimeError("boom")

    @property
    def session_id(self):
        return "broken-1"


def test_normalize_session_object_input_uses_object_fields():
    out = normalize_session(SessionObj())

    assert out["id"] == "obj-1"
    assert out["session_id"] == "obj-1"
    assert out["title"] == "Custom object title"
    assert out["summary"] == "Object summary"
    assert out["tag"] == "blue"
    assert out["created_at"] == 1600000000
    assert out["updated_at"] == 1700000000
    assert out["last_modified"] == 1700000000
    assert out["cwd"] == "/tmp/work"
    assert out["root_session_id"] == "root-1"
    assert out["message_count"] == 5
    assert out["model"] == "claude-x"
    assert out["raw"]["session_id"] == "obj-1"
    assert out["raw"]["git_branch"] == "main"
    assert out["raw"]["file_size"] == 123


def test_normalize_session_falls_back_title_to_summary_then_first_prompt():
    out_summary = normalize_session(
        {
            "session_id": "s-1",
            "summary": "Summary title fallback",
        }
    )
    out_prompt = normalize_session(
        {
            "session_id": "s-2",
            "first_prompt": "Prompt title fallback",
        }
    )

    assert out_summary["title"] == "Summary title fallback"
    assert out_prompt["title"] == "Prompt title fallback"


def test_normalize_session_untitled_when_no_title_sources_exist():
    out = normalize_session({"session_id": "s-3"})

    assert out["title"] == "Untitled session"
    assert out["summary"] == ""


def test_normalize_session_uses_alias_fields_from_dict_input():
    out = normalize_session(
        {
            "id": "alias-1",
            "updatedAt": "2026-07-10T10:00:00",
            "createdAt": "2026-07-09T10:00:00",
            "name": "Alias title",
            "description": "Alias description",
            "working_directory": "/repo",
            "rootSessionId": "root-alias",
            "messageCount": 7,
            "model_name": "claude-alias",
        }
    )

    assert out["id"] == "alias-1"
    assert out["session_id"] == "alias-1"
    assert out["title"] == "Alias title"
    assert out["summary"] == "Alias description"
    assert out["cwd"] == "/repo"
    assert out["root_session_id"] == "root-alias"
    assert out["message_count"] == 7
    assert out["model"] == "claude-alias"
    assert out["updated_at"] == "2026-07-10T10:00:00"
    assert out["created_at"] == "2026-07-09T10:00:00"


def test_normalize_session_handles_attribute_errors_gracefully():
    out = normalize_session(BrokenAttrSession())

    assert out["id"] == "broken-1"
    assert out["title"] == "Untitled session"
    assert out["summary"] == ""
    assert out["raw"]["summary"] is None
    assert out["raw"]["custom_title"] is None


def test_normalize_session_list_sorts_numeric_and_iso_timestamps_desc():
    sessions = [
        {"session_id": "old-num", "updated_at": 100},
        {"session_id": "new-iso", "updated_at": "2026-07-10T12:00:00"},
        {"session_id": "mid-num", "updated_at": 200},
    ]

    out = normalize_session_list(sessions)

    assert [item["id"] for item in out] == ["new-iso", "mid-num", "old-num"]


def test_normalize_session_list_invalid_or_missing_timestamps_sort_last():
    sessions = [
        {"session_id": "good", "updated_at": "2026-07-10T12:00:00"},
        {"session_id": "bad", "updated_at": "not-a-timestamp"},
        {"session_id": "none", "updated_at": None},
    ]

    out = normalize_session_list(sessions)

    assert out[0]["id"] == "good"
    assert {out[1]["id"], out[2]["id"]} == {"bad", "none"}

def test_normalize_session_list_uses_created_at_when_updated_at_missing():
    sessions = [
        {"session_id": "older-created", "updated_at": None, "created_at": 100},
        {"session_id": "newer-created", "updated_at": None, "created_at": 200},
    ]

    out = normalize_session_list(sessions)

    assert [item["session_id"] for item in out] == [
        "newer-created",
        "older-created",
    ]


def test_normalize_session_list_none_updated_at_ties_break_by_id():
    sessions = [
        {"session_id": "b-session", "updated_at": None, "created_at": None},
        {"session_id": "a-session", "updated_at": None, "created_at": None},
    ]

    out = normalize_session_list(sessions)

    assert [item["session_id"] for item in out] == [
        "a-session",
        "b-session",
    ]

