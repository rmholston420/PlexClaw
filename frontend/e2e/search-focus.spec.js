import { test, expect } from '@playwright/test';

test('opening search modal moves focus to the modal search input', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const openSearch = page.locator('#open-search');
  const searchInput = page.locator('#search-input-modal');

  await expect(openSearch).toBeVisible();
  await openSearch.click();
  await expect(searchInput).toBeFocused();
});
