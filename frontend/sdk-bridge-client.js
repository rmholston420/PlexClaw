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
    modelLabel: document.getElementById('model-label'),
    sessionLabel: document.getElementById('session-label'),
    archiveList: document.getElementById('archive-list'),
    archiveSearch: document.getElementById('archive-search'),
    archiveSort: document.getElementById('archive-sort'),
    replayBanner: document.getElementById('replay-banner'),
    exitReplay: document.getElementById('exit-replay'),
    themeToggle: document.getElementById('theme-toggle'),
    refreshArchive: document.getElementById('refresh-archive'),
  };

  function hideWelcome() {
    if (el.welcome) el.welcome.classList.add('hidden');
  }

  function scrollBottom() {
    requestAnimationFrame(() => {
      el.transcript.scrollTop = el.transcript.scrollHeight;
    });
  }

  function setConnection(connected) {
    el.statusDot.classList.toggle('connected', connected);
    el.connectionLabel.textContent = connected ? 'Connected' : 'Disconnected';
  }

  function setSessionLabel(id) {
    el.sessionLabel.textContent = id ? `Session ${id.slice(0, 8)}` : 'No session';
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

  function appendAssistantDelta(text) {
    hideWelcome();
    let msg = document.querySelector('.msg.assistant.streaming:last-of-type');
    if (!msg) {
      msg = document.createElement('div');
      msg.className = 'msg assistant streaming';
      msg.textContent = '';
      el.transcript.appendChild(msg);
    }
    msg.textContent += text;
    scrollBottom();
  }

  function finalizeAssistant() {
    const msg = document.querySelector('.msg.assistant.streaming:last-of-type');
    if (msg) msg.classList.remove('streaming');
  }

  function appendSystemMessage(text, level='info') {
    hideWelcome();
    const div = document.createElement('div');
    div.className = 'system-msg';
    div.textContent = `[${level}] ${text}`;
    el.transcript.appendChild(div);
    scrollBottom();
  }

  function getOrCreateTool(toolId, toolName) {
    let block = state.toolEls.get(toolId);
    if (block) return block;

    hideWelcome();
    block = document.createElement('div');
    block.className = 'tool-block running';
    const expanded = !state.firstToolExpanded;
    state.firstToolExpanded = true;
    if (expanded) block.classList.add('expanded');

    const header = document.createElement('div');
    header.className = 'tool-header';
    const title = document.createElement('div');
    title.className = 'tool-title';
    title.textContent = `Tool: ${toolName}`;
    const status = document.createElement('div');
    status.className = 'muted tool-status';
    status.textContent = 'running';
    header.appendChild(title);
    header.appendChild(status);

    const body = document.createElement('div');
    body.className = 'tool-body';
    block.appendChild(header);
    block.appendChild(body);

    header.addEventListener('click', () => {
      block.classList.toggle('expanded');
    });

    el.transcript.appendChild(block);
    state.toolEls.set(toolId, block);
    scrollBottom();
    return block;
  }

  function renderEvent(evt) {
    switch (evt.type) {
      case 'session.ready':
        appendSystemMessage(`Live session ready (${evt.payload.model || state.model})`);
        break;
      case 'session.updated':
        appendSystemMessage('Session updated');
        break;
      case 'assistant.delta':
        appendAssistantDelta(evt.payload.text || '');
        break;
      case 'assistant.completed':
        finalizeAssistant();
        break;
      case 'tool.started': {
        const block = getOrCreateTool(evt.payload.tool_id, evt.payload.tool_name || 'tool');
        block.querySelector('.tool-body').textContent = JSON.stringify(evt.payload.tool_input, null, 2);
        break;
      }
      case 'tool.delta': {
        const block = getOrCreateTool(evt.payload.tool_id, 'tool');
        const body = block.querySelector('.tool-body');
        body.textContent += `${evt.payload.partial || ''}`;
        break;
      }
      case 'tool.completed': {
        const block = getOrCreateTool(evt.payload.tool_id, evt.payload.tool_name || 'tool');
        block.classList.remove('running');
        block.classList.add(evt.payload.is_error ? 'error' : 'done');
        block.querySelector('.tool-status').textContent = evt.payload.is_error ? 'error' : 'done';
        const body = block.querySelector('.tool-body');
        const current = body.textContent.trim();
        body.textContent = [current, typeof evt.payload.output === 'string' ? evt.payload.output : JSON.stringify(evt.payload.output, null, 2)].filter(Boolean).join('\n\n');
        break;
      }
      case 'tool.permission_required':
        appendSystemMessage('Tool permission required', 'warn');
        break;
      case 'system.message':
        appendSystemMessage(evt.payload.text || '', evt.payload.level || 'info');
        break;
      case 'session.interrupted':
        appendSystemMessage('Run interrupted by user', 'warn');
        break;
      case 'session.failed':
        appendSystemMessage(evt.payload.error || 'Session failed', 'error');
        break;
      case 'mcp.status':
        appendSystemMessage(`MCP: ${evt.payload.status || 'status update'}`);
        break;
      default:
        appendSystemMessage(`Unhandled event ${evt.type}`);
    }
  }

  async function api(path, options={}) {
    const res = await fetch(`${state.bridgeUrl}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) {
      throw new Error(`API ${path} failed: ${res.status}`);
    }
    return res.json();
  }

  async function createSession({ resumeSessionId=null, forkSession=false } = {}) {
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
    if (state.socket) state.socket.close();
    const url = `${state.wsBase}/${state.sessionId}?protocol_version=${state.protocolVersion}`;
    const ws = new WebSocket(url);
    state.socket = ws;
    ws.addEventListener('open', () => setConnection(true));
    ws.addEventListener('close', () => setConnection(false));
    ws.addEventListener('message', (msg) => {
      const evt = JSON.parse(msg.data);
      renderEvent(evt);
    });
  }

  function sendPrompt() {
    const prompt = el.promptInput.value.trim();
    if (!prompt || !state.socket || state.socket.readyState !== WebSocket.OPEN) return;
    setReplayMode(false);
    state.socket.send(JSON.stringify({ prompt }));
    el.promptInput.value = '';
  }

  async function interrupt() {
    if (!state.sessionId) return;
    await api(`/api/sessions/${state.sessionId}/interrupt`, { method: 'POST' });
  }

  async function replaySession(id) {
    const events = await api(`/api/sessions/${id}/replay`);
    clearTranscript();
    setReplayMode(true);
    for (const evt of events) renderEvent(evt);
  }

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
    if (mode === 'title') arr.sort((a,b) => (a.title||'').localeCompare(b.title||''));
    if (mode === 'tag') arr.sort((a,b) => (a.tag||'').localeCompare(b.tag||''));
    if (mode === 'root') arr.sort((a,b) => (a.root_session_id||a.id).localeCompare(b.root_session_id||b.id));
    if (mode === 'recent') arr.sort((a,b) => String(b.updated_at||'').localeCompare(String(a.updated_at||'')));
    return arr;
  }

  async function renameSession(id, currentTitle) {
    const title = prompt('Rename session', currentTitle || '');
    if (title === null) return;
    await api(`/api/archive/sessions/${id}/rename`, { method: 'POST', body: JSON.stringify({ title }) });
    await loadArchive();
  }

  async function tagSession(id, currentTag) {
    const tag = prompt('Set tag (leave blank to clear)', currentTag || '') ?? '';
    await api(`/api/archive/sessions/${id}/tag`, { method: 'POST', body: JSON.stringify({ tag: tag || null }) });
    await loadArchive();
  }

  function renderArchive() {
    const query = el.archiveSearch.value.trim().toLowerCase();
    const filtered = sortArchive(state.archive).filter(item => {
      const hay = [
        item.title, item.summary, item.id, item.root_session_id, item.cwd, item.tag,
      ].filter(Boolean).join(' ').toLowerCase();
      return !query || hay.includes(query);
    });

    const groups = groupByLineage(filtered);
    el.archiveList.innerHTML = '';
    if (!groups.length) {
      el.archiveList.innerHTML = '<div class="muted">No archived sessions found.</div>';
      return;
    }

    for (const [root, items] of groups) {
      const group = document.createElement('div');
      group.className = 'lineage-group';
      const header = document.createElement('div');
      header.className = 'lineage-header';
      const open = state.lineageOpen.has(root) ? state.lineageOpen.get(root) : items.length === 1;
      state.lineageOpen.set(root, open);
      header.innerHTML = `<span>${open ? '▾' : '▸'} Lineage ${root.slice(0,8)}</span><span class="muted">${items.length}</span>`;
      const body = document.createElement('div');
      body.className = 'group-body';
      if (!open) body.classList.add('hidden');

      header.addEventListener('click', () => {
        const next = !state.lineageOpen.get(root);
        state.lineageOpen.set(root, next);
        renderArchive();
      });

      items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'session-card';
        if (item.id === state.sessionId) card.classList.add('active');
        const chips = [
          item.tag ? `<span class="chip">tag:${item.tag}</span>` : '',
          item.model ? `<span class="chip">${item.model}</span>` : '',
          item.message_count != null ? `<span class="chip">${item.message_count} msgs</span>` : '',
        ].join(' ');
        card.innerHTML = `
          <div class="session-title">${item.title || 'Untitled session'}</div>
          <div class="session-meta">${item.summary || ''}<br>${item.id}</div>
          <div>${chips}</div>
          <div class="card-actions">
            <button data-action="continue">Continue</button>
            <button data-action="fork">Fork</button>
            <button data-action="replay">Replay</button>
            <button data-action="rename">Rename</button>
            <button data-action="tag">Tag</button>
          </div>
        `;
        card.querySelector('[data-action="continue"]').addEventListener('click', async () => {
          clearTranscript();
          await createSession({ resumeSessionId: item.id, forkSession: false });
        });
        card.querySelector('[data-action="fork"]').addEventListener('click', async () => {
          clearTranscript();
          await createSession({ resumeSessionId: item.id, forkSession: true });
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

      group.appendChild(header);
      group.appendChild(body);
      el.archiveList.appendChild(group);
    }
  }

  async function loadArchive() {
    try {
      state.archive = await api('/api/archive/sessions');
      renderArchive();
    } catch (err) {
      console.error(err);
    }
  }

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
      await createSession();
    });
    el.exitReplay.addEventListener('click', () => {
      setReplayMode(false);
      clearTranscript();
      if (el.welcome) el.welcome.classList.remove('hidden');
    });
    el.archiveSearch.addEventListener('input', renderArchive);
    el.archiveSort.addEventListener('change', renderArchive);
    el.themeToggle.addEventListener('click', () => {
      document.body.classList.toggle('light');
    });
    el.refreshArchive.addEventListener('click', loadArchive);
    document.querySelectorAll('.prompt-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        el.promptInput.value = btn.textContent;
        el.promptInput.focus();
      });
    });
  }

  async function init() {
    bindEvents();
    await loadArchive();
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', Bridge.init);
