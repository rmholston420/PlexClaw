from app.config import (
    DEFAULT_ALLOWED_HOSTS,
    DEFAULT_ALLOWED_ORIGINS,
    get_allowed_hosts,
    get_allowed_origins,
)


def test_get_allowed_origins_defaults(monkeypatch):
    monkeypatch.delenv("PLEXCLAW_ALLOWED_ORIGINS", raising=False)
    assert get_allowed_origins() == DEFAULT_ALLOWED_ORIGINS


def test_get_allowed_origins_parses_csv(monkeypatch):
    monkeypatch.setenv(
        "PLEXCLAW_ALLOWED_ORIGINS",
        " http://frontend.local , http://localhost:5555 ",
    )
    assert get_allowed_origins() == [
        "http://frontend.local",
        "http://localhost:5555",
    ]


def test_get_allowed_hosts_defaults(monkeypatch):
    monkeypatch.delenv("PLEXCLAW_ALLOWED_HOSTS", raising=False)
    assert get_allowed_hosts() == DEFAULT_ALLOWED_HOSTS


def test_get_allowed_hosts_parses_csv(monkeypatch):
    monkeypatch.setenv(
        "PLEXCLAW_ALLOWED_HOSTS",
        " testserver , localhost , 127.0.0.1 ",
    )
    assert get_allowed_hosts() == [
        "testserver",
        "localhost",
        "127.0.0.1",
    ]
