import { test, expect } from '@playwright/test';

test('archive refresh control remains usable with archive surface visible', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const refreshArchive = page.locator('#refresh-archive');
  const archiveList = page.locator('#archive-list');
  const archiveSearch = page.locator('#archive-search');

  await expect(refreshArchive).toBeVisible();
  await expect(refreshArchive).toBeEnabled();
  await expect(archiveList).toBeVisible();
  await expect(archiveSearch).toBeVisible();

  await refreshArchive.click();

  await expect(refreshArchive).toBeVisible();
  await expect(refreshArchive).toBeEnabled();
  await expect(archiveList).toBeVisible();
  await expect(archiveSearch).toBeVisible();
});
