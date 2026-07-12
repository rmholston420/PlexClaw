const Bridge = (() => {
  let runtimeMetaExpanded = false;

  function setRuntimeMetaExpanded(expanded) {
    runtimeMetaExpanded = !!expanded;
    const shell = document.getElementById('runtime-meta-shell');
    const panel = document.getElementById('runtime-meta-panel');
    const toggle = document.getElementById('runtime-meta-toggle');
    if (shell) shell.classList.toggle('expanded', runtimeMetaExpanded);
    if (panel) panel.hidden = !runtimeMetaExpanded;
    if (toggle) {
      toggle.setAttribute('aria-expanded', runtimeMetaExpanded ? 'true' : 'false');
      toggle.title = runtimeMetaExpanded ? 'Hide advanced session details' : 'Show advanced session details';
    }
    if (window.lucide?.createIcons) window.lucide.createIcons();
  }

  function bindRuntimeMetaToggle() {
    const toggle = document.getElementById('runtime-meta-toggle');
    if (!toggle || toggle.dataset.bound === 'true') return;
    toggle.dataset.bound = 'true';
    toggle.addEventListener('click', () => {
      setRuntimeMetaExpanded(!runtimeMetaExpanded);
    });
  }

  const pageUrl = new URL(window.location.href);
  const wsProtocol = pageUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  const bridgeOrigin = pageUrl.origin;
  const derivedWsBase = `${wsProtocol}//${pageUrl.host}/ws`;
  const state = {
    bridgeUrl: bridgeOrigin,
    wsBase: derivedWsBase,
    protocolVersion: '0.2.0',
    sessionId: null,
   connections: 0,
   idleSeconds: 0,
    socket: null,
    model: '',
    provider: 'ollama',
   providerBaseUrl: null,
  runtimeMode: null,
  toolSearchMode: null,
  toolSearchActive: null,
  sessionStartedAt: null,
  sessionElapsedTimer: null,
    providers: {},
    providerHealth: {},
    permissionMode: 'auto',
    cwd: '',
    cwdSelected: '',
    cwdBrowsing: null,
    assistantChunkBuffer: '',
    fakeToolWarningShown: false,
    replayMode: false,
    archive: [],
    attachments: [],
    attachmentTokens: 0,
    rawLogLines: [],
    terminalOpen: false,
    terminalErrorsOnly: false,
    terminalHeight: 220,
    searchResults: [],
    pendingSearchJump: '',
    tabs: [],
    activeTabId: null,
    nextTabNumber: 1,
    lineageOpen: new Map(),
    toolEls: new Map(),
    firstToolExpanded: false,
    copiedRuntimeMetaTimeouts: new Map(),
   sdkPermissionMode: 'default',
  effectiveSessionConfig: {
    sessionId: null,
    model: null,
    provider: null,
    providerBaseUrl: null,
    permissionMode: null,
    sdkPermissionMode: null,
    toolSearchMode: null,
    toolSearchActive: null,
    cwd: null,
    runtimeMode: null,
  },
  };

  const el = {
    cwdContextLabel: document.getElementById('cwd-context-label'),
    transcript: document.getElementById('transcript'),
    welcome: document.getElementById('welcome'),
    attachmentRow: document.getElementById('attachment-row'),
    attachmentError: document.getElementById('attachment-error'),
    composer: document.getElementById('composer'),
    attachFileBtn: document.getElementById('attach-file-btn'),
    attachFileInput: document.getElementById('attach-file-input'),
    promptInput: document.getElementById('prompt-input'),
    promptStats: document.getElementById('prompt-stats'),
    sendBtn: document.getElementById('send-btn'),
    interruptBtn: document.getElementById('interrupt-btn'),
    replayCurrentBtn: document.getElementById('replay-current-btn'),
    newSessionBtn: document.getElementById('new-session'),
    statusDot: document.getElementById('status-dot'),
    connectionLabel: document.getElementById('connection-label'),
  runtimeModeLabel: document.getElementById('runtime-mode-label'),
    sessionLabel: document.getElementById('session-label'),
    cwdPill: document.getElementById('cwd-pill'),
    cwdLabel: document.getElementById('cwd-label'),
    cwdModal: document.getElementById('cwd-modal'),
    cwdBackdrop: document.getElementById('cwd-backdrop'),
    cwdClose: document.getElementById('cwd-close'),
    cwdCancel: document.getElementById('cwd-cancel'),
    cwdConfirm: document.getElementById('cwd-confirm'),
    cwdCurrentPath: document.getElementById('cwd-current-path'),
    cwdGitRoots: document.getElementById('cwd-git-roots'),
    cwdManualInput: document.getElementById('cwd-manual-input'),
    cwdBrowser: document.getElementById('cwd-browser'),
    archiveList: document.getElementById('archive-list'),
    archiveSearch: document.getElementById('archive-search'),
    archiveSort: document.getElementById('archive-sort'),
    replayBanner: document.getElementById('replay-banner'),
    exitReplay: document.getElementById('exit-replay'),
    providerSwitcher: document.getElementById('provider-switcher'),
   providerRuntimeMeta: document.getElementById('provider-runtime-meta'),
  providerReasonMeta: document.getElementById('provider-reason-meta'),
  providerBaseUrlMeta: document.getElementById('provider-base-url-meta'),
  providerBaseUrlInput: document.getElementById('provider-base-url-input'),
  providerSettingsBtn: document.getElementById('provider-settings-btn'),
  toolRuntimeMeta: document.getElementById('tool-runtime-meta'),
 sessionCwdMeta: document.getElementById('session-cwd-meta'),
 sessionRuntimeMeta: document.getElementById('session-runtime-meta'),
sessionConfigMeta: document.getElementById('session-config-meta'),
sessionElapsedMeta: document.getElementById('session-elapsed-meta'),
  toolSearchSelect: document.getElementById('tool-search-select'),
 sdkPermissionModeSelect: document.getElementById('sdk-permission-mode-select'),
    modelSelect: document.getElementById('model-select'),
    openSearchBtn: document.getElementById('open-search'),
    exportSessionBtn: document.getElementById('export-session'),
    exportSessionJsonBtn: document.getElementById('export-session-json'),
    searchModal: document.getElementById('search-modal'),
    searchBackdrop: document.getElementById('search-backdrop'),
    searchClose: document.getElementById('search-close'),
    searchInputModal: document.getElementById('search-input-modal'),
    searchResults: document.getElementById('search-results'),
    refreshArchive: document.getElementById('refresh-archive'),
    modeManualBtn: document.getElementById('mode-manual-btn'),
    modeAutoBtn: document.getElementById('mode-auto-btn'),
    terminalToggle: document.getElementById('terminal-toggle'),
    terminalDrawer: document.getElementById('terminal-drawer'),
    terminalResizeHandle: document.getElementById('terminal-resize-handle'),
    terminalErrorsOnly: document.getElementById('terminal-errors-only'),
    terminalClear: document.getElementById('terminal-clear'),
    terminalCopy: document.getElementById('terminal-copy'),
    terminalPre: document.getElementById('terminal-pre'),
    terminalCount: document.getElementById('terminal-count'),
    tabbar: document.getElementById('tabbar'),
    newTabBtn: document.getElementById('new-tab-btn'),
    tabScrollLeft: document.getElementById('tab-scroll-left'),
    tabScrollRight: document.getElementById('tab-scroll-right'),
  };

  // ---- Helpers ----
  function hideWelcome() {
    if (el.welcome) el.welcome.classList.add('hidden');
  }

  function shouldIncludeRawLog(evt) {
    if (!state.terminalErrorsOnly) return true;
    return ['session.failed', 'system.message'].includes(evt.type) ||
      evt.type.includes('error') ||
      String(evt.payload?.level || '').toLowerCase() === 'error' ||
      String(evt.payload?.level || '').toLowerCase() === 'warn';
  }

  function renderRawLog() {
    if (!el.terminalPre) return;
    const lines = state.rawLogLines.filter(item => shouldIncludeRawLog(item.evt));
    el.terminalPre.textContent = lines.map(item => item.line).join('\n');
    if (el.terminalCount) el.terminalCount.textContent = `${lines.length} lines`;
    el.terminalPre.scrollTop = el.terminalPre.scrollHeight;
  }

  function appendRawLog(evt) {
    const line = `[${new Date().toISOString()}] ${JSON.stringify(evt)}`;
    state.rawLogLines.push({ evt, line });
    if (state.rawLogLines.length > 500) state.rawLogLines = state.rawLogLines.slice(-500);
    renderRawLog();
  }

  function setTerminalOpen(open) {
    state.terminalOpen = !!open;
    el.terminalDrawer?.classList.toggle('open', state.terminalOpen);
    el.terminalToggle?.classList.toggle('active', state.terminalOpen);
  }

  function applyTerminalHeight() {
    if (!el.terminalDrawer) return;
    el.terminalDrawer.style.height = `${state.terminalHeight}px`;
  }

  function scrollBottom() {
    requestAnimationFrame(() => {
      el.transcript.scrollTop = el.transcript.scrollHeight;
    });
  }

  
function setRuntimeMode(mockMode) {
 if (!el.runtimeModeLabel) return;
 if (mockMode === true) {
   state.runtimeMode = 'mock';
   el.runtimeModeLabel.textContent = 'Mock runtime';
   el.runtimeModeLabel.className = 'badge mock';
   el.runtimeModeLabel.title = 'Using mock Claude runtime';
   renderProviderRuntimeMeta();
   return;
 }
 if (mockMode === false) {
   state.runtimeMode = 'live';
   el.runtimeModeLabel.textContent = 'Working directory';
   el.runtimeModeLabel.className = 'badge live';
   el.runtimeModeLabel.title = 'Using live Claude runtime';
   renderProviderRuntimeMeta();
   return;
 }
 state.runtimeMode = null;
 el.runtimeModeLabel.textContent = 'Unknown runtime';
 el.runtimeModeLabel.className = 'badge';
 el.runtimeModeLabel.title = 'Runtime mode';
 renderProviderRuntimeMeta();
}

function setRuntimeMetaCopyValue(node, displayText, copyText, titleText) {
  if (!node) return;
  node.textContent = displayText;
  node.dataset.copyValue = copyText;
  node.title = titleText;
  node.setAttribute('aria-label', titleText);
}

async function copyRuntimeMetaValue(node, copiedLabel) {
  if (!node) return;
  const value = node.dataset.copyValue || node.textContent || '';
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    const originalTitle = node.dataset.originalTitle || node.title || '';
    node.dataset.originalTitle = originalTitle;
    node.title = `${copiedLabel} copied`;
    node.classList.add('copied');
    const existing = state.copiedRuntimeMetaTimeouts.get(node.id);
    if (existing) clearTimeout(existing);
    const timeout = setTimeout(() => {
      node.classList.remove('copied');
      node.title = node.dataset.originalTitle || originalTitle;
      state.copiedRuntimeMetaTimeouts.delete(node.id);
    }, 1200);
    state.copiedRuntimeMetaTimeouts.set(node.id, timeout);
  } catch (err) {
    appendSystemMessage('Could not copy runtime metadata.', 'error');
  }
}

function bindRuntimeMetaCopyHandlers() {
  const bindings = [
    [el.providerRuntimeMeta, 'Provider route'],
    [el.toolRuntimeMeta, 'Tool search state'],
    [el.sessionCwdMeta, 'Working directory'],
    [el.sessionRuntimeMeta, 'Runtime mode'],
   [el.sessionConfigMeta, 'Session config'],
  ];
  bindings.forEach(([node, label]) => {
    if (!node || node.dataset.copyBound === 'true') return;
    node.dataset.copyBound = 'true';
    node.addEventListener('click', async () => {
      await copyRuntimeMetaValue(node, label);
    });
  });
}


function buildSessionConfigSummary() {
  const requested = {
    model: state.model || null,
    provider: state.provider || null,
    providerBaseUrl: state.providerBaseUrl || null,
    permissionMode: state.permissionMode || null,
    sdkPermissionMode: state.sdkPermissionMode || 'default',
    toolSearchMode: state.toolSearchMode || null,
    cwd: state.cwdSelected || state.cwd || null,
  };
  const effective = {
    model: state.effectiveSessionConfig?.model || requested.model,
    provider: state.effectiveSessionConfig?.provider || requested.provider,
    providerBaseUrl: Object.prototype.hasOwnProperty.call(state.effectiveSessionConfig || {}, 'providerBaseUrl')
      ? state.effectiveSessionConfig.providerBaseUrl
      : requested.providerBaseUrl,
    permissionMode: state.effectiveSessionConfig?.permissionMode || requested.permissionMode,
    sdkPermissionMode: state.effectiveSessionConfig?.sdkPermissionMode || requested.sdkPermissionMode,
    toolSearchMode: state.effectiveSessionConfig?.toolSearchMode || requested.toolSearchMode,
    toolSearchActive: state.effectiveSessionConfig?.toolSearchActive,
    cwd: state.effectiveSessionConfig?.cwd || requested.cwd,
    runtimeMode: state.effectiveSessionConfig?.runtimeMode || state.runtimeMode || null,
  };
  return JSON.stringify({ requested, effective }, null, 2);
}

function providerSelectionReason() {
  const health = state.providerHealth || {};
  const provider = state.provider || 'ollama';

  if (provider === 'ollama') {
    if (health.ollama?.ok === false && health.vllm?.ok) {
      return 'Ollama unavailable; vLLM fallback preferred';
    }
    return 'Ollama primary selected';
  }

  if (provider === 'vllm') {
    if (health.ollama?.ok === false) {
      return 'vLLM fallback selected because Ollama is offline';
    }
    return 'vLLM selected explicitly';
  }

  return 'Cloud selected explicitly';
}

function renderProviderRuntimeMeta() {
  const provider = state.providers[state.provider] || {};
  const label = provider.label || state.provider || 'Cloud';
  const baseUrl = state.providerBaseUrl || provider.base_url || null;

  const selectionReason = providerSelectionReason();

  setRuntimeMetaCopyValue(
    el.providerRuntimeMeta,
    label,
    `${label} — ${selectionReason}`,
    `Click to copy provider route: ${label} (${selectionReason})`
  );

  if (el.providerReasonMeta) {
    setRuntimeMetaCopyValue(
      el.providerReasonMeta,
      selectionReason,
      selectionReason,
      `Click to copy provider selection reason: ${selectionReason}`
    );
  }

  setRuntimeMetaCopyValue(
    el.providerBaseUrlMeta,
    baseUrl || 'Default',
    baseUrl || 'Default',
    `Click to copy provider base URL: ${baseUrl || 'Default'}`
  );

  if (el.providerBaseUrlInput) {
    el.providerBaseUrlInput.value = baseUrl || '';
    el.providerBaseUrlInput.placeholder =
      provider.base_url ||
      (state.provider === 'ollama'
        ? 'http://127.0.0.1:11434'
        : state.provider === 'vllm'
          ? 'http://127.0.0.1:30000'
          : 'Provider default');
    el.providerBaseUrlInput.disabled = state.provider === 'cloud';
  el.providerBaseUrlInput.title = state.provider === 'cloud'
    ? 'Cloud provider uses the Anthropic route configured by the backend; endpoint override is disabled here.'
    : 'Override the provider endpoint for this frontend session.';
  }

  if (el.sessionCwdMeta) {
    const cwdText = state.cwd || state.cwdSelected || '~';
    setRuntimeMetaCopyValue(
      el.sessionCwdMeta,
      shortenPath(cwdText),
      cwdText,
      `Click to copy working directory: ${cwdText}`
    );
  }

  if (el.sessionRuntimeMeta) {
    const runtimeText =
      state.runtimeMode === 'mock'
        ? 'Mock runtime'
        : state.runtimeMode === 'live'
          ? 'Working directory'
          : 'Unknown runtime';
    setRuntimeMetaCopyValue(
      el.sessionRuntimeMeta,
      runtimeText,
      runtimeText,
      `Click to copy runtime mode: ${runtimeText}`
    );
  }

  if (el.sessionConfigMeta) {
    const summary = buildSessionConfigSummary();
    setRuntimeMetaCopyValue(
      el.sessionConfigMeta,
      'Copy config',
      summary,
      'Click to copy session config summary'
    );
  }

  if (el.toolRuntimeMeta) {
    const mode = state.toolSearchMode;
    const active = state.toolSearchActive;
    let toolText = 'Default tools';
    let toolTitle = 'Tools: default';

    if (mode === 'auto') {
      toolText = 'Auto tools';
      toolTitle = 'Tool search is explicitly enabled in auto mode';
    } else if (mode === 'auto:5') {
      toolText = 'Auto tools 5%';
      toolTitle = 'Tool search is explicitly enabled in auto 5% mode';
    } else if (mode === 'true') {
      toolText = 'Tools enabled';
      toolTitle = 'Tool search is explicitly enabled for this session';
    } else if (mode === 'false') {
      toolText = 'Tools disabled';
      toolTitle = 'Tool search is explicitly disabled for this session';
    } else if (active === false && baseUrl) {
      toolText = 'Tools disabled';
      toolTitle = 'Tools: off (custom route)';
    } else if (active === false) {
      toolText = 'Tools disabled';
      toolTitle = 'Tool search is disabled by backend configuration';
    }

    setRuntimeMetaCopyValue(
      el.toolRuntimeMeta,
      toolText,
      toolText,
      `Click to copy tool search state: ${toolTitle}`
    );
  }

  bindRuntimeMetaCopyHandlers();

  if (el.toolSearchSelect) {
    el.toolSearchSelect.value = state.toolSearchMode || '';
    const selected = el.toolSearchSelect.options[el.toolSearchSelect.selectedIndex];
    el.toolSearchSelect.title = `Tool search mode: ${selected ? selected.textContent : 'Tool search: Default'}`;
  }
}

function setConnection(status) {
    // status: 'disconnected' | 'connecting' | 'connected' | 'error'
    el.statusDot.className = 'status-dot ' + status;
    const labels = {
      disconnected: 'Disconnected',
      connecting: 'Connecting…',
      connected: 'Connected',
      error: 'Error',
    };
    el.connectionLabel.textContent = labels[status] || status;
    el.connectionLabel.className = 'badge' + (status === 'connected' ? ' accent' : '');
  }

  function setSessionLabel(id) {
    el.sessionLabel.textContent = id ? `Session ${id.slice(0, 8)}` : 'No session';
    el.sessionLabel.className = 'badge' + (id ? ' accent' : '');
  }

  function setReplayMode(on) {
    state.replayMode = on;
    el.replayBanner.classList.toggle('visible', on);
  }

  function makeEmptyTabState() {
    const id = `tab-${state.nextTabNumber++}`;
    return {
      id,
      title: `Tab ${state.nextTabNumber - 1}`,
      sessionId: null,
     connections: 0,
     idleSeconds: 0,
      transcriptHtml: '',
      attachments: [],
      attachmentTokens: 0,
      replayMode: false,
      rawLogLines: [],
      terminalErrorsOnly: false,
      terminalOpen: false,
      terminalHeight: 220,
      cwdSelected: state.cwdSelected,
      model: state.model,
      provider: state.provider,
     providerBaseUrl: state.providerBaseUrl,
     toolSearchMode: state.toolSearchMode,
     toolSearchActive: state.toolSearchActive,
     sdkPermissionMode: state.sdkPermissionMode,
    };
  }

  function currentTab() {
    return state.tabs.find(t => t.id === state.activeTabId) || null;
  }

  function syncStateToActiveTab() {
    const tab = currentTab();
    if (!tab) return;
    tab.sessionId = state.sessionId;
   tab.connections = state.connections || 0;
   tab.idleSeconds = state.idleSeconds || 0;
    tab.transcriptHtml = el.transcript?.innerHTML || '';
    tab.attachments = [...state.attachments];
    tab.attachmentTokens = state.attachmentTokens;
    normalizePermissionState();
   tab.permissionMode = state.permissionMode;
    tab.replayMode = state.replayMode;
    tab.rawLogLines = [...state.rawLogLines];
    tab.terminalErrorsOnly = state.terminalErrorsOnly;
    tab.terminalOpen = state.terminalOpen;
    tab.terminalHeight = state.terminalHeight;
    tab.cwdSelected = state.cwdSelected;
    tab.model = state.model;
    tab.provider = state.provider;
   tab.providerBaseUrl = state.providerBaseUrl;
   tab.toolSearchMode = state.toolSearchMode;
   tab.toolSearchActive = state.toolSearchActive;
  }

  function syncActiveTabToState() {
    const tab = currentTab();
    if (!tab) return;
    state.sessionId = tab.sessionId;
   state.connections = tab.connections || 0;
   state.idleSeconds = tab.idleSeconds || 0;
    state.attachments = [...(tab.attachments || [])];
    state.attachmentTokens = tab.attachmentTokens || 0;
    state.permissionMode = tab.permissionMode || 'auto';
    state.replayMode = !!tab.replayMode;
    state.rawLogLines = [...(tab.rawLogLines || [])];
    state.terminalErrorsOnly = !!tab.terminalErrorsOnly;
    state.terminalOpen = !!tab.terminalOpen;
    state.terminalHeight = tab.terminalHeight || 220;
    state.cwdSelected = tab.cwdSelected || state.cwdSelected;
    if (state.cwdSelected) setCwd(state.cwdSelected);
    state.model = tab.model || state.model;
    state.provider = tab.provider || state.provider;
   state.providerBaseUrl = Object.prototype.hasOwnProperty.call(tab, 'providerBaseUrl') ? tab.providerBaseUrl : state.providerBaseUrl;
   state.toolSearchMode = Object.prototype.hasOwnProperty.call(tab, 'toolSearchMode') ? tab.toolSearchMode : state.toolSearchMode;
   state.toolSearchActive = Object.prototype.hasOwnProperty.call(tab, 'toolSearchActive') ? tab.toolSearchActive : state.toolSearchActive;
  state.sdkPermissionMode = Object.prototype.hasOwnProperty.call(tab, 'sdkPermissionMode') ? tab.sdkPermissionMode : (state.sdkPermissionMode || 'default');
 normalizePermissionState();

    setSessionLabel(state.sessionId);
    setReplayMode(state.replayMode);
    if (el.transcript) {
      el.transcript.innerHTML = tab.transcriptHtml || '';
    }
    state.toolEls.clear();
    state.firstToolExpanded = true;
    renderAttachments();
    updateTokenCounter();
    renderRawLog();
    renderModelOptions();
    renderProviderSwitcher();
 renderProviderRuntimeMeta();
    renderPermissionMode();
    updateTokenCounter();
    if (el.terminalErrorsOnly) el.terminalErrorsOnly.checked = state.terminalErrorsOnly;
    if (!tab.transcriptHtml && el.welcome) el.welcome.classList.remove('hidden');
  }

  function renderTabs() {
    if (!el.tabbar) return;
    const existingNew = el.newTabBtn;
    el.tabbar.querySelectorAll('.session-tab').forEach(node => node.remove());

    state.tabs.forEach((tab) => {
      const btn = document.createElement('button');
     const isConnected = (tab.connections || 0) > 0;
     const idleLabel = Number.isFinite(tab.idleSeconds) ? Number(tab.idleSeconds).toFixed(1) : '0.0';
      btn.type = 'button';
      btn.className = 'session-tab' + (tab.id === state.activeTabId ? ' active' : '');
      btn.setAttribute('data-tab-id', tab.id);
     btn.title = `Connections: ${tab.connections || 0} • Idle: ${idleLabel}s`;
      btn.innerHTML = `
        <span class="status-dot ${isConnected ? 'connected' : 'disconnected'}"></span>
        <span class="session-tab-title">${escapeHtml(tab.title)}</span>
        <span class="session-tab-close" data-close-tab="${tab.id}">×</span>
      `;
      btn.addEventListener('click', (e) => {
        if (e.target?.matches?.('[data-close-tab]')) return;
        switchTab(tab.id);
      });
      btn.querySelector('[data-close-tab]')?.addEventListener('click', (e) => {
        e.stopPropagation();
        closeTab(tab.id);
      });
      existingNew?.before(btn);
    });

    updateTabScrollButtons();
  }

  function updateTabScrollButtons() {
    if (!el.tabbar) return;
    const maxScroll = el.tabbar.scrollWidth - el.tabbar.clientWidth;
    const canScroll = maxScroll > 4;
    if (el.tabScrollLeft) el.tabScrollLeft.disabled = !canScroll || el.tabbar.scrollLeft <= 4;
    if (el.tabScrollRight) el.tabScrollRight.disabled = !canScroll || el.tabbar.scrollLeft >= maxScroll - 4;
  }

  function openNewTab() {
    syncStateToActiveTab();
    const tab = makeEmptyTabState();
    state.tabs.push(tab);
    state.activeTabId = tab.id;
    state.socket && state.socket.close();
    state.socket = null;
    state.sessionId = null;
  stopSessionElapsedTimer();
       state.providerBaseUrl = null;
       state.toolSearchMode = null;
       state.toolSearchActive = null;
    state.attachments = [];
    state.rawLogLines = [];
    state.replayMode = false;
    clearTranscript();
    renderAttachments();
    renderRawLog();
    setSessionLabel(null);
    setConnection('disconnected');
  setRuntimeMode(null);
    if (el.welcome) el.welcome.classList.remove('hidden');
    renderTabs();
  }

  function switchTab(tabId) {
    if (tabId === state.activeTabId) return;
    syncStateToActiveTab();
    if (state.socket) { try { state.socket.close(); } catch (_) {} }
    state.socket = null;
    state.activeTabId = tabId;
    syncActiveTabToState();
    if (state.sessionId) connectSocket();
    renderTabs();
  }

  function closeTab(tabId) {
    if (state.tabs.length <= 1) return;
    const idx = state.tabs.findIndex(t => t.id === tabId);
    if (idx === -1) return;
    const closingActive = state.activeTabId === tabId;
    state.tabs.splice(idx, 1);
    if (closingActive) {
      const next = state.tabs[Math.max(0, idx - 1)] || state.tabs[0];
      state.activeTabId = next.id;
      syncActiveTabToState();
      if (state.sessionId) connectSocket();
    }
    renderTabs();
  }

  function clearTranscript() {
    el.transcript.innerHTML = '';
    state.toolEls.clear();
    state.firstToolExpanded = false;
    currentAssistantEl = null;
    currentAssistantText = '';
    state.pendingSearchJump = '';
    syncStateToActiveTab();
  }


  function shortenPath(path) {
    if (!path) return '~';
    const norm = String(path).replace(/\\/g, '/');
    const parts = norm.split('/').filter(Boolean);
    if (parts.length <= 2) return norm || '/';
    return '…/' + parts.slice(-2).join('/');
  }


  function setCwd(path) {
    state.cwd = path || '~';
    state.cwdSelected = path || null;
    if (el.cwdLabel) el.cwdLabel.textContent = shortenPath(state.cwd);
    if (el.cwdCurrentPath) el.cwdCurrentPath.textContent = state.cwd;
  }

  function renderModelOptions() {
    if (!el.modelSelect) return;
    const active = state.providers[state.provider] || state.providers.cloud || { models: [] };
    const models = active.models || [];
    el.modelSelect.innerHTML = '';
    models.forEach((model) => {
      const opt = document.createElement('option');
      opt.value = model;
      opt.textContent = model;
      if (model === state.model) opt.selected = true;
      el.modelSelect.appendChild(opt);
    });
    if (!models.includes(state.model) && models.length) {
      state.model = models[0];
      el.modelSelect.value = state.model;
    }
  }



function deriveLegacyPermissionMode(sdkMode) {
  if (sdkMode === 'default') return 'manual';
  return 'auto';
}

function normalizePermissionState(target = state) {
  if (!target) return;
  target.sdkPermissionMode = target.sdkPermissionMode || 'default';
  target.permissionMode = deriveLegacyPermissionMode(target.sdkPermissionMode);
}

function renderPermissionMode() {
  if (el.modeManualBtn) el.modeManualBtn.classList.toggle('active', state.permissionMode === 'manual');
  if (el.modeAutoBtn) el.modeAutoBtn.classList.toggle('active', state.permissionMode === 'auto');
  if (el.sdkPermissionModeSelect) el.sdkPermissionModeSelect.value = state.sdkPermissionMode || 'default';
}

async function setPermissionMode(mode) {
  if (!['auto', 'manual'].includes(mode)) return;
  if (state.permissionMode === mode) return;

  state.permissionMode = mode;
  syncStateToActiveTab();
  renderPermissionMode();

  if (state.sessionId) {
    try {
      await api(`/api/sessions/${state.sessionId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          permission_mode: mode,
          sdk_permission_mode: state.sdkPermissionMode || 'default',
        }),
      });
    } catch (err) {
      appendSystemMessage('Failed to update approval mode.', 'error');
    }
  }
}

async function setSdkPermissionMode(mode) {
  const allowed = ['default', 'acceptEdits', 'bypassPermissions'];
  if (!allowed.includes(mode)) return;
  if (state.sdkPermissionMode === mode) return;

  state.sdkPermissionMode = mode;
  syncStateToActiveTab();
  renderPermissionMode();
  renderProviderRuntimeMeta();

  if (state.sessionId) {
    try {
      await api(`/api/sessions/${state.sessionId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          permission_mode: state.permissionMode,
          sdk_permission_mode: mode,
        }),
      });
    } catch (err) {
      appendSystemMessage('Failed to update Claude SDK mode.', 'error');
    }
  }
}

