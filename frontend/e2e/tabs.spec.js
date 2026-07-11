import { test, expect } from '@playwright/test';

test('new tab button is present and clickable', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const newTabButton = page.locator('#new-tab-btn');
  await expect(newTabButton).toBeVisible();
  await expect(newTabButton).toBeEnabled();

  await newTabButton.click();
});
