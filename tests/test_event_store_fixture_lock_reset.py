from threading import Lock

import app.event_store as event_store


def test_event_store_fixture_resets_db_lock() -> None:
    assert hasattr(event_store, "_db_lock")
    assert isinstance(event_store._db_lock, Lock().__class__)
    fresh = Lock()
    assert event_store._db_lock is not fresh
