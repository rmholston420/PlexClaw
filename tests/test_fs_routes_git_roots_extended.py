from __future__ import annotations

import pytest

import app.fs_routes as fs_routes


@pytest.mark.asyncio
async def test_git_roots_breaks_when_current_escapes_root(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    escaped = tmp_path.parent

    monkeypatch.setattr(
        fs_routes,
        "_resolve_safe_path",
        lambda start, session_id=None: (escaped, root),
    )
    monkeypatch.setattr(fs_routes, "_is_within_root", lambda a, b: a == b)

    result = await fs_routes.git_roots(
        start=str(root),
        max_depth=3,
        session_id=None,
    )

    assert result == {"root": str(root), "roots": []}
