from pathlib import Path


def test_provider_runtime_meta_is_rendered():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "function renderProviderRuntimeMeta()" in text
    assert "providerBaseUrl: null" in text
    assert "evt.payload?.provider_base_url || null" in text
    assert "data.provider_base_url" in text


def test_provider_change_resets_live_session():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert (
        "Provider changed from ${previousProvider} to ${name}. "
        "Start a new session to use the new local route."
    ) in text
    assert "tab.sessionId = null;" in text
    assert "state.sessionId = null;" in text
    assert "syncStateToActiveTab();" in text
    assert "renderProviderRuntimeMeta();" in text


def test_provider_switcher_prefers_local_routes():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "function preferredProviderOrder()" in text
    assert "return ['ollama', 'vllm', 'cloud'];" in text
    assert "function chooseBestProvider(preferred)" in text
    assert "if (health.ollama?.ok) return 'ollama';" in text
    assert "if (health.vllm?.ok) return 'vllm';" in text
    assert (
        "state.provider = data.default_provider || state.provider || "
        "'ollama';"
    ) in text


def test_provider_runtime_meta_exposes_selection_reason():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "function providerSelectionReason()" in text
    assert "return 'Ollama primary selected';" in text
    assert "return 'vLLM fallback selected because Ollama is offline';" in text
    assert "return 'Cloud selected explicitly';" in text
    assert "const selectionReason = providerSelectionReason();" in text
