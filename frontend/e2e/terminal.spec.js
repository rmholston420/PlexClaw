import { test, expect } from '@playwright/test';

test('terminal controls are exposed in the current DOM', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  await expect(page.locator('#terminal-toggle')).toHaveCount(1);
  await expect(page.locator('#terminal-drawer')).toHaveCount(1);
  await expect(page.locator('#terminal-clear')).toHaveCount(1);
  await expect(page.locator('#terminal-copy')).toHaveCount(1);
  await expect(page.locator('#terminal-errors-only')).toHaveCount(1);
  await expect(page.locator('#terminal-count')).toHaveCount(1);
  await expect(page.locator('#terminal-pre')).toHaveCount(1);
});
