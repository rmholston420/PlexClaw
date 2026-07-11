import { test, expect } from '@playwright/test';

test('search modal opens and closes from stable controls', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const openBtn = page.locator('#open-search');
  const modal = page.locator('#search-modal');
  const closeBtn = page.locator('#search-close');

  await expect(openBtn).toBeVisible();
  await expect(modal).toHaveAttribute('aria-hidden', 'true');

  await openBtn.click();
  await expect(modal).toHaveAttribute('aria-hidden', 'false');

  await closeBtn.click();
  await expect(modal).toHaveAttribute('aria-hidden', 'true');
});
