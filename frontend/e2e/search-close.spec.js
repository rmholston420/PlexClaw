import { test, expect } from '@playwright/test';

test('search close button closes the search modal', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const openSearch = page.locator('#open-search');
  const searchModal = page.locator('#search-modal');
  const searchClose = page.locator('#search-close');

  await expect(openSearch).toBeVisible();

  await openSearch.click();
  await expect(searchModal).toHaveAttribute('aria-hidden', 'false');

  await searchClose.click();
  await expect(searchModal).toHaveAttribute('aria-hidden', 'true');
});
