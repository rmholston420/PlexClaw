(function (global) {
  function normalizeArchiveText(value) {
    return String(value || '').toLowerCase().replace(/\s+/g, ' ').trim();
  }

  function archiveSearchHaystack(item) {
    return [
      item?.title,
      item?.summary,
      item?.id,
      item?.root_session_id,
      item?.cwd,
      item?.tag,
      item?.model,
    ].filter(Boolean).join(' ');
  }

  function sortArchiveItems(items, mode) {
    const arr = [...(items || [])];
    if (mode === 'title') {
      arr.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
      return arr;
    }
    if (mode === 'tag') {
      arr.sort((a, b) => (a.tag || '').localeCompare(b.tag || ''));
      return arr;
    }
    if (mode === 'root') {
      arr.sort((a, b) => (a.root_session_id || a.id || '').localeCompare(b.root_session_id || b.id || ''));
      return arr;
    }
    arr.sort((a, b) => String(b.updated_at || b.created_at || '').localeCompare(String(a.updated_at || a.created_at || '')));
    return arr;
  }

  function groupArchiveByLineage(items) {
    const groups = new Map();
    for (const item of items || []) {
      const root = item.root_session_id || item.id || 'unknown';
      if (!groups.has(root)) groups.set(root, []);
      groups.get(root).push(item);
    }
    return [...groups.entries()].map(([root, grouped]) => ({ root, items: grouped }));
  }

  function archiveLineageLabel(item) {
    const rootId = item?.root_session_id || item?.id || '';
    const isRoot = rootId === item?.id;
    return isRoot ? 'Lineage root' : `Branch of ${String(rootId).slice(0, 8)}`;
  }

  function archiveRoleLabel(item) {
    const rootId = item?.root_session_id || item?.id || '';
    return rootId === item?.id ? 'Root' : 'Branch';
  }

  const api = {
    normalizeArchiveText,
    archiveSearchHaystack,
    sortArchiveItems,
    groupArchiveByLineage,
    archiveLineageLabel,
    archiveRoleLabel,
  };

  global.ClaudeArchiveUtils = api;
  global.PlexClawArchiveUtils = api;
})(window);
