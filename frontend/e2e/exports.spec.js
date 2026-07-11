import { test, expect } from '@playwright/test';

test('export controls are exposed in the current DOM', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const exportText = page.locator('#export-session');
  const exportJson = page.locator('#export-session-json');

  await expect(exportText).toBeVisible();
  await expect(exportJson).toBeVisible();

  await expect(exportText).toHaveCount(1);
  await expect(exportJson).toHaveCount(1);

  await expect(exportText).toContainText(/export/i);
  await expect(exportJson).toContainText(/json/i);
});