function preferredProviderOrder() {
  return ['ollama', 'vllm', 'cloud'];
}

function providerDisplayLabel(name, info = {}) {
  const base = info.label || name;
  if (name === 'ollama') return `${base} (primary)`;
  if (name === 'vllm') return `${base} (backup)`;
  return base;
}

function chooseBestProvider(preferred) {
  const explicit = preferred || state.provider || null;
  const health = state.providerHealth || {};

  if (explicit) {
    if (explicit === 'ollama' && health.ollama?.ok !== false) return 'ollama';
    if (explicit === 'vllm' && health.vllm?.ok !== false) return 'vllm';
    if (explicit === 'cloud') return 'cloud';
  }

  if (health.ollama?.ok) return 'ollama';
  if (health.vllm?.ok) return 'vllm';
  return explicit || 'ollama';
}

function renderProviderSwitcher() {
    if (!el.providerSwitcher) return;
    el.providerSwitcher.innerHTML = '';
    preferredProviderOrder().forEach((name) => {
      const info = state.providers[name] || { label: name };
      const health = state.providerHealth[name] || {};
      const label = providerDisplayLabel(name, info);
      const isOffline = name !== 'cloud' && health.ok === false;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'badge' + (state.provider === name ? ' accent' : '');
      btn.title = isOffline ? `${label} offline` : `${label} online`;
      btn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px">
        <span style="width:8px;height:8px;border-radius:999px;background:${isOffline ? '#6b7280' : '#22c55e'}"></span>
        <span>${label}</span>
      </span>`;
      btn.disabled = isOffline;
      btn.addEventListener('click', () => {
        const previousProvider = state.provider;
        if (previousProvider === name) return;

        state.provider = name;

        const tab = currentTab();
        if (state.sessionId && tab) {
          tab.sessionId = null;
          state.sessionId = null;
          setSessionLabel(null);
          appendSystemMessage(`Provider changed from ${previousProvider} to ${name}. Start a new session to use the new local route.`);
        }

        syncStateToActiveTab();
        renderProviderSwitcher();
        renderProviderRuntimeMeta();
        renderModelOptions();
      });
      el.providerSwitcher.appendChild(btn);
    });
  }

  async function loadProviderHealth() {
    try {
      state.providerHealth = await api('/api/providers/health');
    } catch (err) {
      console.warn('Provider health load error', err);
      state.providerHealth = {
        cloud: { ok: true },
        ollama: { ok: false },
        vllm: { ok: false },
      };
    }
    renderProviderSwitcher();
  }

 async function loadProviders() {
   try {
     const data = await api('/api/providers');
     state.providers = data.providers || {};
     state.provider = data.default_provider || state.provider || 'ollama';
     await loadProviderHealth();
     state.provider = chooseBestProvider(state.provider);
     renderModelOptions();
     renderProviderRuntimeMeta();
   } catch (err) {
     console.warn('Provider load error', err);
     state.providers = {
       ollama: { label: 'Ollama', base_url: 'http://127.0.0.1:11434', models: [] },
       vllm: { label: 'vLLM', base_url: 'http://127.0.0.1:30000', models: [] },
       cloud: { label: 'Cloud', models: ['claude-sonnet-4-5-20250929', 'claude-opus-4-5-20251101', 'claude-haiku-4-5-20251001'] },
     };
     await loadProviderHealth();
     state.provider = chooseBestProvider('ollama');
     renderModelOptions();
     renderProviderRuntimeMeta();
   }
   renderProviderSwitcher();
   renderProviderRuntimeMeta();
 }

  async function browseCwd(path = null) {
    const params = new URLSearchParams();
    if (path) params.set('path', path);
    if (state.sessionId) params.set('session_id', state.sessionId);
    const query = params.toString() ? `?${params.toString()}` : '';
    const data = await api(`/api/fs/browse${query}`);
    state.cwdBrowsing = data.path;
   renderFsContextLabel();
    if (el.cwdCurrentPath) el.cwdCurrentPath.textContent = data.path;
    if (!el.cwdBrowser) return;

    el.cwdBrowser.innerHTML = '';
    data.entries.forEach((entry) => {
      const row = document.createElement('button');
      row.className = 'cwd-entry';
      row.type = 'button';
      row.innerHTML = `
        <span class="cwd-entry-main">
          <i data-lucide="${entry.is_dir ? 'folder' : 'file-text'}"></i>
          <span class="cwd-entry-name">${escapeHtml(entry.name)}</span>
        </span>
        <span class="cwd-entry-meta">${entry.is_dir ? 'dir' : (entry.size ?? 0) + ' bytes'}</span>
      `;
      row.addEventListener('click', async () => {
        if (!entry.is_dir) return;
        let nextPath = null;
        if (entry.name === '..') {
          const current = data.path.replace(/\/+$/, '');
          nextPath = current.slice(0, current.lastIndexOf('/')) || '/';
        } else {
          nextPath = data.path.replace(/\/+$/, '') + '/' + entry.name;
        }
        await browseCwd(nextPath);
      });
      el.cwdBrowser.appendChild(row);
    });
    const cwdIconNodes = el.cwdBrowser.querySelectorAll('[data-lucide]');
    if (window.lucide && typeof window.lucide.createIcons === 'function' && cwdIconNodes.length) {
      window.lucide.createIcons({ nodes: cwdIconNodes });
    }
  }

  async function loadGitRoots() {
    const query = state.sessionId ? `?session_id=${encodeURIComponent(state.sessionId)}` : '';
    const data = await api(`/api/fs/git-roots${query}`);
    if (!el.cwdGitRoots) return;
    el.cwdGitRoots.innerHTML = '';
    (data.roots || []).forEach((root) => {
      const chip = document.createElement('button');
      chip.className = 'cwd-chip';
      chip.type = 'button';
      chip.textContent = root;
      chip.addEventListener('click', async () => {
        await browseCwd(root);
      });
      el.cwdGitRoots.appendChild(chip);
    });
  }

  function renderFsContextLabel() {
    if (!el.cwdContextLabel) return;
    const sessionId = state.sessionId || null;
    const cwd = state.cwdBrowsing || state.cwdSelected || '';
    if (!sessionId && !cwd) {
      el.cwdContextLabel.textContent = '';
      el.cwdContextLabel.hidden = true;
      return;
    }
    const parts = [];
    if (sessionId) parts.push(`session ${sessionId.slice(0, 8)}`);
    if (cwd) parts.push(`cwd ${cwd}`);
    el.cwdContextLabel.textContent = `Filesystem view for ${parts.join(' · ')}`;
    el.cwdContextLabel.hidden = false;
  }

  async function initCwd() {
    try {
      const query = state.sessionId ? `?session_id=${encodeURIComponent(state.sessionId)}` : '';
      const fsData = await api(`/api/fs/browse${query}`);
      const gitData = await api(`/api/fs/git-roots${query}`);
      const roots = gitData.roots || [];
      const initial = roots[0] || fsData.root || fsData.path || '';
      setCwd(initial);
      state.cwdSelected = initial;
      state.cwdBrowsing = initial;
      renderFsContextLabel();
      if (el.cwdCurrentPath) el.cwdCurrentPath.textContent = initial;
    } catch (err) {
      console.warn('CWD init error', err);
    }
  }

  function openCwdModal() {
    el.cwdModal.classList.remove('hidden');
    el.cwdModal.setAttribute('aria-hidden', 'false');
    if (el.cwdManualInput) el.cwdManualInput.value = state.cwdSelected || state.cwd || '';
    loadGitRoots().catch(console.error);
    browseCwd(state.cwdSelected || state.cwd || state.cwdBrowsing || null).catch(console.error);
  }

  function closeCwdModal() {
    el.cwdModal.classList.add('hidden');
    el.cwdModal.setAttribute('aria-hidden', 'true');
  }

  function openSearchModal() {
    el.searchModal?.classList.remove('hidden');
    el.searchModal?.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(() => el.searchInputModal?.focus());
    renderSearchResults();
  }

  
  function safeCreateIcons(nodes) {
    if (!nodes) return;
    if (!window.lucide || typeof window.lucide.createIcons !== 'function') return;
    window.lucide.createIcons({ nodes });
  }

function closeSearchModal() {
    el.searchModal?.classList.add('hidden');
    el.searchModal?.setAttribute('aria-hidden', 'true');
  }


  

function bindStableUiHandlers() {
   if (el.newTabBtn && !el.newTabBtn.dataset.bound) {
     el.newTabBtn.addEventListener('click', () => openNewTab());
     el.newTabBtn.dataset.bound = 'true';
   }

   if (el.cwdClose && !el.cwdClose.dataset.bound) {
     el.cwdClose.addEventListener('click', () => closeCwdModal());
     el.cwdClose.dataset.bound = 'true';
   }

   if (el.cwdCancel && !el.cwdCancel.dataset.bound) {
     el.cwdCancel.addEventListener('click', () => closeCwdModal());
     el.cwdCancel.dataset.bound = 'true';
   }

   if (el.cwdBackdrop && !el.cwdBackdrop.dataset.bound) {
     el.cwdBackdrop.addEventListener('click', () => closeCwdModal());
     el.cwdBackdrop.dataset.bound = 'true';
   }

   if (el.openSearchBtn && !el.openSearchBtn.dataset.bound) {
     el.openSearchBtn.addEventListener('click', () => openSearchModal());
     el.openSearchBtn.dataset.bound = 'true';
   }

   if (el.searchClose && !el.searchClose.dataset.bound) {
     el.searchClose.addEventListener('click', () => closeSearchModal());
     el.searchClose.dataset.bound = 'true';
   }

   if (el.searchBackdrop && !el.searchBackdrop.dataset.bound) {
     el.searchBackdrop.addEventListener('click', () => closeSearchModal());
     el.searchBackdrop.dataset.bound = 'true';
   }

   if (el.sdkPermissionModeSelect && !el.sdkPermissionModeSelect.dataset.bound) {
     el.sdkPermissionModeSelect.addEventListener('change', (e) => {
       setSdkPermissionMode(e.target.value);
     });
     el.sdkPermissionModeSelect.dataset.bound = 'true';
   }
}


  function renderSearchResults() {
    if (!el.searchResults) return;
    const query = el.searchInputModal?.value?.trim() || '';
    if (!state.searchResults?.length) {
      el.searchResults.innerHTML = `<div class="search-empty">${query ? 'No matching sessions found.' : 'Type to search across sessions.'}</div>`;
      return;
    }

    const groups = new Map();
    state.searchResults.forEach((item) => {
      const key = item.session_id || 'unknown';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });

    el.searchResults.innerHTML = Array.from(groups.entries()).map(([sessionId, items]) => {
      const title = items[0]?.session_title || `Session ${sessionId.slice(0, 8)}`;
      return `
        <div class="search-group">
          <div class="search-group-title">${escapeHtml(title)} · ${items.length} match${items.length === 1 ? '' : 'es'}</div>
          ${items.map((item) => `
            <button class="search-result" type="button" data-search-session="${escapeHtml(item.session_id || '')}" data-search-snippet="${escapeHtml(item.snippet || '')}">
              <div class="search-result-meta">${escapeHtml(item.role || 'event')} · ${escapeHtml(item.created_at || '')}</div>
              <div>${escapeHtml(item.snippet || '')}</div>
            </button>
          `).join('')}
        </div>
      `;
    }).join('');

    el.searchResults.querySelectorAll('[data-search-session]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-search-session');
        if (!id) return;
        state.pendingSearchJump = btn.getAttribute('data-search-snippet') || el.searchInputModal?.value || '';
        closeSearchModal();
        await replaySession(id, 'archive');
      });
    });
  }

  async function runSessionSearch() {
    const query = el.searchInputModal?.value?.trim() || '';
    if (!query) {
      state.searchResults = [];
      renderSearchResults();
      return;
    }

    try {
      state.searchResults = await api(`/api/search?q=${encodeURIComponent(query)}`);
    } catch (err) {
      appendSystemMessage(`Search failed: ${err.message || err}`, 'error');
      state.searchResults = [];
    }
    renderSearchResults();
  }


  // ---- Markdown-lite renderer ----
  async function exportCurrentSession(format = 'md') {
    if (!state.sessionId) {
      appendSystemMessage('No active session to export.', 'error');
      return;
    }

    const safeFormat = format === 'json' ? 'json' : 'md';
    const ext = safeFormat === 'json' ? 'json' : 'md';

    try {
      const response = await fetch(`/api/sessions/${encodeURIComponent(state.sessionId)}/export?format=${safeFormat}`);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Export failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session-${state.sessionId.slice(0, 8)}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      appendSystemMessage(`Export failed: ${err.message || err}`, 'error');
    }
  }


  function renderMarkdown(text) {
    const div = document.createElement('div');
    // Split on code fences first
    const rawText = String(text);
    const fenceCount = (rawText.match(/```/g) || []).length;
    const normalizedText = fenceCount % 2 === 1 ? rawText + '\n\n```' : rawText;
    const parts = normalizedText.split(/(```[\s\S]*?```)/g);
    parts.forEach(part => {
      if (part.startsWith('```')) {
        const lines = part.slice(3).split('\n');
        const lang = lines.shift() || '';
        const code = lines.slice(0, -1).join('\n');
        const pre = document.createElement('pre');
        const codeEl = document.createElement('code');
        if (lang) codeEl.setAttribute('class', `language-${lang}`);
        codeEl.textContent = code;
        pre.appendChild(codeEl);
        div.appendChild(pre);
      } else {
        // Inline code
        const p = document.createElement('p');
        p.innerHTML = part
          .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
          .replace(/`([^`]+)`/g, '<code>$1</code>')
          .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
          .replace(/\*([^*]+)\*/g, '<em>$1</em>');
        if (p.innerHTML.trim()) div.appendChild(p);
      }
    });
    return div;
  }

  // ---- Tool icon picker ----
  const TOOL_ICONS = {
    bash: 'terminal',
    computer: 'monitor',
    str_replace_editor: 'file-pen-line',
    str_replace_based_edit_tool: 'file-pen-line',
    write_file: 'file-plus',
    read_file: 'file-text',
    list_files: 'folder-open',
    search_files: 'search',
    glob: 'folder-search',
    grep: 'search-code',
    web_search: 'globe',
    web_fetch: 'download',
    browser_action: 'chrome',
    case "system.message":
        if (event.payload?.kind === "hook.event") renderHookEvent(event.payload);
        break;

      default: 'zap',
  };

  function toolIcon(name) {
    const key = Object.keys(TOOL_ICONS).find(k => name && name.toLowerCase().includes(k)) || 'default';
    return TOOL_ICONS[key];
  }

  // ---- Rendering ----
  let currentAssistantEl = null;
  let currentAssistantText = '';

  function appendAssistantDelta(text) {
    hideWelcome();
    if (!currentAssistantEl) {
      currentAssistantEl = document.createElement('div');
      currentAssistantEl.className = 'msg assistant streaming';
      tagSearchableNode(currentAssistantEl, '');
      el.transcript.appendChild(currentAssistantEl);
    }
    currentAssistantText += text;
    tagSearchableNode(currentAssistantEl, currentAssistantText);
    // Simple incremental rendering — full re-render on each delta is expensive for large outputs;
    // use textContent streaming then do a final markdown pass on completion
    currentAssistantEl.textContent = currentAssistantText;
    scrollBottom();
  }

  function finalizeAssistant() {
    if (currentAssistantEl) {
      currentAssistantEl.classList.remove('streaming');
      tagSearchableNode(currentAssistantEl, currentAssistantText);
      // Final pass: render markdown
      currentAssistantEl.innerHTML = '';
      currentAssistantEl.appendChild(renderMarkdown(currentAssistantText));
      currentAssistantEl = null;
      currentAssistantText = '';
      scrollBottom();
    }
  }

  function appendSystemMessage(text, level = 'info') {
    hideWelcome();
    const div = document.createElement('div');
    div.className = 'system-msg' + (level !== 'info' ? ` ${level}` : '');
    div.textContent = text;
    tagSearchableNode(div, text);
    el.transcript.appendChild(div);
    scrollBottom();
  }

  function getOrCreateTool(toolId, toolName) {
    let block = state.toolEls.get(toolId);
    if (block) return block;

    hideWelcome();

    // Finalize any streaming assistant message before a tool block
    if (currentAssistantEl) finalizeAssistant();

    block = document.createElement('div');
    block.className = 'tool-block running';
    const autoExpand = !state.firstToolExpanded;
    state.firstToolExpanded = true;
    if (autoExpand) block.classList.add('expanded');

    const icon = toolIcon(toolName);

    block.innerHTML = `
      <div class="tool-shimmer"></div>
      <div class="tool-header">
        <i data-lucide="${icon}" class="tool-icon"></i>
        <span class="tool-title">${escapeHtml(toolName || 'tool')}</span>
        <span class="tool-status-badge">running</span>
        <i data-lucide="chevron-right" class="tool-chevron" style="width:16px;height:16px"></i>
      </div>
      <div class="tool-body">
        <div class="tool-body-section" id="tool-input-${toolId}">
          <div class="tool-label">Input</div>
          <pre></pre>
        </div>
      </div>
    `;

    block.querySelector('.tool-header').addEventListener('click', () => {
      block.classList.toggle('expanded');
    });

    el.transcript.appendChild(block);
    safeCreateIcons([block]);
    state.toolEls.set(toolId, block);
    scrollBottom();
    return block;
  }


  function sendToolDecision(decision, toolId) {
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return;
    state.socket.send(JSON.stringify({ type: decision, tool_id: toolId }));
  }


  function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;');
}


  function normalizeSearchText(value) {
    return String(value || '').toLowerCase().replace(/\s+/g, ' ').trim();
  }

  function looksLikeFakeToolMarkup(text) {
    const value = String(text || '');
    if (!value) return false;
    return (
      value.includes('<tool_call>') ||
      value.includes('</tool_call>') ||
      value.includes('<function') ||
      value.includes('</function>') ||
      value.includes('<parameter>') ||
      value.includes('</parameter>') ||
      value.includes('<parameter=') ||
      value.includes('</parameter') ||
      value.includes('=Write>') ||
      value.includes('=Read>') ||
      value.includes('=Edit>') ||
      value.includes('=Bash>') ||
      value.includes('=Grep>') ||
      value.includes('=Glob>') ||
      value.includes('=LS>')
    );
  }

  function flushAssistantChunkBuffer(force = false) {
    const value = state.assistantChunkBuffer || '';
    if (!value) return;

    if (looksLikeFakeToolMarkup(value)) {
      state.assistantChunkBuffer = '';
      finalizeAssistant();
      if (!state.fakeToolWarningShown) {
        appendSystemMessage('Suppressed fake tool-call markup emitted as assistant text', 'warn');
        state.fakeToolWarningShown = true;
      }
      return;
    }

    const holdBack = force ? 0 : 24;
    if (!force && value.length <= holdBack) return;

    const safeText = force ? value : value.slice(0, -holdBack);
    state.assistantChunkBuffer = force ? '' : value.slice(-holdBack);

    if (safeText) appendAssistantDelta(safeText);
  }


  function tagSearchableNode(node, text) {
    if (!node) return;
    node.dataset.searchText = normalizeSearchText(text);
  }

  function formatElapsed(ms) {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
      return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  function renderSessionElapsed() {
    if (!el.sessionElapsedMeta) return;
    if (!state.sessionStartedAt) {
      el.sessionElapsedMeta.textContent = '--:--';
      el.sessionElapsedMeta.title = 'Click to copy elapsed session time';
      return;
    }
    const elapsed = formatElapsed(Date.now() - state.sessionStartedAt);
    el.sessionElapsedMeta.textContent = elapsed;
    el.sessionElapsedMeta.title = `Click to copy elapsed session time: ${elapsed}`;
  }

  function stopSessionElapsedTimer() {
    if (state.sessionElapsedTimer) {
      window.clearInterval(state.sessionElapsedTimer);
      state.sessionElapsedTimer = null;
    }
    state.sessionStartedAt = null;
    renderSessionElapsed();
  }

  function startSessionElapsedTimer(startValue = null) {
    if (state.sessionElapsedTimer) {
      window.clearInterval(state.sessionElapsedTimer);
      state.sessionElapsedTimer = null;
    }
    const parsed = startValue ? Date.parse(startValue) : NaN;
    state.sessionStartedAt = Number.isFinite(parsed) ? parsed : Date.now();
    renderSessionElapsed();
    state.sessionElapsedTimer = window.setInterval(renderSessionElapsed, 1000);
  }

  function jumpToPendingSearchHit() {
    const needle = normalizeSearchText(state.pendingSearchJump);
    if (!needle || !el.transcript) return;

    const nodes = Array.from(el.transcript.querySelectorAll('[data-search-text]'));
    const match = nodes.find((node) => (node.dataset.searchText || '').includes(needle));
    state.pendingSearchJump = '';

    if (!match) return;
    match.scrollIntoView({ behavior: 'smooth', block: 'center' });
    match.classList.remove('search-hit-flash');
    void match.offsetWidth;
    match.classList.add('search-hit-flash');
    window.setTimeout(() => match.classList.remove('search-hit-flash'), 2200);
  }

  function renderEvent(evt) {
    appendRawLog(evt);
    switch (evt.type) {
      case 'session.created':
      case 'session.ready':
       if (evt.payload?.provider) state.provider = evt.payload.provider;
       state.providerBaseUrl = evt.payload?.provider_base_url || null;
      state.toolSearchMode = evt.payload?.tool_search_mode ?? null;
      state.toolSearchActive = Object.prototype.hasOwnProperty.call(evt.payload || {}, 'tool_search_active')
        ? Boolean(evt.payload.tool_search_active)
        : null;
      state.effectiveSessionConfig = {
      sessionId: state.sessionId || null,
      model: evt.payload?.model || state.model || null,
      provider: evt.payload?.provider || state.provider || null,
      providerBaseUrl: Object.prototype.hasOwnProperty.call(evt.payload || {}, 'provider_base_url')
        ? evt.payload.provider_base_url
        : null,
      permissionMode: state.permissionMode || null,
      sdkPermissionMode: state.sdkPermissionMode || 'default',
      toolSearchMode: Object.prototype.hasOwnProperty.call(evt.payload || {}, 'tool_search_mode')
        ? evt.payload.tool_search_mode
        : null,
      toolSearchActive: Object.prototype.hasOwnProperty.call(evt.payload || {}, 'tool_search_active')
        ? Boolean(evt.payload.tool_search_active)
        : null,
      cwd: state.cwd || state.cwdSelected || null,
      runtimeMode: typeof evt.payload?.mock_mode === 'boolean'
        ? (evt.payload.mock_mode ? 'mock' : 'live')
        : null,
    };
   renderProviderRuntimeMeta();
        const mockMode = Boolean(evt.payload?.mock_mode);
      appendSystemMessage(`${mockMode ? 'Mock session ready' : 'Live session ready'} (${evt.payload?.model || state.model})`);
      setRuntimeMode(mockMode);
    startSessionElapsedTimer(evt.payload?.created_at || null);
      state.assistantChunkBuffer = '';
      state.fakeToolWarningShown = false;
        break;
      case 'session.updated':
        appendSystemMessage('Session updated');
        break;
      case 'assistant.delta': {
        const chunk = evt.payload?.text || '';
        state.assistantChunkBuffer = `${state.assistantChunkBuffer || ''}${chunk}`;
        flushAssistantChunkBuffer(false);
        break;
      }
      case 'assistant.completed':
        flushAssistantChunkBuffer(true);
        finalizeAssistant();
        state.fakeToolWarningShown = false;
        break;
      case 'tool.started': {
        const block = getOrCreateTool(evt.payload?.tool_id, evt.payload?.tool_name || 'tool');
        block.classList.remove('pending', 'done', 'error');
        block.classList.add('running');
        const badge = block.querySelector('.tool-status-badge');
        if (badge) badge.textContent = 'running';
        const inputSection = block.querySelector(`#tool-input-${evt.payload?.tool_id} pre`);
        if (inputSection) {
          inputSection.textContent = '[hidden in transcript]';
        }
        break;
      }
      case 'tool.delta': {
        const block = getOrCreateTool(evt.payload?.tool_id, 'tool');

        if (evt.payload?.tool_input !== undefined) {
          const inputSection = block.querySelector(`#tool-input-${evt.payload?.tool_id} pre`);
          if (inputSection) {
            inputSection.textContent = '[hidden in transcript]';
          }
        }

        if (evt.payload?.partial) {
          let outputSection = block.querySelector('.tool-output-section');
          if (!outputSection) {
            outputSection = document.createElement('div');
            outputSection.className = 'tool-body-section tool-output-section';
            outputSection.innerHTML = '<div class="tool-label">Output</div><pre></pre>';
            block.querySelector('.tool-body').appendChild(outputSection);
          }
          outputSection.querySelector('pre').textContent += evt.payload.partial;
        }
        break;
      }
      case 'tool.completed': {
        const block = getOrCreateTool(evt.payload?.tool_id, evt.payload?.tool_name || 'tool');
        block.classList.remove('running', 'pending');
        block.classList.add(evt.payload?.is_error ? 'error' : 'done');
        const badge = block.querySelector('.tool-status-badge');
        if (badge) badge.textContent = evt.payload?.is_error ? 'error' : 'done';
        let outputSection = block.querySelector('.tool-output-section');
        if (!outputSection && evt.payload?.output != null) {
          outputSection = document.createElement('div');
          outputSection.className = 'tool-body-section tool-output-section';
          outputSection.innerHTML = '<div class="tool-label">Output</div><pre></pre>';
          block.querySelector('.tool-body').appendChild(outputSection);
        }
        if (outputSection && evt.payload?.output != null) {
          const out = typeof evt.payload.output === 'string'
            ? evt.payload.output
            : JSON.stringify(evt.payload.output, null, 2);
          outputSection.querySelector('pre').textContent = out;
          tagSearchableNode(block, `${evt.payload?.tool_name || 'tool'} ${out}`);
        }
        scrollBottom();
        break;
      }
      case 'tool.permission_required': {
      const block = getOrCreateTool(evt.payload?.tool_id, evt.payload?.tool_name || 'tool');
      block.classList.remove('running', 'done', 'error');
      block.classList.add('pending', 'expanded');
      const badge = block.querySelector('.tool-status-badge');
      if (badge) badge.textContent = 'pending';

      let approvalSection = block.querySelector('.tool-approval-section');
      if (!approvalSection) {
        approvalSection = document.createElement('div');
        approvalSection.className = 'tool-body-section tool-approval-section';
        approvalSection.innerHTML = `
          <div class="tool-label">Approval required</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="card-btn primary" data-approve-tool="${evt.payload?.tool_id}">Approve</button>
            <button class="card-btn" data-reject-tool="${evt.payload?.tool_id}">Reject</button>
          </div>
        `;
        block.querySelector('.tool-body').appendChild(approvalSection);
      }

      const approveBtn = approvalSection.querySelector(`[data-approve-tool="${evt.payload?.tool_id}"]`);
      const rejectBtn = approvalSection.querySelector(`[data-reject-tool="${evt.payload?.tool_id}"]`);

      if (approveBtn) {
        approveBtn.onclick = () => {
          sendToolDecision('approve', evt.payload?.tool_id);
          if (badge) badge.textContent = 'running';
          block.classList.remove('pending');
          block.classList.add('running');
          approvalSection.remove();
        };
      }
      if (rejectBtn) {
        rejectBtn.onclick = () => {
          sendToolDecision('reject', evt.payload?.tool_id);
          if (badge) badge.textContent = 'rejected';
          block.classList.remove('pending', 'running');
          block.classList.add('error');
          approvalSection.remove();
        };
      }

      scrollBottom();
      break;
    }
      case 'tool.permission_decided': {
      const toolId = evt.payload?.tool_id;
      const decision = evt.payload?.decision || 'unknown';
      const toolName = evt.payload?.tool_name || 'tool';
      const block = getOrCreateTool(toolId, toolName);

      const approvalSection = block.querySelector('.tool-approval-section');
      if (approvalSection) approvalSection.remove();

      block.classList.remove('pending');
      const badge = block.querySelector('.tool-status-badge');

      if (decision === 'approve') {
        if (badge) badge.textContent = 'approved';
        block.classList.remove('error');
        block.classList.add('running');
      } else if (decision === 'reject') {
        if (badge) badge.textContent = 'rejected';
        block.classList.remove('running');
        block.classList.add('error');
      } else {
        if (badge) badge.textContent = decision;
      }

      let decisionSection = block.querySelector('.tool-decision-section');
      if (!decisionSection) {
        decisionSection = document.createElement('div');
        decisionSection.className = 'tool-body-section tool-decision-section';
        decisionSection.innerHTML = '<div class="tool-label">Decision</div><pre></pre>';
        block.querySelector('.tool-body').appendChild(decisionSection);
      }
      decisionSection.querySelector('pre').textContent = decision;

      tagSearchableNode(block, `${toolName} ${decision}`);
      scrollBottom();
      break;
    }
    case 'system.message':
        appendSystemMessage(evt.payload?.text || '', evt.payload?.level || 'info');
        break;
      case 'session.interrupted':
        finalizeAssistant();
        appendSystemMessage('Run interrupted by user', 'warn');
        break;
      case 'session.failed':
        finalizeAssistant();
        appendSystemMessage(evt.payload?.error || 'Session failed', 'error');
        break;
      case 'mcp.status':
        appendSystemMessage(`MCP: ${evt.payload?.status || 'status update'}`);
        break;
      default:
        break;
    }
  }

  // ---- API ----
  async function api(path, options = {}) {
    const res = await fetch(`${state.bridgeUrl}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
    return res.json();
  }


  function estimateAttachmentTokens(files) {
    return (files || []).reduce((sum, item) => {
      const size = Number(item.size || 0);
      return sum + Math.ceil(size / 4);
    }, 0);
  }

  function updateTokenCounter() {
    const promptText = (el.promptInput?.value || '').trim();
    const chars = promptText.length;
    const words = promptText ? (promptText.match(/\S+/g) || []).length : 0;
    const promptTokens = promptText ? Math.ceil(chars / 4) : 0;
    const attachmentTokens = estimateAttachmentTokens(state.attachments);
    state.attachmentTokens = attachmentTokens;
    const total = promptTokens + attachmentTokens;

    if (el.promptStats) {
      el.promptStats.textContent = attachmentTokens > 0
        ? `~${total} tok · ${chars} ch · ${words} wd · +${attachmentTokens} file`
        : `~${promptTokens} tok · ${chars} ch · ${words} wd`;
    }

  }

  function renderAttachments() {
    if (!el.attachmentRow) return;
    el.attachmentRow.innerHTML = '';
    state.attachments.forEach((item) => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.innerHTML = `
        <span>${escapeHtml(item.filename)} (${Math.round((item.size || 0) / 1024)}KB)</span>
        <button type="button" data-remove-attachment="${escapeHtml(item.filename)}" style="margin-left:8px;border:none;background:none;cursor:pointer;color:inherit">×</button>
      `;
      const btn = chip.querySelector('button');
      btn?.addEventListener('click', async () => {
        if (!state.sessionId) return;
        await api(`/api/sessions/${state.sessionId}/context/${encodeURIComponent(item.filename)}`, { method: 'DELETE' });
        await loadAttachments();
      });
      el.attachmentRow.appendChild(chip);
    });
    updateTokenCounter();
  }

  async function loadAttachments() {
    if (!state.sessionId) {
      state.attachments = [];
      state.attachmentTokens = 0;
      renderAttachments();
      return;
    }
    try {
      const data = await api(`/api/sessions/${state.sessionId}/context`);
      state.attachments = data.files || [];
      state.attachmentTokens = estimateAttachmentTokens(state.attachments);
      renderAttachments();
    } catch (err) {
      console.warn('Attachment load error', err);
      state.attachments = [];
      state.attachmentTokens = 0;
      renderAttachments();
    }
  }

  function setAttachmentError(message = '') {
    if (!el.attachmentError) return;
    el.attachmentError.textContent = message;
    el.attachmentError.style.display = message ? 'block' : 'none';
  }

  async function uploadAttachment(file) {
    if (!file) return;
    setAttachmentError('');

    if (file.size > 204800) {
      setAttachmentError(`"${file.name}" exceeds the 200KB limit.`);
      return;
    }

    if (!state.sessionId) {
      await createSession();
    }

    const form = new FormData();
    form.append('file', file);

    const res = await fetch(`${state.bridgeUrl}/api/sessions/${state.sessionId}/context`, {
      method: 'POST',
      body: form,
    });

    if (!res.ok) {
      let detail = `Upload failed (${res.status})`;
      try {
        const data = await res.json();
        if (data?.detail) detail = data.detail;
      } catch (_) {}

      if (String(detail).includes('file exceeds 200KB limit')) {
        setAttachmentError(`"${file.name}" exceeds the 200KB limit.`);
        return;
      }

      throw new Error(detail);
    }

    setAttachmentError('');
    await loadAttachments();
  }

  async function createSession({ resumeSessionId = null, forkSession = false } = {}) {
    state.model = el.modelSelect?.value || state.model;
    state.toolSearchMode = el.toolSearchSelect?.value || null;

    const manualCwd = (el.cwdManualInput?.value || '').trim();
    const effectiveCwd = (
      state.cwdBrowsing ||
      manualCwd ||
      state.cwdSelected ||
      state.cwd ||
      ''
    ).trim();

    if (effectiveCwd) setCwd(effectiveCwd);

    syncStateToActiveTab();
    const body = {
      model: state.model,
      cwd: effectiveCwd || null,
      provider: state.provider,
      permission_mode: state.permissionMode,
      sdk_permission_mode: state.sdkPermissionMode || 'default',
      tool_search_mode: state.toolSearchMode,
      system_prompt: null,
      resume_session_id: resumeSessionId,
      fork_session: forkSession,
    };
    console.log('Creating session with cwd:', body.cwd);
    const data = await api('/api/sessions', { method: 'POST', body: JSON.stringify(body) });
    state.sessionId = data.session_id;
   state.connections = 0;
   state.idleSeconds = 0;
  if (data.model) state.model = data.model;
  if (data.provider) state.provider = data.provider;
 if (data.provider_base_url) state.providerBaseUrl = data.provider_base_url;
 else state.providerBaseUrl = null;
if (Object.prototype.hasOwnProperty.call(data, 'tool_search_mode')) state.toolSearchMode = data.tool_search_mode;
if (Object.prototype.hasOwnProperty.call(data, 'tool_search_active')) state.toolSearchActive = Boolean(data.tool_search_active);
if (data.permission_mode) state.permissionMode = data.permission_mode;
if (data.sdk_permission_mode) state.sdkPermissionMode = data.sdk_permission_mode;
else if (data.permission_mode === 'manual') state.sdkPermissionMode = 'default';
else if (data.permission_mode === 'auto') state.sdkPermissionMode = 'acceptEdits';
normalizePermissionState();
state.effectiveSessionConfig = {
  sessionId: data.session_id || state.sessionId || null,
  model: data.model || state.model || null,
  provider: data.provider || state.provider || null,
  providerBaseUrl: Object.prototype.hasOwnProperty.call(data, 'provider_base_url') ? data.provider_base_url : null,
  permissionMode: data.permission_mode || state.permissionMode || null,
  sdkPermissionMode: data.sdk_permission_mode || state.sdkPermissionMode || 'default',
  toolSearchMode: Object.prototype.hasOwnProperty.call(data, 'tool_search_mode') ? data.tool_search_mode : null,
  toolSearchActive: Object.prototype.hasOwnProperty.call(data, 'tool_search_active') ? Boolean(data.tool_search_active) : null,
  cwd: body.cwd || state.cwd || state.cwdSelected || null,
  runtimeMode: typeof data.mock_mode === 'boolean'
    ? (data.mock_mode ? 'mock' : 'live')
    : (state.runtimeMode || null),
};
  if (Object.prototype.hasOwnProperty.call(data, 'cwd')) setCwd(data.cwd);
  if (typeof data.mock_mode === 'boolean') setRuntimeMode(data.mock_mode);
  renderModelOptions();
  renderProviderSwitcher();
  renderPermissionMode();
    const tab = currentTab();
    if (tab && !tab.sessionId) tab.title = (resumeSessionId ? 'Resumed' : 'Live') + ' ' + state.sessionId.slice(0, 8);
    setSessionLabel(state.sessionId);
    syncStateToActiveTab();
    renderTabs();
    connectSocket();
    await loadAttachments();
    syncStateToActiveTab();
    return data;
  }

  function connectSocket() {
    if (!state.sessionId) return;
    if (state.socket) { try { state.socket.close(); } catch (_) {} }
    setConnection('connecting');
    const url = `${state.wsBase}/${state.sessionId}?protocol_version=${state.protocolVersion}`;
    const ws = new WebSocket(url);
    state.socket = ws;
    ws.addEventListener('open', () => setConnection('connected'));
    ws.addEventListener('close', () => setConnection('disconnected'));
    ws.addEventListener('error', () => setConnection('error'));
    ws.addEventListener('message', (msg) => {
      try {
        const evt = JSON.parse(msg.data);
        renderEvent(evt);
      } catch (e) { console.error('WS parse error', e); }
    });
  }

  function sendPrompt() {
    const prompt = el.promptInput.value.trim();
    if (!prompt) return;
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
      appendSystemMessage('Not connected. Create a session first.', 'warn');
      return;
    }
    setReplayMode(false);
    // Show user message in transcript
    hideWelcome();
    const userMsg = document.createElement('div');
    userMsg.className = 'msg user';
    userMsg.textContent = prompt;
    tagSearchableNode(userMsg, prompt);
    el.transcript.appendChild(userMsg);
    scrollBottom();

    state.socket.send(JSON.stringify({ prompt }));
    syncStateToActiveTab();
    el.promptInput.value = '';
    el.promptInput.style.height = '';
  }

  async function interrupt() {
    if (!state.sessionId) return;
    try { await api(`/api/sessions/${state.sessionId}/interrupt`, { method: 'POST' }); }
    catch (e) { console.warn('Interrupt error', e); }
  }

  async function replaySession(id, source = 'live') {
    let events;
    const endpoint = source === 'archive'
      ? `/api/archive/sessions/${id}/replay`
      : `/api/sessions/${id}/replay`;
    try { events = await api(endpoint); }
    catch (e) { appendSystemMessage('Could not load replay data.', 'error'); return; }
    clearTranscript();
    setReplayMode(true);
    for (const evt of events) renderEvent(evt);
    finalizeAssistant();
    jumpToPendingSearchHit();
  }

  // ---- Archive ----
  function groupByLineage(items) {
    const map = new Map();
    items.forEach(item => {
      const root = item.root_session_id || item.id;
      if (!map.has(root)) map.set(root, []);
      map.get(root).push(item);
    });
    return [...map.entries()];
  }

  function sortArchive(items) {
    const mode = el.archiveSort.value;
    const arr = [...items];
    if (mode === 'title') arr.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    if (mode === 'tag') arr.sort((a, b) => (a.tag || '').localeCompare(b.tag || ''));
    if (mode === 'root') arr.sort((a, b) => (a.root_session_id || a.id).localeCompare(b.root_session_id || b.id));
    if (mode === 'recent') arr.sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')));
    return arr;
  }

  async function renameSession(id, currentTitle) {
    // Inline rename — find the card and add input
    const card = document.querySelector(`[data-session-id="${id}"]`);
    if (!card) return;
    const existing = card.querySelector('.inline-input');
    if (existing) { existing.focus(); return; }
    const input = document.createElement('input');
    input.className = 'inline-input';
    input.value = currentTitle || '';
    input.placeholder = 'Session title…';
    card.appendChild(input);
    input.focus();
    input.select();
    const commit = async () => {
      const title = input.value.trim();
      if (title) {
        try { await api(`/api/archive/sessions/${id}/rename`, { method: 'POST', body: JSON.stringify({ title }) }); }
        catch (e) { console.warn('Rename error', e); }
      }
      input.remove();
      await loadArchive();
    };
    input.addEventListener('blur', commit);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') input.remove(); });
  }

  async function tagSession(id, currentTag) {
    const card = document.querySelector(`[data-session-id="${id}"]`);
    if (!card) return;
    const existing = card.querySelector('.inline-input.tag-input-el');
    if (existing) { existing.focus(); return; }
    const input = document.createElement('input');
    input.className = 'inline-input tag-input-el';
    input.value = currentTag || '';
    input.placeholder = 'Tag (blank to clear)…';
    card.appendChild(input);
    input.focus();
    input.select();
    const commit = async () => {
      try { await api(`/api/archive/sessions/${id}/tag`, { method: 'POST', body: JSON.stringify({ tag: input.value.trim() || null }) }); }
      catch (e) { console.warn('Tag error', e); }
      input.remove();
      await loadArchive();
    };
    input.addEventListener('blur', commit);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') input.remove(); });
  }

  function renderArchive() {
    const query = el.archiveSearch.value.trim().toLowerCase();
    const filtered = sortArchive(state.archive).filter(item => {
      const hay = [item.title, item.summary, item.id, item.root_session_id, item.cwd, item.tag]
        .filter(Boolean).join(' ').toLowerCase();
      return !query || hay.includes(query);
    });

    el.archiveList.innerHTML = '';

    if (!filtered.length) {
      el.archiveList.innerHTML = `
        <div class="empty-archive">
          <i data-lucide="folder-search" style="width:36px;height:36px"></i>
          <p>${query ? 'No sessions match your search, tag, cwd, or lineage query.' : 'No archived sessions yet. Completed or resumable Claude sessions will appear here.'}</p>
        </div>`;
      safeCreateIcons([el.archiveList]);
      return;
    }

    const groups = Array.isArray(groupByLineage(filtered)) ? groupByLineage(filtered) : [];

    groups.forEach((groupEntry) => {
      const root = groupEntry?.root || 'unknown';
      const items = Array.isArray(groupEntry?.items) ? groupEntry.items : [];
      const isOpen = state.lineageOpen.has(root) ? state.lineageOpen.get(root) : items.length <= 3;
      state.lineageOpen.set(root, isOpen);

      const group = document.createElement('div');
      group.className = 'lineage-group' + (isOpen ? ' lineage-open' : '');

      if (!items.length) {
        return;
      }

      if (items.length > 1) {
        const header = document.createElement('button');
        header.type = 'button';
        header.className = 'lineage-header';
        header.innerHTML = `
          <span style="display:flex;align-items:center;gap:8px;">
            <i data-lucide="chevron-right" class="lineage-chevron" style="width:14px;height:14px"></i>
            <strong>${escapeHtml(items[0].title || 'Untitled root')}</strong>
          </span>
          <span class="badge">${items.length} sessions</span>
        `;
        header.addEventListener('click', () => {
          const next = !state.lineageOpen.get(root);
          state.lineageOpen.set(root, next);
          group.classList.toggle('lineage-open', next);
          body.hidden = !next;
        });
        group.appendChild(header);
      }

      const body = document.createElement('div');
      body.hidden = !isOpen;

      items.forEach((item) => {
        const card = document.createElement('div');
        card.className = 'session-card';
        card.dataset.sessionId = item.id;

        const title = item.title || 'Untitled session';
        const summary = item.summary || 'No summary available.';
        const rootId = item.root_session_id || item.id;
        const isRoot = rootId === item.id;
        const lineageLabel = window.ClaudeArchiveUtils.archiveLineageLabel(item);
        const cwdLabel = item.cwd || '~';
        const modelLabel = item.model || 'Unknown model';
        const tagChip = item.tag ? `<span class="chip accent">${escapeHtml(item.tag)}</span>` : '';
        const updatedLabel = item.updated_at || item.created_at || 'Unknown activity time';
        const messageCount = Number.isFinite(item.message_count) ? `${item.message_count} msgs` : null;

        card.innerHTML = `
          <div class="session-card-header">
            <div class="session-title-wrap">
              <div class="session-title">${escapeHtml(title)}</div>
              <div class="session-subtitle">${escapeHtml(lineageLabel)}</div>
            </div>
            <div class="session-card-chips">
              ${tagChip}
              <span class="chip">${window.ClaudeArchiveUtils.archiveRoleLabel(item)}</span>
            </div>
          </div>

          <div class="session-summary">${escapeHtml(summary)}</div>

          <div class="session-meta">
            <span class="meta-pill" title="Last activity">${escapeHtml(updatedLabel)}</span>
            <span class="meta-pill" title="Working directory">${escapeHtml(cwdLabel)}</span>
            <span class="meta-pill" title="Model">${escapeHtml(modelLabel)}</span>
            ${messageCount ? `<span class="meta-pill" title="Message count">${escapeHtml(messageCount)}</span>` : ''}
          </div>

          <div class="card-actions">
            <button class="card-btn" data-action="continue" title="Resume this archived session in its existing lineage">
              <i data-lucide="play" style="width:11px;height:11px"></i>Continue
            </button>
            <button class="card-btn" data-action="fork" title="Start a new branch from this archived session">
              <i data-lucide="git-branch" style="width:11px;height:11px"></i>Fork
            </button>
            <button class="card-btn" data-action="replay" title="Replay stored events through the transcript renderer">
              <i data-lucide="rewind" style="width:11px;height:11px"></i>Replay
            </button>
            <button class="card-btn" data-action="rename" title="Rename this archived session">
              <i data-lucide="pencil" style="width:11px;height:11px"></i>Rename
            </button>
            <button class="card-btn" data-action="tag" title="Add or change session tag">
              <i data-lucide="tag" style="width:11px;height:11px"></i>Tag
            </button>
          </div>
        `;

        card.querySelector('[data-action="continue"]').addEventListener('click', async () => {
          try { await createSession({ resumeSessionId: item.id, forkSession: false }); }
          catch (e) { appendSystemMessage('Failed to continue session lineage.', 'error'); }
        });

        card.querySelector('[data-action="fork"]').addEventListener('click', async () => {
          try { await createSession({ resumeSessionId: item.id, forkSession: true }); }
          catch (e) { appendSystemMessage('Failed to fork session.', 'error'); }
        });

        card.querySelector('[data-action="replay"]').addEventListener('click', async () => {
          await replaySession(item.id, 'archive');
        });

        card.querySelector('[data-action="rename"]').addEventListener('click', async () => {
          await renameSession(item.id, item.title || '');
        });

        card.querySelector('[data-action="tag"]').addEventListener('click', async () => {
          await tagSession(item.id, item.tag || '');
        });

        body.appendChild(card);
      });

      group.appendChild(body);
      el.archiveList.appendChild(group);
    });

    safeCreateIcons([el.archiveList]);
  }

  async function loadArchive() {
    try {
      state.archive = await api('/api/archive/sessions');
    } catch (err) {
      console.warn('Archive load error', err);
      state.archive = [];
    }
    renderArchive();
  }

  function updatePromptStats() {
    updateTokenCounter();
  }

  // ---- Auto-resize textarea ----
  function bindTextareaResize() {
    el.promptInput.addEventListener('input', () => {
      el.promptInput.style.height = 'auto';
      el.promptInput.style.height = Math.min(el.promptInput.scrollHeight, 240) + 'px';
      updatePromptStats();
    });
  }

  // ---- Events ----
  function bindEvents() {
    el.sendBtn.addEventListener('click', sendPrompt);
    el.attachFileBtn?.addEventListener('click', () => el.attachFileInput?.click());
    el.attachFileInput?.addEventListener('change', async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        await uploadAttachment(file);
      } catch (err) {
        appendSystemMessage(err.message || 'Attachment upload failed.', 'error');
      } finally {
        e.target.value = '';
      }
    });
    el.toolSearchSelect?.addEventListener('change', () => {
      state.toolSearchMode = el.toolSearchSelect?.value || null;
      renderProviderRuntimeMeta();
      syncStateToActiveTab();
    });
    el.composer?.addEventListener('dragover', (e) => {
      e.preventDefault();
      el.composer.classList.add('dragover');
    });
    el.composer?.addEventListener('dragleave', () => {
      el.composer.classList.remove('dragover');
    });
    el.composer?.addEventListener('drop', async (e) => {
      e.preventDefault();
      el.composer.classList.remove('dragover');
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      try {
        await uploadAttachment(file);
      } catch (err) {
        appendSystemMessage(err.message || 'Attachment upload failed.', 'error');
      }
    });
    updatePromptStats();

  el.promptInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendPrompt();
      }
    });
    el.interruptBtn.addEventListener('click', interrupt);
    el.replayCurrentBtn.addEventListener('click', async () => {
      if (state.sessionId) await replaySession(state.sessionId);
    });
    el.newSessionBtn.addEventListener('click', async () => {
      clearTranscript();
      setReplayMode(false);
      try { await createSession(); }
      catch (e) { appendSystemMessage('Could not connect to bridge at ' + state.bridgeUrl + '.', 'error'); }
    });
    el.exitReplay.addEventListener('click', () => {
  stopSessionElapsedTimer();
      setReplayMode(false);
      clearTranscript();
      if (el.welcome) el.welcome.classList.remove('hidden');
    });
    el.archiveSearch.addEventListener('input', renderArchive);
    el.archiveSort.addEventListener('change', renderArchive);
    el.refreshArchive.addEventListener('click', loadArchive);
    el.openSearchBtn?.addEventListener('click', openSearchModal);
    el.exportSessionBtn?.addEventListener('click', () => exportCurrentSession('md'));
    el.exportSessionJsonBtn?.addEventListener('click', () => exportCurrentSession('json'));
    el.searchBackdrop?.addEventListener('click', closeSearchModal);
    el.searchClose?.addEventListener('click', closeSearchModal);
    el.searchInputModal?.addEventListener('input', runSessionSearch);
    el.providerSettingsBtn?.addEventListener('click', () => {
    const raw = (el.providerBaseUrlInput?.value || '').trim();
    state.providerBaseUrl = state.provider === 'cloud' ? null : (raw || null);
    renderProviderRuntimeMeta();
    appendSystemMessage(
      state.provider === 'cloud'
        ? 'Cloud provider uses its default route.'
        : `Provider endpoint set to ${state.providerBaseUrl || 'default'} for new sessions.`
    );
  });

  el.modelSelect?.addEventListener('change', () => {
      state.model = el.modelSelect.value;
    });
    el.modeManualBtn?.addEventListener('click', () => setPermissionMode('manual'));
    el.modeAutoBtn?.addEventListener('click', () => setPermissionMode('auto'));
    el.tabScrollLeft?.addEventListener('click', () => {
      el.tabbar?.scrollBy({ left: -240, behavior: 'smooth' });
      window.setTimeout(updateTabScrollButtons, 180);
    });
    el.tabScrollRight?.addEventListener('click', () => {
      el.tabbar?.scrollBy({ left: 240, behavior: 'smooth' });
      window.setTimeout(updateTabScrollButtons, 180);
    });
    el.tabbar?.addEventListener('scroll', updateTabScrollButtons);
  el.newTabBtn?.addEventListener('click', openNewTab);
    el.terminalToggle?.addEventListener('click', () => {
      setTerminalOpen(!state.terminalOpen);
      syncStateToActiveTab();
    });
    el.terminalErrorsOnly?.addEventListener('change', () => {
      state.terminalErrorsOnly = !!el.terminalErrorsOnly.checked;
      renderRawLog();
      syncStateToActiveTab();
    });
    el.terminalClear?.addEventListener('click', () => {
      state.rawLogLines = [];
      renderRawLog();
      syncStateToActiveTab();
    });
    el.terminalCopy?.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(el.terminalPre?.textContent || '');
        appendSystemMessage('Raw terminal copied to clipboard.');
      } catch (_) {
        appendSystemMessage('Could not copy raw terminal.', 'error');
      }
    });

    let resizingTerminal = false;
    let resizeMove = null;
    let resizeUp = null;

    el.terminalResizeHandle?.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      resizingTerminal = true;

      resizeMove = (evt) => {
        if (!resizingTerminal) return;
        const maxHeight = Math.floor(window.innerHeight * 0.6);
        const nextHeight = Math.max(100, Math.min(maxHeight, window.innerHeight - evt.clientY));
        state.terminalHeight = nextHeight;
        applyTerminalHeight();
        syncStateToActiveTab();
      };

      resizeUp = () => {
        resizingTerminal = false;
        window.removeEventListener('pointermove', resizeMove);
        window.removeEventListener('pointerup', resizeUp);
      };

      window.addEventListener('pointermove', resizeMove);
      window.addEventListener('pointerup', resizeUp);
    });

    document.addEventListener('keydown', (e) => {
      if (!(e.metaKey || e.ctrlKey)) return;

      if (e.key === '`') {
        e.preventDefault();
        setTerminalOpen(!state.terminalOpen);
        syncStateToActiveTab();
        return;
      }

      if (e.key.toLowerCase() === 't') {
        e.preventDefault();
        openNewTab();
    renderTabs();
  bindStableUiHandlers();
        return;
      }

      if (e.key.toLowerCase() === 'f') {
        e.preventDefault();
        openSearchModal();
        return;
      }

      if (e.shiftKey && e.key.toLowerCase() === 'e') {
        e.preventDefault();
        exportCurrentSession('md');
        return;
      }

      if (e.key.toLowerCase() === 'w') {
        e.preventDefault();
        closeTab(state.activeTabId);
        return;
      }

      if (/^[1-9]$/.test(e.key)) {
        const idx = Number(e.key) - 1;
        const tab = state.tabs[idx];
        if (tab) {
          e.preventDefault();
          switchTab(tab.id);
        }
      }
    });

    document.addEventListener('keyup', (e) => {
      if (e.key !== 'Escape') return;

      if (el.searchModal && !el.searchModal.classList.contains('hidden')) {
        closeSearchModal();
        return;
      }

      if (el.cwdModal && !el.cwdModal.classList.contains('hidden')) {
        closeCwdModal();
        return;
      }
    });

    // Prompt chips
    document.querySelectorAll('.prompt-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        el.promptInput.value = btn.textContent.trim();
        el.promptInput.focus();
        el.promptInput.dispatchEvent(new Event('input'));
      });
    });
  }

  async function init() {
  try {
    openNewTab();
    await initCwd();
    renderPermissionMode();
    el.cwdPill?.addEventListener('click', openCwdModal);
    el.cwdBackdrop?.addEventListener('click', closeCwdModal);
    el.cwdClose?.addEventListener('click', closeCwdModal);
    el.cwdCancel?.addEventListener('click', closeCwdModal);
    el.cwdConfirm?.addEventListener('click', () => {
      const manualValue = el.cwdManualInput?.value.trim() || '';
      setCwd(manualValue || state.cwdBrowsing || state.cwdSelected || state.cwd);
      closeCwdModal();
    });
    el.cwdManualInput?.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const value = el.cwdManualInput.value.trim();
        if (!value) return;
        await browseCwd(value);
      }
    });

    await loadProviders();
    bindRuntimeMetaToggle();
    setRuntimeMetaExpanded(false);
    bindEvents();
    bindTextareaResize();
    applyTerminalHeight();
    setTerminalOpen(state.terminalOpen);
    if (el.terminalErrorsOnly) el.terminalErrorsOnly.checked = state.terminalErrorsOnly;
    renderRawLog();
    updateTabScrollButtons();
    await loadArchive();
  } catch (error) {
    console.error('Startup initialization failed:', error);
    appendSystemMessage(`Could not reach backend at [${state.bridgeUrl}](${state.bridgeUrl}). Check that the Claude bridge server is running and reload the page.`);
  }
}

