export async function gotoCanonicalUi(page) {
  await page.goto('/');
}

export async function openTerminalDrawer(page) {
  const terminalToggle = page.locator('#terminal-toggle');
  const terminalDrawer = page.locator('#terminal-drawer');
  await terminalToggle.click();
  await terminalDrawer.waitFor({ state: 'visible' });
  return {
    terminalToggle,
    terminalDrawer,
    terminalClear: page.locator('#terminal-clear'),
    terminalCopy: page.locator('#terminal-copy'),
    terminalErrorsOnly: page.locator('#terminal-errors-only'),
  };
}

export async function openSearchModal(page) {
  const openSearch = page.locator('#open-search');
  const searchModal = page.locator('#search-modal');
  const searchInput = page.locator('#search-input-modal');
  await openSearch.click();
  await searchModal.waitFor({ state: 'visible' });
  return { openSearch, searchModal, searchInput };
}

export async function createAdditionalTabs(page, count) {
  const newTabBtn = page.locator('#new-tab-btn');
  for (let i = 0; i < count; i += 1) {
    await newTabBtn.click();
  }
  return {
    newTabBtn,
    tabs: page.locator('.session-tab'),
    tabbar: page.locator('#tabbar'),
    scrollLeft: page.locator('#tab-scroll-left'),
    scrollRight: page.locator('#tab-scroll-right'),
  };
}
