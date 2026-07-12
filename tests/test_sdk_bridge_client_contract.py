from __future__ import annotations

from pathlib import Path


def test_sdk_bridge_client_includes_sdk_permission_mode_in_create_session_body() -> (
    None
):
    text = Path("frontend/sdk-bridge-client.js").read_text()

    assert "sdk_permission_mode: state.sdkPermissionMode || 'default'" in text


def test_cwd_confirm_prefers_manual_input_value() -> None:
    text = Path("frontend/sdk-bridge-client.js").read_text()

    assert "const manualValue = el.cwdManualInput?.value.trim() || ''" in text
    assert (
        "setCwd(manualValue || state.cwdBrowsing || state.cwdSelected || state.cwd);"
        in text
    )
