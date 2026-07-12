import tempfile
from pathlib import Path

from app import runtime_sdk as runtimesdk


class DummySession:
    def __init__(self, cwd: str):
        self.cwd = cwd


def _make_fake_repo(tmp: Path) -> None:
    (tmp / "app").mkdir()
    (tmp / "frontend").mkdir()
    (tmp / "tests").mkdir()

    (tmp / "app" / "eventstore.py").write_text("# event store\n", encoding="utf-8")
    (tmp / "app" / "hooks.py").write_text("# hooks\n", encoding="utf-8")
    (tmp / "app" / "websocketmanager.py").write_text("# ws manager\n", encoding="utf-8")
    (tmp / "app" / "normalizer.py").write_text("# normalizer\n", encoding="utf-8")
    (tmp / "app" / "archivenormalizer.py").write_text(
        "# archive normalizer\n",
        encoding="utf-8",
    )

    (tmp / "README.md").write_text(
        "PlexClaw\n\n"
        "A browser-based GUI for Claude Code and the Claude Agent SDK.\n"
        "FastAPI backend with WebSocket bridge, static HTML/JS frontend.\n",
        encoding="utf-8",
    )
    (tmp / "CLAUDE.md").write_text(
        "Project memory for Claude Code sessions.\n"
        "Describes tools, hooks, and runtime behavior.\n",
        encoding="utf-8",
    )
    (tmp / "AGENTS.md").write_text(
        "Agent definitions and subagent topology.\n",
        encoding="utf-8",
    )
    (tmp / "BUILD_STATUS.md").write_text(
        "Build status: experimental but working end-to-end.\n",
        encoding="utf-8",
    )
    (tmp / "pyproject.toml").write_text(
        "[project]\nname = 'plexclaw'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )


def test_build_repo_summary_produces_text_with_architecture_hints():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _make_fake_repo(tmp)
        session = DummySession(str(tmp))
        summary = runtimesdk._build_repo_summary(session)
        assert summary is not None
        assert "Repository root" in summary
        assert "Top-level directories" in summary
        assert "README.md" in summary
        assert "PlexClaw" in summary
        assert "Architectural hints" in summary
        assert "eventstore.py" in summary
        assert "hooks.py" in summary
        assert "websocketmanager.py" in summary
        assert "normalizer.py" in summary
        assert "archivenormalizer.py" in summary


def test_attach_repo_summary_for_repo_prompt():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _make_fake_repo(tmp)
        session = DummySession(str(tmp))
        prompt = "summarize this repo"
        combined = runtimesdk._maybe_attach_repo_summary(session, prompt)
        assert "Project summary (from filesystem inspection)" in combined
        assert "User request:" in combined
        assert prompt in combined
