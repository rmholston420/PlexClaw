import { test, expect } from '@playwright/test';

test('new tab button diagnostic reveals runtime tab state', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  page.on('pageerror', (err) => console.log('PAGEERROR:', err.message));
  page.on('console', (msg) => console.log(`BROWSER:${msg.type()}: ${msg.text()}`));

  const newTabButton = page.locator('#new-tab-btn');
  const tabbar = page.locator('#tabbar');

  await expect(newTabButton).toBeVisible();
  await expect(newTabButton).toBeEnabled();
  await expect(tabbar).toBeVisible();

  const before = await page.evaluate(() => {
    const runtime = globalThis;
    return {
      hasOpenNewTab: typeof runtime.openNewTab === 'function',
      hasRenderTabs: typeof runtime.renderTabs === 'function',
      hasState: typeof runtime.state !== 'undefined',
      tabsLength: runtime.state?.tabs?.length ?? null,
      activeTabId: runtime.state?.activeTabId ?? null,
      tabbarHtml: document.querySelector('#tabbar')?.innerHTML?.replace(/\s+/g, ' ').trim() ?? null,
      sessionTabCount: document.querySelectorAll('#tabbar .session-tab').length,
    };
  });

  console.log('BEFORE_RUNTIME=' + JSON.stringify(before));

  await newTabButton.click();
  await page.waitForTimeout(300);

  const after = await page.evaluate(() => {
    const runtime = globalThis;
    return {
      hasOpenNewTab: typeof runtime.openNewTab === 'function',
      hasRenderTabs: typeof runtime.renderTabs === 'function',
      hasState: typeof runtime.state !== 'undefined',
      tabsLength: runtime.state?.tabs?.length ?? null,
      activeTabId: runtime.state?.activeTabId ?? null,
      tabbarHtml: document.querySelector('#tabbar')?.innerHTML?.replace(/\s+/g, ' ').trim() ?? null,
      sessionTabCount: document.querySelectorAll('#tabbar .session-tab').length,
    };
  });

  console.log('AFTER_RUNTIME=' + JSON.stringify(after));

  expect(after.sessionTabCount).toBeGreaterThanOrEqual(before.sessionTabCount);
});
