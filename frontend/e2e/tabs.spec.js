import { test, expect } from '@playwright/test';

test('new tab button creates another tab', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');
  const tabbar = page.locator('#tabbar');
  const initialButtons = await tabbar.locator('button').count();
  await page.locator('#new-tab-btn').click();
  await expect(tabbar.locator('button')).toHaveCount(initialButtons + 1);
});
