import { test, expect } from '@playwright/test';

test('new tab button adds a rendered session tab', async ({ page }) => {
  await page.goto('/');

  const newTabBtn = page.locator('#new-tab-btn');
  const tabButtons = page.locator('.session-tab');

  await expect(newTabBtn).toBeVisible();

  const before = await tabButtons.count();
  await newTabBtn.click();
  await expect(tabButtons).toHaveCount(before + 1);
});
