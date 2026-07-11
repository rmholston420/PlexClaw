from __future__ import annotations

from pathlib import Path


def test_playwright_package_manifest_exists() -> None:
    text = Path("frontend/package.json").read_text()
    assert '"@playwright/test"' in text
    assert '"test:e2e"' in text
    assert '"playwright.config.js"' not in text


def test_playwright_config_exists() -> None:
    text = Path("frontend/playwright.config.mjs").read_text()
    assert "defineConfig" in text
    assert "./e2e" in text
    assert "baseURL" in text
    assert "reuseExistingServer" in text


def test_playwright_smoke_spec_exists() -> None:
    text = Path("frontend/e2e/smoke.spec.js").read_text()
    assert "test('loads core frontend controls'" in text
    assert "runtime-mode-label" in text
    assert "tool-search-select" in text
    assert "provider-switcher" in text
    assert "new-tab-btn" in text
    assert "terminal-errors-only" in text


def test_playwright_tabs_spec_exists() -> None:
    text = Path("frontend/e2e/tabs.spec.js").read_text()
    assert (
        "test('new tab button diagnostic reveals runtime tab state'" in text
    )
    assert "BEFORE_RUNTIME=" in text
    assert "AFTER_RUNTIME=" in text
    assert "sessionTabCount" in text


def test_playwright_controls_spec_exists() -> None:
    text = Path("frontend/e2e/controls.spec.js").read_text()
    assert "test('observable controls match current DOM exposure'" in text
    assert "#mode-manual-btn" in text
    assert "#mode-auto-btn" in text
    assert "#cwd-pill" in text
    assert "#export-session" in text
    assert "#export-session-json" in text
    assert "#provider-switcher" in text
    assert "#model-select" in text
    assert "#terminal-errors-only" in text


def test_playwright_exports_spec_exists() -> None:
    text = Path("frontend/e2e/exports.spec.js").read_text()
    assert (
        "test('export controls expose accessible metadata in the current DOM'" in text
    )
    assert "#export-session" in text
    assert "#export-session-json" in text
    assert "aria-label" in text
    assert "markdown" in text.lower()
    assert "json" in text.lower()


def test_playwright_runtime_mode_spec_exists() -> None:
    text = Path("frontend/e2e/runtime-mode.spec.js").read_text()
    assert "test('runtime mode controls are exposed in the current DOM'" in text
    assert "#runtime-mode-label" in text
    assert "#mode-manual-btn" in text
    assert "#mode-auto-btn" in text
    assert "not.toHaveText" in text


def test_playwright_tool_search_spec_exists() -> None:
    text = Path("frontend/e2e/tool-search.spec.js").read_text()
    assert "test('tool search selector is exposed in the current DOM'" in text
    assert "#tool-search-select" in text
    assert "toBeVisible" in text
    assert "toBeEnabled" in text
