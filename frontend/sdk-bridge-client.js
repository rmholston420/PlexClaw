const Bridge = (() => {
  const state = {
    bridgeUrl: 'http://127.0.0.1:8020',
    wsBase: 'ws://127.0.0.1:8020/ws',
    protocolVersion: '0.2.0',
    sessionId: null,
    socket: null,
    model: 'claude-sonnet-4-5',
    replayMode: false,
    archive: [],
    lineageOpen: new Map(),
    toolEls: new Map(),
    firstToolExpanded: false,
  };

  const el = {
    transcript: document.getElementById('transcript'),
    welcome: document.getElementById('welcome'),
    promptInput: document.getElementById('prompt-input'),
    sendBtn: document.getElementById('send-btn'),
    interruptBtn: document.getElementById('interrupt-btn'),
    replayCurrentBtn: document.getElementById('replay-current-btn'),
    newSessionBtn: document.getElementById('new-session'),
    statusDot: document.getElementById('status-dot'),
    connectionLabel: document.getElementById('connection-label'),
    sessionLabel: document.getElementById('session-label'),
    archiveList: document.getElementById('archive-list'),
    archiveSearch: document.getElementById('archive-search'),
    archiveSort: document.getElementById('archive-sort'),
    replayBanner: document.getElementById('replay-banner'),
    exitReplay: document.getElementById('exit-replay'),
    modelSelect: document.getElementById('model-select'),
    refreshArchive: document.getElementById('refresh-archive'),
  };

  // ---- Helpers ----
  function hideWelcome() {
    if (el.welcome) el.welcome.classList.add('hidden');
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

  function clearTranscript() {
    el.transcript.innerHTML = '';
    state.toolEls.clear();
    state.firstToolExpanded = false;
  }

  // ---- Markdown-lite renderer ----
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
      el.transcript.appendChild(currentAssistantEl);
    }
    currentAssistantText += text;
    // Simple incremental rendering — full re-render on each delta is expensive for large outputs;
    // use textContent streaming then do a final markdown pass on completion
    currentAssistantEl.textContent = currentAssistantText;
    scrollBottom();
  }

  function finalizeAssistant() {
    if (currentAssistantEl) {
      currentAssistantEl.classList.remove('streaming');
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

  function escapeHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function renderEvent(evt) {
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
      case 'tool.permission_required':
        appendSystemMessage('⚠ Tool permission required — check terminal', 'warn');
        break;
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

  async function createSession({ resumeSessionId = null, forkSession = false } = {}) {
    state.model = el.modelSelect?.value || state.model;
    const body = {
      model: state.model,
      cwd: null,
      provider: 'cloud',
      permission_mode: 'default',
      system_prompt: null,
      resume_session_id: resumeSessionId,
      fork_session: forkSession,
    };
    const data = await api('/api/sessions', { method: 'POST', body: JSON.stringify(body) });
    state.sessionId = data.session_id;
    setSessionLabel(state.sessionId);
    connectSocket();
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
    el.transcript.appendChild(userMsg);
    scrollBottom();

    state.socket.send(JSON.stringify({ prompt }));
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
    });
  }

  // ---- Events ----
  function bindEvents() {
    el.sendBtn.addEventListener('click', sendPrompt);
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
    bindEvents();
    bindTextareaResize();
    await loadArchive();
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', Bridge.init);
