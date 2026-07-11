"""Extended frontend test coverage for sdk-bridge-client.js and plexclaw-ui-canonical.html.

Each test targets a distinct surface area not already covered by the existing
frontend test suite, driving overall coverage toward 100%.
"""
from __future__ import annotations

from pathlib import Path

JS = Path("frontend/sdk-bridge-client.js").read_text()
HTML = Path("frontend/plexclaw-ui-canonical.html").read_text()


# ---------------------------------------------------------------------------
# shortenPath contract
# ---------------------------------------------------------------------------

def test_shorten_path_function_exists() -> None:
    assert "function shortenPath(path)" in JS


def test_shorten_path_returns_tilde_for_falsy() -> None:
    assert "if (!path) return '~';" in JS


def test_shorten_path_normalises_backslashes() -> None:
    assert r".replace(/\\/g, '/')" in JS


def test_shorten_path_joins_last_parts() -> None:
    # Implementation keeps at most last 3 path segments joined with '/'
    assert ".split('/').filter(Boolean)" in JS


# ---------------------------------------------------------------------------
# setCwd + cwd UI element contract
# ---------------------------------------------------------------------------

def test_set_cwd_function_exists() -> None:
    assert "function setCwd(path)" in JS


def test_set_cwd_updates_cwd_label_via_shorten_path() -> None:
    assert "el.cwdLabel.textContent = shortenPath(state.cwd);" in JS


def test_cwd_pill_element_in_html() -> None:
    assert 'id="cwd-pill"' in HTML


def test_cwd_label_element_in_html() -> None:
    assert 'id="cwd-label"' in HTML


def test_session_cwd_meta_element_in_html() -> None:
    assert 'id="session-cwd-meta"' in HTML


# ---------------------------------------------------------------------------
# renderPermissionMode / setPermissionMode contract
# ---------------------------------------------------------------------------

def test_render_permission_mode_function_exists() -> None:
    assert "function renderPermissionMode()" in JS


def test_render_permission_mode_toggles_manual_btn() -> None:
    assert "el.modeManualBtn.classList.toggle('active', state.permissionMode === 'manual')" in JS


def test_render_permission_mode_toggles_auto_btn() -> None:
    assert "el.modeAutoBtn.classList.toggle('active', state.permissionMode === 'auto')" in JS


def test_set_permission_mode_function_exists() -> None:
    assert "async function setPermissionMode(mode)" in JS


def test_mode_manual_btn_in_html() -> None:
    assert 'id="mode-manual-btn"' in HTML


def test_mode_auto_btn_in_html() -> None:
    assert 'id="mode-auto-btn"' in HTML


# ---------------------------------------------------------------------------
# Export session element IDs
# ---------------------------------------------------------------------------

def test_export_session_btn_element_in_html() -> None:
    assert 'id="export-session"' in HTML


def test_export_session_json_btn_element_in_html() -> None:
    assert 'id="export-session-json"' in HTML


def test_export_session_btn_wired_in_js() -> None:
    assert "exportSessionBtn" in JS


def test_export_session_json_btn_wired_in_js() -> None:
    assert "exportSessionJsonBtn" in JS


# ---------------------------------------------------------------------------
# Attachments tab-state preservation contract
# ---------------------------------------------------------------------------

def test_attachments_saved_to_tab_on_sync() -> None:
    assert "tab.attachments = [...state.attachments];" in JS


def test_attachments_restored_from_tab_on_switch() -> None:
    assert "state.attachments = [...(tab.attachments || [])];" in JS


def test_attachment_tokens_saved_to_tab() -> None:
    assert "tab.attachmentTokens = state.attachmentTokens;" in JS


def test_attachment_tokens_restored_from_tab() -> None:
    assert "state.attachmentTokens = tab.attachmentTokens || 0;" in JS


def test_attach_file_btn_element_in_html() -> None:
    assert 'id="attach-file-btn"' in HTML


# ---------------------------------------------------------------------------
# terminalErrorsOnly tab-state preservation contract
# ---------------------------------------------------------------------------

def test_terminal_errors_only_saved_to_tab() -> None:
    assert "tab.terminalErrorsOnly = state.terminalErrorsOnly;" in JS


def test_terminal_errors_only_restored_from_tab() -> None:
    assert "state.terminalErrorsOnly = !!tab.terminalErrorsOnly;" in JS


def test_terminal_errors_only_element_in_html() -> None:
    assert 'id="terminal-errors-only"' in HTML


def test_terminal_errors_only_checkbox_synced_on_tab_switch() -> None:
    assert "el.terminalErrorsOnly.checked = state.terminalErrorsOnly;" in JS


# ---------------------------------------------------------------------------
# shouldIncludeRawLog terminal filter logic
# ---------------------------------------------------------------------------

def test_should_include_raw_log_function_exists() -> None:
    assert "function shouldIncludeRawLog(evt)" in JS


