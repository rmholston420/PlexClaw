import { test, expect } from '@playwright/test';

test('new tab button updates the tab UI', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const tabbar = page.locator('#tabbar');
  await expect(tabbar).toBeVisible();

  const before = await tabbar.textContent();
  await page.locator('#new-tab-btn').click();
  await page.waitForTimeout(250);
  const after = await tabbar.textContent();

  expect(after).not.toBe(before);
});
