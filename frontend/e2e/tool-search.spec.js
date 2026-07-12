import { test, expect } from '@playwright/test';

test('tool search selector is exposed in the current DOM', async ({ page }) => {
  await page.goto('/');

  const toolSearch = page.locator('#tool-search-select');

  await expect(toolSearch).toBeVisible();
  await expect(toolSearch).toHaveCount(1);
  await expect(toolSearch).toBeEnabled();
});
