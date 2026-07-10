from __future__ import annotations

from pathlib import Path


def test_run_sh_contains_hook_bootstrap_port_check_and_launch_commands() -> None:
    text = Path("run.sh").read_text()

    assert 'bash scripts/setup-git-hooks.sh' in text
    assert 'from app.port_check import blocked_ports, format_blocked_ports' in text
    assert 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8020 &' in text
    assert 'python -m http.server 5555 --bind 127.0.0.1' in text


def test_run_sh_cleans_up_backend_on_exit() -> None:
    text = Path("run.sh").read_text()

    assert 'cleanup() {' in text
    assert 'kill "$BACKEND_PID" 2>/dev/null || true' in text
    assert 'trap cleanup EXIT' in text
