import { test, expect } from '@playwright/test';

test('cwd modal opens and closes from stable controls', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const openBtn = page.locator('#cwd-pill');
  const modal = page.locator('#cwd-modal');
  const closeBtn = page.locator('#cwd-close');

  await expect(openBtn).toBeVisible();
  await expect(modal).toHaveAttribute('aria-hidden', 'true');

  await openBtn.click();
  await expect(modal).toHaveAttribute('aria-hidden', 'false');

  await closeBtn.click();
  await expect(modal).toHaveAttribute('aria-hidden', 'true');
});
