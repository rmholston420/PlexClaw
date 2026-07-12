import { test, expect } from '@playwright/test';

test('composer controls are exposed in the current DOM', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('#composer')).toHaveCount(1);
  await expect(page.locator('#prompt-input')).toBeVisible();
  await expect(page.locator('#send-btn')).toBeVisible();

  await expect(page.locator('#attach-file-btn')).toHaveCount(1);
  await expect(page.locator('#attach-file-input')).toHaveCount(1);
  await expect(page.locator('#prompt-stats')).toHaveCount(1);
});
