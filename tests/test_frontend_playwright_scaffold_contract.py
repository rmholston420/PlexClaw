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
    assert "test('new tab button adds a rendered session tab'" in text
    assert "#new-tab-btn" in text
    assert ".session-tab" in text
    assert "toHaveCount(before + 1)" in text


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


def test_playwright_runtime_mode_spec_exists() -> None:
    text = Path("frontend/e2e/runtime-mode.spec.js").read_text()
    assert "test('runtime mode controls are exposed in the current DOM'" in text
    assert "#runtime-mode-label" in text
    assert "#mode-manual-btn" in text
    assert "#mode-auto-btn" in text


def test_playwright_tool_search_spec_exists() -> None:
    text = Path("frontend/e2e/tool-search.spec.js").read_text()
    assert "test('tool search selector is exposed in the current DOM'" in text
    assert "#tool-search-select" in text
    assert "toBeVisible" in text
    assert "toBeEnabled" in text


def test_playwright_session_utils_spec_exists() -> None:
    text = Path("frontend/e2e/session-utils.spec.js").read_text()
    assert "test('session utility controls are exposed in the current DOM'" in text
    assert "#session-label" in text
    assert "#runtime-mode-label" in text
    assert "#tool-search-select" in text
    assert "#export-session" in text
    assert "#export-session-json" in text
    assert "#connection-status" not in text


def test_playwright_composer_spec_exists() -> None:
    text = Path("frontend/e2e/composer.spec.js").read_text()
    assert "test('composer controls are exposed in the current DOM'" in text
    assert "#composer" in text
    assert "#prompt-input" in text
    assert "#prompt-stats" in text
    assert "#send-btn" in text
    assert "#attach-file-btn" in text
    assert "#attach-file-input" in text


def test_playwright_archive_spec_exists() -> None:
    text = Path("frontend/e2e/archive.spec.js").read_text()
    assert "test('archive controls are exposed in the current DOM'" in text
    assert "#archive-list" in text
    assert "#archive-search" in text
    assert "#archive-sort" in text
    assert "#refresh-archive" in text


def test_playwright_terminal_spec_exists() -> None:
    text = Path("frontend/e2e/terminal.spec.js").read_text()
    assert "test('terminal controls are exposed in the current DOM'" in text
    assert "#terminal-toggle" in text
    assert "#terminal-drawer" in text
    assert "#terminal-clear" in text
    assert "#terminal-copy" in text
    assert "#terminal-errors-only" in text
    assert "#terminal-count" in text
    assert "#terminal-pre" in text

def test_playwright_search_modal_spec_exists() -> None:
    text = Path("frontend/e2e/search-modal.spec.js").read_text()
    assert "test('search modal opens and closes from stable controls'" in text
    assert "#open-search" in text
    assert "#search-modal" in text
    assert "#search-close" in text
    assert "aria-hidden" in text



def test_playwright_search_modal_diagnostic_spec_exists() -> None:
    text = Path("frontend/e2e/search-modal-diagnostic.spec.js").read_text()
    assert "test('diagnose search modal wiring'" in text
    assert "BEFORE=" in text
    assert "AFTER_CLICK=" in text
    assert "AFTER_DOM_CLICK=" in text

def test_playwright_cwd_modal_spec_exists() -> None:
    text = Path("frontend/e2e/cwd-modal.spec.js").read_text()
    assert "test('cwd modal opens and closes from stable controls'" in text
    assert "#cwd-pill" in text
    assert "#cwd-modal" in text
    assert "#cwd-close" in text
    assert "aria-hidden" in text

def test_playwright_modal_escape_spec_exists() -> None:
    text = Path("frontend/e2e/modal-escape.spec.js").read_text()
    assert "test('Escape closes search and cwd modals'" in text
    assert "#open-search" in text
    assert "#search-modal" in text
    assert "#cwd-pill" in text
    assert "#cwd-modal" in text
    assert "keyboard.press('Escape')" in text
def test_playwright_modal_backdrop_spec_exists() -> None:
    text = Path("frontend/e2e/modal-backdrop.spec.js").read_text()
    assert "test('backdrop click closes search and cwd modals'" in text
    assert "#open-search" in text
    assert "#search-modal" in text
    assert "#cwd-pill" in text
    assert "#cwd-modal" in text
    assert "click({ position: { x: 5, y: 5 } })" in text

def test_playwright_tab_activation_spec_exists() -> None:
    text = Path("frontend/e2e/tab-activation.spec.js").read_text()
    assert "test('clicking a session tab activates it after creating a new tab'" in text
    assert "#new-tab-btn" in text
    assert ".session-tab" in text
    assert "toHaveClass(/active/)" in text
    assert "not.toHaveClass(/active/)" in text

def test_playwright_search_focus_spec_exists() -> None:
    text = Path("frontend/e2e/search-focus.spec.js").read_text()
    assert "test('opening search modal moves focus to the modal search input'" in text
    assert "#open-search" in text
    assert "#search-input-modal" in text
    assert "toBeFocused()" in text
def test_playwright_terminal_toggle_spec_exists() -> None:
    text = Path("frontend/e2e/terminal-toggle.spec.js").read_text()
    assert "test('terminal toggle opens and closes the terminal panel'" in text
    assert "#terminal-toggle" in text
    assert "#terminal-drawer" in text
    assert "aria-hidden" in text
def test_playwright_export_controls_tabs_spec_exists() -> None:
    text = Path("frontend/e2e/export-controls-tabs.spec.js").read_text()
    assert (
        "test('export controls remain visible and enabled across tab changes'"
        in text
    )
    assert "#new-tab-btn" in text
    assert "#export-session" in text
    assert "#export-session-json" in text
    assert ".session-tab" in text
    assert "toBeEnabled()" in text
def test_playwright_search_close_spec_exists() -> None:
    text = Path("frontend/e2e/search-close.spec.js").read_text()
    assert "test('search close button closes the search modal'" in text
    assert "#open-search" in text
    assert "#search-modal" in text
    assert "#search-close" in text
    assert "aria-hidden" in text
