from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _make_fake_python(path: Path, log_path: Path) -> None:
    _write_executable(
        path,
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "{log_path}"
exit 0
""",
    )


def _make_fake_git(path: Path, repo_root: Path) -> None:
    _write_executable(
        path,
        f"""#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -eq 2 ] && [ "$1" = "rev-parse" ] && [ "$2" = "--show-toplevel" ]; then
  printf '%s\n' "{repo_root}"
  exit 0
fi
echo "unexpected git invocation: $*" >&2
exit 1
""",
    )


def _run_validate(
    repo_root: Path, *, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/validate.sh"],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_validate_script_uses_default_dotvenv_python(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    venv_bin = repo_root / ".venv" / "bin"
    fake_bin = tmp_path / "fake-bin"
    log_path = tmp_path / "default-python.log"

    scripts_dir.mkdir(parents=True)
    venv_bin.mkdir(parents=True)
    fake_bin.mkdir(parents=True)
    (repo_root / "app.py").write_text("print(123)\n")

    validate_src = Path("scripts/validate.sh").read_text()
    (scripts_dir / "validate.sh").write_text(validate_src)

    _make_fake_python(venv_bin / "python", log_path)
    _make_fake_git(fake_bin / "git", repo_root)

    env = os.environ.copy()
    env.pop("PYTHON_BIN", None)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = _run_validate(repo_root, env=env)

    assert result.returncode == 0, result.stderr
    assert "[validate] Using: .venv/bin/python" in result.stdout

    lines = log_path.read_text().splitlines()
    assert lines == ["-m ruff check .", "-m pytest -q"]


def test_validate_script_resolves_python_from_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    fake_bin = tmp_path / "fake-bin"
    log_path = tmp_path / "path-python.log"

    scripts_dir.mkdir(parents=True)
    fake_bin.mkdir(parents=True)
    (repo_root / "app.py").write_text("print(123)\n")

    validate_src = Path("scripts/validate.sh").read_text()
    (scripts_dir / "validate.sh").write_text(validate_src)

    _make_fake_python(fake_bin / "python3", log_path)
    _make_fake_git(fake_bin / "git", repo_root)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PYTHON_BIN"] = "python3"

    result = _run_validate(repo_root, env=env)

    assert result.returncode == 0, result.stderr
    assert f"[validate] Using: {fake_bin / 'python3'}" in result.stdout

    lines = log_path.read_text().splitlines()
    assert lines == ["-m ruff check .", "-m pytest -q"]
