import { test, expect } from '@playwright/test';

test('archive controls are exposed in the current DOM', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  await expect(page.locator('#archive-list')).toHaveCount(1);
  await expect(page.locator('#archive-search')).toBeVisible();
  await expect(page.locator('#archive-sort')).toBeVisible();
  await expect(page.locator('#refresh-archive')).toHaveCount(1);
});
