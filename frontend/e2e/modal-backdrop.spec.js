import { test, expect } from '@playwright/test';

test('backdrop click closes search and cwd modals', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const searchOpen = page.locator('#open-search');
  const searchModal = page.locator('#search-modal');
  const cwdOpen = page.locator('#cwd-pill');
  const cwdModal = page.locator('#cwd-modal');

  await searchOpen.click();
  await expect(searchModal).toHaveAttribute('aria-hidden', 'false');
  await searchModal.click({ position: { x: 5, y: 5 } });
  await expect(searchModal).toHaveAttribute('aria-hidden', 'true');

  await cwdOpen.click();
  await expect(cwdModal).toHaveAttribute('aria-hidden', 'false');
  await cwdModal.click({ position: { x: 5, y: 5 } });
  await expect(cwdModal).toHaveAttribute('aria-hidden', 'true');
});