return { init };
})();

document.addEventListener('DOMContentLoaded', Bridge.init);



function setCapabilityPill(id, active, label) {
  const el = document.getElementById(id);
  if (!el) return;
  if (label) el.textContent = label;
  el.classList.toggle("is-active", !!active);
}

function syncCapabilityPills(state) {
  const hasSession = !!state?.sessionId;
  const hasReplay = !!state?.isReplayMode;
  const hasRouting = !!state?.provider || !!state?.providerBaseUrl;
  const hasTools = !!state?.toolSearchActive || !!state?.activeToolUseId;
  setCapabilityPill("cap-session-pill", hasSession, "Session continuity");
  setCapabilityPill("cap-lineage-pill", true, "Resume / fork lineage");
  setCapabilityPill("cap-replay-pill", hasReplay, hasReplay ? "Replay mode active" : "Replayable events");
  setCapabilityPill("cap-hooks-pill", true, "Hook-ready runtime");
  setCapabilityPill("cap-routing-pill", hasRouting, hasRouting ? `Route: ${state.provider || "configured"}` : "Local model routing");
  setCapabilityPill("cap-tools-pill", hasTools, hasTools ? "Tool streaming active" : "Tool streaming");
}




function setProviderHealthPill(id, label, online) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = label;
  el.classList.toggle("is-online", online === true);
  el.classList.toggle("is-offline", online === false);
}

function syncProviderHealthPills(state) {
  const health = state?.providerHealth || {};
  setProviderHealthPill("provider-health-cloud", `Cloud: ${health.cloud === true ? "online" : health.cloud === false ? "offline" : "unknown"}`, health.cloud);
  setProviderHealthPill("provider-health-ollama", `Ollama: ${health.ollama === true ? "online" : health.ollama === false ? "offline" : "unknown"}`, health.ollama);
  setProviderHealthPill("provider-health-vllm", `vLLM: ${health.vllm === true ? "online" : health.vllm === false ? "offline" : "unknown"}`, health.vllm);
}



function renderHookEvent(payload) {
  const transcript = document.getElementById("messages");
  if (!transcript) return;
  const node = document.createElement("div");
  node.className = "system-banner";
  node.textContent = payload?.message || "Hook event observed.";
  transcript.appendChild(node);
}
