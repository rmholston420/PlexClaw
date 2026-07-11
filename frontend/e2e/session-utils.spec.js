import { test, expect } from '@playwright/test';

test('session utility controls are exposed in the current DOM', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  await expect(page.locator('#session-label')).toHaveCount(1);
  await expect(page.locator('#connection-status')).toHaveCount(1);

  await expect(page.locator('#runtime-mode-label')).toBeVisible();
  await expect(page.locator('#tool-search-select')).toBeVisible();

  await expect(page.locator('#export-session')).toBeVisible();
  await expect(page.locator('#export-session-json')).toBeVisible();
});
