import { test, expect } from '@playwright/test';

test('observable controls are present in the DOM', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  await expect(page.locator('#mode-manual-btn')).toBeVisible();
  await expect(page.locator('#mode-auto-btn')).toBeVisible();
  await expect(page.locator('#cwd-pill')).toBeVisible();
  await expect(page.locator('#export-session')).toBeVisible();
  await expect(page.locator('#export-session-json')).toBeVisible();
  await expect(page.locator('#provider-switcher')).toBeVisible();
  await expect(page.locator('#model-select')).toBeVisible();
  await expect(page.locator('#terminal-errors-only')).toHaveCount(1);
});