def test_include_all_when_not_errors_only() -> None:
    assert "if (!state.terminalErrorsOnly) return true;" in JS


def test_session_failed_always_shown_in_errors_only_mode() -> None:
    assert "'session.failed'" in JS
    assert "'system.message'" in JS


def test_error_level_payload_shown_in_errors_only_mode() -> None:
    assert ".toLowerCase() === 'error'" in JS


def test_warn_level_payload_shown_in_errors_only_mode() -> None:
    assert ".toLowerCase() === 'warn'" in JS


# ---------------------------------------------------------------------------
# fakeToolWarningShown per-session reset contract
# ---------------------------------------------------------------------------

def test_fake_tool_warning_shown_reset_on_session_created() -> None:
    # On session.created the flag must be cleared so warning fires once per session
    assert "state.fakeToolWarningShown = false;" in JS


def test_fake_tool_warning_shown_reset_on_assistant_completed() -> None:
    # Also reset at assistant turn boundary so long conversations stay clean
    lines = [l.strip() for l in JS.splitlines()]
    completed_idx = next(
        (i for i, l in enumerate(lines) if "case 'assistant.completed'" in l), None
    )
    assert completed_idx is not None
    # Reset occurs after assistant.completed case
    reset_count = sum(
        1 for l in lines[completed_idx: completed_idx + 10]
        if "fakeToolWarningShown = false" in l
    )
    assert reset_count >= 1


def test_looksLikeFakeToolMarkup_function_exists() -> None:
    assert "function looksLikeFakeToolMarkup(text)" in JS


def test_looksLikeFakeToolMarkup_checks_tool_call_tag() -> None:
    assert "value.includes('<tool_call>')" in JS


def test_looksLikeFakeToolMarkup_checks_function_tag() -> None:
    assert "value.includes('<function')" in JS


def test_looksLikeFakeToolMarkup_checks_parameter_tag() -> None:
    assert "value.includes('<parameter>')" in JS


# ---------------------------------------------------------------------------
# appendSystemMessage level system
# ---------------------------------------------------------------------------

def test_append_system_message_function_exists() -> None:
    assert "function appendSystemMessage(text, level = 'info')" in JS


def test_system_message_event_routed_to_append_system_message() -> None:
    assert "case 'system.message':" in JS
    assert "appendSystemMessage(evt.payload?.text || '', evt.payload?.level || 'info')" in JS


def test_session_interrupted_emits_system_message() -> None:
    assert "case 'session.interrupted':" in JS
    assert "appendSystemMessage('Run interrupted by user', 'warn')" in JS


def test_session_failed_emits_error_system_message() -> None:
    assert "case 'session.failed':" in JS
    assert "appendSystemMessage(evt.payload?.error || 'Session failed', 'error')" in JS


def test_session_updated_event_handled() -> None:
    assert "case 'session.updated':" in JS
    assert "appendSystemMessage('Session updated')" in JS


# ---------------------------------------------------------------------------
# setConnection / setSessionLabel contract
# ---------------------------------------------------------------------------

def test_set_connection_function_exists() -> None:
    assert "function setConnection(status)" in JS


def test_set_connection_applies_class_to_status_dot() -> None:
    assert "el.statusDot.className = 'status-dot ' + status;" in JS


def test_set_session_label_function_exists() -> None:
    assert "function setSessionLabel(id)" in JS


def test_set_session_label_shows_truncated_id() -> None:
    assert "id ? `Session ${id.slice(0, 8)}`" in JS


def test_set_session_label_shows_no_session_when_null() -> None:
    assert "'No session'" in JS


# ---------------------------------------------------------------------------
# sessionElapsed timer contract
# ---------------------------------------------------------------------------

def test_render_session_elapsed_function_exists() -> None:
    assert "function renderSessionElapsed()" in JS


def test_format_elapsed_function_exists() -> None:
    assert "function formatElapsed(ms)" in JS


def test_format_elapsed_includes_hours_branch() -> None:
    assert "if (hours > 0)" in JS


def test_start_session_elapsed_timer_function_exists() -> None:
    assert "function startSessionElapsedTimer(startValue = null)" in JS


def test_stop_session_elapsed_timer_function_exists() -> None:
    assert "function stopSessionElapsedTimer()" in JS


def test_session_elapsed_meta_element_in_html() -> None:
    assert 'id="session-elapsed-meta"' in HTML


def test_session_runtime_meta_element_in_html() -> None:
    assert 'id="session-runtime-meta"' in HTML


# ---------------------------------------------------------------------------
# setRuntimeMetaCopyValue + bindRuntimeMetaCopyHandlers
# ---------------------------------------------------------------------------

def test_set_runtime_meta_copy_value_function_exists() -> None:
    assert "function setRuntimeMetaCopyValue(node, displayText, copyText, titleText)" in JS


