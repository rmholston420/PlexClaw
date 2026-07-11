import { test, expect } from '@playwright/test';

test('loads core frontend controls', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');
  await expect(page.locator('#runtime-mode-label')).toBeVisible();
  await expect(page.locator('#tool-search-select')).toBeVisible();
  await expect(page.locator('#provider-switcher')).toBeVisible();
  await expect(page.locator('#new-tab-btn')).toBeVisible();
  await expect(page.locator('#terminal-errors-only')).toBeVisible();
  await expect(page.locator('#export-session')).toBeVisible();
});
