from __future__ import annotations

from pathlib import Path


def test_run_sh_contains_hook_bootstrap_port_check_and_launch_commands() -> None:
    text = Path("run.sh").read_text()

    assert 'bash scripts/setup-git-hooks.sh' in text
    assert 'from app.port_check import blocked_ports, format_blocked_ports' in text
    assert 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8020 &' in text
    assert 'wait "$BACKEND_PID"' in text
    assert 'python -m http.server 5555 --bind 127.0.0.1' not in text


def test_run_sh_cleans_up_backend_on_exit() -> None:
    text = Path("run.sh").read_text()

    assert 'cleanup() {' in text
    assert 'kill "$BACKEND_PID" 2>/dev/null || true' in text
    assert 'trap cleanup EXIT' in text

def test_run_sh_stages_frontend_into_temp_dir_for_serving() -> None:
    text = Path("run.sh").read_text()

    assert 'FRONTEND_TMP_DIR="$(mktemp -d)"' in text
    assert 'export FRONTEND_TMP_DIR' in text
    assert 'shutil.copytree(src, dst, dirs_exist_ok=True)' in text
    assert 'cd "$FRONTEND_TMP_DIR"' in text


def test_run_sh_rewrites_sdk_bridge_cache_busting_token() -> None:
    text = Path("run.sh").read_text()

    assert 'hashlib.sha256(bridge.read_bytes()).hexdigest()[:12]' in text
    assert 'html = html.replace("sdk-bridge-client.js?v=DEV", ' in text
    assert 'f"sdk-bridge-client.js?v={digest}")' in text
    assert '[run.sh] frontend cache-bust hash:' in text


def test_run_sh_cleans_up_frontend_temp_dir_on_exit() -> None:
    text = Path("run.sh").read_text()

    assert 'rm -rf "$FRONTEND_TMP_DIR" 2>/dev/null || true' in text
