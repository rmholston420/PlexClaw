import { test, expect } from '@playwright/test';

test('observable controls match current DOM exposure', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('#mode-manual-btn')).toBeVisible();
  await expect(page.locator('#mode-auto-btn')).toBeVisible();
  await expect(page.locator('#cwd-pill')).toBeVisible();
  await expect(page.locator('#export-session')).toBeVisible();
  await expect(page.locator('#export-session-json')).toBeVisible();

  await expect(page.locator('#provider-switcher')).toHaveCount(1);
  await expect(page.locator('#model-select')).toHaveCount(1);
  await expect(page.locator('#terminal-errors-only')).toHaveCount(1);
});
