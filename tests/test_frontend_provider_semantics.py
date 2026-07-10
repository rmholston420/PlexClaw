from pathlib import Path


def test_provider_runtime_meta_is_rendered():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "function renderProviderRuntimeMeta()" in text
    assert "providerBaseUrl: null" in text
    assert "evt.payload?.provider_base_url || null" in text
    assert "data.provider_base_url" in text


def test_provider_change_resets_live_session():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "Provider changed from ${previousProvider} to ${name}. Start a new session to use the new route." in text
    assert "tab.sessionId = null;" in text
    assert "state.sessionId = null;" in text
    assert "syncStateToActiveTab();" in text
    assert "renderProviderRuntimeMeta();" in text
