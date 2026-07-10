const Bridge = (() => {
  const state = {
    bridgeUrl: 'http://127.0.0.1:8020',
    wsBase: 'ws://127.0.0.1:8020/ws',
    protocolVersion: '0.2.0',
    sessionId: null,
    socket: null,
    model: 'claude-sonnet-4-5',
    provider: 'cloud',
    providers: {},
    providerHealth: {},
    permissionMode: 'manual',
    cwd: '~',
    cwdSelected: null,
    cwdBrowsing: null,
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
  };

  const el = {
    transcript: document.getElementById('transcript'),
    welcome: document.getElementById('welcome'),
    attachmentRow: document.getElementById('attachment-row'),
    attachmentError: document.getElementById('attachment-error'),
    composer: document.getElementById('composer'),
    attachFileBtn: document.getElementById('attach-file-btn'),
    attachFileInput: document.getElementById('attach-file-input'),
    promptInput: document.getElementById('prompt-input'),
    sendBtn: document.getElementById('send-btn'),
    interruptBtn: document.getElementById('interrupt-btn'),
    replayCurrentBtn: document.getElementById('replay-current-btn'),
    newSessionBtn: document.getElementById('new-session'),
    statusDot: document.getElementById('status-dot'),
    connectionLabel: document.getElementById('connection-label'),
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
    };
  }

  function currentTab() {
    return state.tabs.find(t => t.id === state.activeTabId) || null;
  }

  function syncStateToActiveTab() {
    const tab = currentTab();
    if (!tab) return;
    tab.sessionId = state.sessionId;
    tab.transcriptHtml = el.transcript?.innerHTML || '';
    tab.attachments = [...state.attachments];
    tab.attachmentTokens = state.attachmentTokens;
    tab.permissionMode = state.permissionMode;
    tab.replayMode = state.replayMode;
    tab.rawLogLines = [...state.rawLogLines];
    tab.terminalErrorsOnly = state.terminalErrorsOnly;
    tab.terminalOpen = state.terminalOpen;
    tab.terminalHeight = state.terminalHeight;
    tab.cwdSelected = state.cwdSelected;
    tab.model = state.model;
    tab.provider = state.provider;
  }

  function syncActiveTabToState() {
    const tab = currentTab();
    if (!tab) return;
    state.sessionId = tab.sessionId;
    state.attachments = [...(tab.attachments || [])];
    state.attachmentTokens = tab.attachmentTokens || 0;
    state.permissionMode = tab.permissionMode || 'manual';
    state.replayMode = !!tab.replayMode;
    state.rawLogLines = [...(tab.rawLogLines || [])];
    state.terminalErrorsOnly = !!tab.terminalErrorsOnly;
    state.terminalOpen = !!tab.terminalOpen;
    state.terminalHeight = tab.terminalHeight || 220;
    state.cwdSelected = tab.cwdSelected || state.cwdSelected;
    state.model = tab.model || state.model;
    state.provider = tab.provider || state.provider;

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
      btn.type = 'button';
      btn.className = 'session-tab' + (tab.id === state.activeTabId ? ' active' : '');
      btn.setAttribute('data-tab-id', tab.id);
      btn.innerHTML = `
        <span class="status-dot ${tab.sessionId ? 'connected' : 'disconnected'}"></span>
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
    state.attachments = [];
    state.rawLogLines = [];
    state.replayMode = false;
    clearTranscript();
    renderAttachments();
    renderRawLog();
    setSessionLabel(null);
    setConnection('disconnected');
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


  function renderPermissionMode() {
    if (el.modeManualBtn) el.modeManualBtn.classList.toggle('active', state.permissionMode === 'manual');
    if (el.modeAutoBtn) el.modeAutoBtn.classList.toggle('active', state.permissionMode === 'auto');
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
          body: JSON.stringify({ permission_mode: mode }),
        });
      } catch (err) {
        appendSystemMessage('Failed to update approval mode.', 'error');
      }
    }
  }
  function renderProviderSwitcher() {
    if (!el.providerSwitcher) return;
    el.providerSwitcher.innerHTML = '';
    ['cloud', 'ollama', 'vllm'].forEach((name) => {
      const info = state.providers[name] || { label: name };
      const health = state.providerHealth[name] || {};
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'badge' + (state.provider === name ? ' accent' : '');
      btn.title = health.ok === false ? `${info.label || name} offline` : `${info.label || name} online`;
      btn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px">
        <span style="width:8px;height:8px;border-radius:999px;background:${health.ok === false ? '#6b7280' : '#22c55e'}"></span>
        <span>${info.label || name}</span>
      </span>`;
      btn.disabled = (name !== 'cloud' && health.ok === false);
      btn.addEventListener('click', () => {
        state.provider = name;
        renderProviderSwitcher();
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
      state.provider = data.default_provider || state.provider || 'cloud';
      renderModelOptions();
    } catch (err) {
      console.warn('Provider load error', err);
      state.providers = {
        cloud: { label: 'Cloud', models: ['claude-sonnet-4-5', 'claude-opus-4-5', 'claude-haiku-4-5'] },
      };
      state.provider = 'cloud';
      renderModelOptions();
    }
    await loadProviderHealth();
    renderProviderSwitcher();
  }

  async function browseCwd(path = null) {
    const query = path ? `?path=${encodeURIComponent(path)}` : '';
    const data = await api(`/api/fs/browse${query}`);
    state.cwdBrowsing = data.path;
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
    lucide.createIcons({ nodes: el.cwdBrowser.querySelectorAll('[data-lucide]') });
  }

  async function loadGitRoots() {
    const data = await api('/api/fs/git-roots');
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

  function openCwdModal() {
    el.cwdModal.classList.remove('hidden');
    el.cwdModal.setAttribute('aria-hidden', 'false');
    if (el.cwdManualInput) el.cwdManualInput.value = state.cwdSelected || state.cwd || '';
    loadGitRoots().catch(console.error);
    browseCwd(state.cwdSelected || null).catch(console.error);
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

  function closeSearchModal() {
    el.searchModal?.classList.add('hidden');
    el.searchModal?.setAttribute('aria-hidden', 'true');
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
        await replaySession(id);
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
    const parts = text.split(/(```[\s\S]*?```)/g);
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
    lucide.createIcons({ nodes: [block] });
    state.toolEls.set(toolId, block);
    scrollBottom();
    return block;
  }


  function sendToolDecision(decision, toolId) {
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return;
    state.socket.send(JSON.stringify({ type: decision, tool_id: toolId }));
  }


  function escapeHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }


  function normalizeSearchText(value) {
    return String(value || '').toLowerCase().replace(/\s+/g, ' ').trim();
  }

  function tagSearchableNode(node, text) {
    if (!node) return;
    node.dataset.searchText = normalizeSearchText(text);
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
        appendSystemMessage(`Live session ready (${evt.payload?.model || state.model})`);
        break;
      case 'session.updated':
        appendSystemMessage('Session updated');
        break;
      case 'assistant.delta':
        appendAssistantDelta(evt.payload?.text || '');
        break;
      case 'assistant.completed':
        finalizeAssistant();
        break;
      case 'tool.started': {
        const block = getOrCreateTool(evt.payload?.tool_id, evt.payload?.tool_name || 'tool');
        const inputSection = block.querySelector(`#tool-input-${evt.payload?.tool_id} pre`);
        if (inputSection) {
          inputSection.textContent = JSON.stringify(evt.payload?.tool_input, null, 2);
        }
        break;
      }
      case 'tool.delta': {
        const block = getOrCreateTool(evt.payload?.tool_id, 'tool');
        let outputSection = block.querySelector('.tool-output-section');
        if (!outputSection) {
          outputSection = document.createElement('div');
          outputSection.className = 'tool-body-section tool-output-section';
          outputSection.innerHTML = '<div class="tool-label">Output</div><pre></pre>';
          block.querySelector('.tool-body').appendChild(outputSection);
        }
        outputSection.querySelector('pre').textContent += evt.payload?.partial || '';
        break;
      }
      case 'tool.completed': {
        const block = getOrCreateTool(evt.payload?.tool_id, evt.payload?.tool_name || 'tool');
        block.classList.remove('running');
        block.classList.add(evt.payload?.is_error ? 'error' : 'done');
        block.querySelector('.tool-status-badge').textContent = evt.payload?.is_error ? 'error' : 'done';
        // Add/update output
        let outputSection = block.querySelector('.tool-output-section');
        if (!outputSection && evt.payload?.output != null) {
          outputSection = document.createElement('div');
          outputSection.className = 'tool-body-section tool-output-section';
          outputSection.innerHTML = '<div class="tool-label">Output</div><pre></pre>';
          block.querySelector('.tool-body').appendChild(outputSection);
        }
        if (outputSection && evt.payload?.output != null) {
          const out = typeof evt.payload.output === 'string' ? evt.payload.output : JSON.stringify(evt.payload.output, null, 2);
          outputSection.querySelector('pre').textContent = out;
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
    if (!el.tokenCounter) return;
    const promptText = (el.promptInput?.value || '').trim();
    const promptTokens = promptText ? Math.ceil(promptText.length / 4) : 0;
    const attachmentTokens = estimateAttachmentTokens(state.attachments);
    state.attachmentTokens = attachmentTokens;
    const total = promptTokens + attachmentTokens;
    el.tokenCounter.textContent = attachmentTokens > 0
      ? `~${total} tokens (${promptTokens} prompt + ${attachmentTokens} files)`
      : `~${promptTokens} tokens`;
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
    syncStateToActiveTab();
    const body = {
      model: state.model,
      cwd: state.cwdSelected,
      provider: state.provider,
      permission_mode: state.permissionMode,
      system_prompt: null,
      resume_session_id: resumeSessionId,
      fork_session: forkSession,
    };
    const data = await api('/api/sessions', { method: 'POST', body: JSON.stringify(body) });
    state.sessionId = data.session_id;
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

  async function replaySession(id) {
    let events;
    try { events = await api(`/api/sessions/${id}/replay`); }
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

    const groups = groupByLineage(filtered);
    el.archiveList.innerHTML = '';

    if (!groups.length) {
      el.archiveList.innerHTML = `
        <div class="empty-archive">
          <i data-lucide="folder-open" style="width:32px;height:32px"></i>
          <p>${query ? 'No sessions match your search.' : 'No archived sessions yet.'}</p>
        </div>`;
      lucide.createIcons({ nodes: [el.archiveList] });
      return;
    }

    for (const [root, items] of groups) {
      const isOpen = state.lineageOpen.has(root) ? state.lineageOpen.get(root) : items.length <= 3;
      state.lineageOpen.set(root, isOpen);

      const group = document.createElement('div');
      group.className = 'lineage-group' + (isOpen ? ' lineage-open' : '');

      if (items.length > 1 || root !== items[0]?.id) {
        const header = document.createElement('div');
        header.className = 'lineage-header';
        header.innerHTML = `
          <i data-lucide="chevron-right" class="lineage-chevron" style="width:14px;height:14px"></i>
          <span>Lineage <code>${root.slice(0, 8)}</code></span>
          <span style="margin-left:auto;opacity:0.6">${items.length} session${items.length !== 1 ? 's' : ''}</span>
        `;
        header.addEventListener('click', () => {
          const next = !state.lineageOpen.get(root);
          state.lineageOpen.set(root, next);
          group.classList.toggle('lineage-open', next);
          body.classList.toggle('hidden', !next);
        });
        group.appendChild(header);
      }

      const body = document.createElement('div');
      body.className = 'group-body' + (!isOpen ? ' hidden' : '');

      items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'session-card' + (item.id === state.sessionId ? ' active' : '');
        card.setAttribute('data-session-id', item.id);

        const chips = [
          item.tag ? `<span class="chip accent">${escapeHtml(item.tag)}</span>` : '',
          item.model ? `<span class="chip">${escapeHtml(item.model)}</span>` : '',
          item.message_count != null ? `<span class="chip">${item.message_count} msgs</span>` : '',
        ].filter(Boolean).join('');

        const ts = item.updated_at
          ? new Date(item.updated_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
          : '';

        card.innerHTML = `
          <div class="session-title" title="${escapeHtml(item.id)}">${escapeHtml(item.title || 'Untitled session')}</div>
          <div class="session-meta">${escapeHtml(item.summary || '')}${ts ? ` · ${ts}` : ''}</div>
          <div class="chips">${chips}</div>
          <div class="card-actions">
            <button class="card-btn primary" data-action="continue"><i data-lucide="play" style="width:11px;height:11px"></i>Continue</button>
            <button class="card-btn" data-action="fork"><i data-lucide="git-branch" style="width:11px;height:11px"></i>Fork</button>
            <button class="card-btn" data-action="replay"><i data-lucide="rewind" style="width:11px;height:11px"></i>Replay</button>
            <button class="card-btn" data-action="rename"><i data-lucide="pencil" style="width:11px;height:11px"></i>Rename</button>
            <button class="card-btn" data-action="tag"><i data-lucide="tag" style="width:11px;height:11px"></i>Tag</button>
          </div>
        `;

        card.querySelector('[data-action="continue"]').addEventListener('click', async () => {
          clearTranscript();
          try { await createSession({ resumeSessionId: item.id, forkSession: false }); }
          catch (e) { appendSystemMessage('Failed to resume session.', 'error'); }
        });
        card.querySelector('[data-action="fork"]').addEventListener('click', async () => {
          clearTranscript();
          try { await createSession({ resumeSessionId: item.id, forkSession: true }); }
          catch (e) { appendSystemMessage('Failed to fork session.', 'error'); }
        });
        card.querySelector('[data-action="replay"]').addEventListener('click', async () => {
          await replaySession(item.id);
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
    }

    lucide.createIcons({ nodes: [el.archiveList] });
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

  // ---- Auto-resize textarea ----
  function bindTextareaResize() {
    el.promptInput.addEventListener('input', () => {
      el.promptInput.style.height = 'auto';
      el.promptInput.style.height = Math.min(el.promptInput.scrollHeight, 240) + 'px';
      updateTokenCounter();
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
        return;
      }

      if (e.key.toLowerCase() === 'f') {
        e.preventDefault();
        openSearchModal();
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
    setCwd('~');
    renderPermissionMode();
    el.cwdPill?.addEventListener('click', openCwdModal);
    el.cwdBackdrop?.addEventListener('click', closeCwdModal);
    el.cwdClose?.addEventListener('click', closeCwdModal);
    el.cwdCancel?.addEventListener('click', closeCwdModal);
    el.cwdConfirm?.addEventListener('click', () => {
      setCwd(state.cwdBrowsing || state.cwdSelected || state.cwd);
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
    bindEvents();
    bindTextareaResize();
    applyTerminalHeight();
    setTerminalOpen(state.terminalOpen);
    if (el.terminalErrorsOnly) el.terminalErrorsOnly.checked = state.terminalErrorsOnly;
    renderRawLog();
    updateTabScrollButtons();
    await loadArchive();
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', Bridge.init);