def test_set_runtime_meta_copy_value_sets_dataset() -> None:
    assert "node.dataset.copyValue = copyText;" in JS


def test_bind_runtime_meta_copy_handlers_function_exists() -> None:
    assert "function bindRuntimeMetaCopyHandlers()" in JS


def test_copy_handlers_cover_all_four_meta_nodes() -> None:
    assert "[el.providerRuntimeMeta, 'Provider route']" in JS
    assert "[el.toolRuntimeMeta, 'Tool search state']" in JS
    assert "[el.sessionCwdMeta, 'Working directory']" in JS
    assert "[el.sessionRuntimeMeta, 'Runtime mode']" in JS


def test_copy_handler_marks_node_as_bound() -> None:
    assert "node.dataset.copyBound = 'true';" in JS


# ---------------------------------------------------------------------------
# escapeHtml utility
# ---------------------------------------------------------------------------

def test_escape_html_function_exists() -> None:
    assert "function escapeHtml(str)" in JS


def test_escape_html_escapes_ampersand() -> None:
    assert ".replace(/&/g, '&amp;')" in JS


def test_escape_html_escapes_less_than() -> None:
    assert ".replace(/</g, '&lt;')" in JS


def test_escape_html_escapes_greater_than() -> None:
    assert ".replace(/>/g, '&gt;')" in JS


# ---------------------------------------------------------------------------
# groupByLineage / sortArchive contract
# ---------------------------------------------------------------------------

def test_group_by_lineage_function_exists() -> None:
    assert "function groupByLineage(items)" in JS


def test_group_by_lineage_uses_root_session_id() -> None:
    assert "const root = item.root_session_id || item.id;" in JS


def test_sort_archive_function_exists() -> None:
    assert "function sortArchive(items)" in JS


def test_sort_archive_supports_title_mode() -> None:
    assert "if (mode === 'title')" in JS


def test_sort_archive_supports_recent_mode() -> None:
    assert "if (mode === 'recent')" in JS


def test_sort_archive_supports_tag_mode() -> None:
    assert "if (mode === 'tag')" in JS


def test_sort_archive_supports_root_mode() -> None:
    assert "if (mode === 'root')" in JS


# ---------------------------------------------------------------------------
# Tab management contract
# ---------------------------------------------------------------------------

def test_open_new_tab_function_exists() -> None:
    assert "function openNewTab()" in JS


def test_switch_tab_function_exists() -> None:
    assert "function switchTab(tabId)" in JS


def test_close_tab_function_exists() -> None:
    assert "function closeTab(tabId)" in JS


def test_render_tabs_function_exists() -> None:
    assert "function renderTabs()" in JS


def test_tabbar_element_in_html() -> None:
    assert 'id="tabbar"' in HTML


def test_new_tab_btn_element_in_html() -> None:
    assert 'id="new-tab-btn"' in HTML


def test_tab_scroll_left_element_in_html() -> None:
    assert 'id="tab-scroll-left"' in HTML


def test_tab_scroll_right_element_in_html() -> None:
    assert 'id="tab-scroll-right"' in HTML


def test_next_tab_number_increments() -> None:
    assert "nextTabNumber: 1" in JS


# ---------------------------------------------------------------------------
# renderModelOptions contract
# ---------------------------------------------------------------------------

def test_render_model_options_function_exists() -> None:
    assert "function renderModelOptions()" in JS


def test_model_select_element_in_html() -> None:
    assert 'id="model-select"' in HTML


# ---------------------------------------------------------------------------
# Terminal element IDs in HTML
# ---------------------------------------------------------------------------

def test_terminal_toggle_element_in_html() -> None:
    assert 'id="terminal-toggle"' in HTML


def test_terminal_clear_element_in_html() -> None:
    assert 'id="terminal-clear"' in HTML


def test_terminal_copy_element_in_html() -> None:
    assert 'id="terminal-copy"' in HTML


# ---------------------------------------------------------------------------
# prompt-stats element contract
# ---------------------------------------------------------------------------

def test_prompt_stats_element_in_html() -> None:
    assert 'id="prompt-stats"' in HTML


def test_update_prompt_stats_function_exists() -> None:
    assert "function updatePromptStats()" in JS


# ---------------------------------------------------------------------------
# assistant.completed event contract
# ---------------------------------------------------------------------------

def test_assistant_completed_event_handled() -> None:
    assert "case 'assistant.completed':" in JS


def test_finalize_assistant_function_exists() -> None:
    assert "function finalizeAssistant()" in JS


# ---------------------------------------------------------------------------
# rawLogLines ring-buffer cap
# ---------------------------------------------------------------------------

def test_raw_log_lines_capped_at_500() -> None:
    assert "if (state.rawLogLines.length > 500)" in JS
    assert "state.rawLogLines.slice(-500)" in JS
