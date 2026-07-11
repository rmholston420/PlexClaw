import { test, expect } from '@playwright/test';

test('archive search input remains editable and archive surface stays visible', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const archiveSearch = page.locator('#archive-search');
  const archiveList = page.locator('#archive-list');
  const refreshArchive = page.locator('#refresh-archive');

  await expect(archiveSearch).toBeVisible();
  await expect(archiveList).toBeVisible();
  await expect(refreshArchive).toBeVisible();
  await expect(refreshArchive).toBeEnabled();

  await archiveSearch.fill('session');
  await expect(archiveSearch).toHaveValue('session');
  await expect(archiveList).toBeVisible();

  await archiveSearch.fill('terminal');
  await expect(archiveSearch).toHaveValue('terminal');
  await expect(archiveList).toBeVisible();

  await archiveSearch.clear();
  await expect(archiveSearch).toHaveValue('');
  await expect(archiveList).toBeVisible();
});
