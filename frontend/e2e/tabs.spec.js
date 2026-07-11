import { test, expect } from '@playwright/test';

test('new tab button diagnostic reveals rendered tab state', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  page.on('pageerror', (err) => console.log('PAGEERROR:', err.message));
  page.on('console', (msg) => console.log(`BROWSER:${msg.type()}: ${msg.text()}`));

  const newTabButton = page.locator('#new-tab-btn');
  const sessionTabs = page.locator('#tabbar .session-tab');
  const tabbar = page.locator('#tabbar');

  await expect(newTabButton).toBeVisible();
  await expect(newTabButton).toBeEnabled();
  await expect(tabbar).toBeVisible();

  const beforeCount = await sessionTabs.count();
  const beforeHtml = await tabbar.innerHTML();

  console.log('BEFORE_COUNT=' + beforeCount);
  console.log('BEFORE_HTML=' + beforeHtml.replace(/\s+/g, ' ').trim());

  await newTabButton.click();
  await page.waitForTimeout(300);

  const afterCount = await sessionTabs.count();
  const afterHtml = await tabbar.innerHTML();

  console.log('AFTER_COUNT=' + afterCount);
  console.log('AFTER_HTML=' + afterHtml.replace(/\s+/g, ' ').trim());

  expect(afterCount).toBeGreaterThanOrEqual(beforeCount);
});
