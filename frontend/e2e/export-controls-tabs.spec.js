import { test, expect } from '@playwright/test';

test('export controls remain visible and enabled across tab changes', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const newTabBtn = page.locator('#new-tab-btn');
  const markdownExport = page.locator('#export-session');
  const jsonExport = page.locator('#export-session-json');
  const tabs = page.locator('.session-tab');

  await expect(newTabBtn).toBeVisible();
  await expect(markdownExport).toBeVisible();
  await expect(markdownExport).toBeEnabled();
  await expect(jsonExport).toBeVisible();
  await expect(jsonExport).toBeEnabled();
  await expect(tabs).toHaveCount(1);

  await newTabBtn.click();
  await expect(tabs).toHaveCount(2);
  await expect(markdownExport).toBeVisible();
  await expect(markdownExport).toBeEnabled();
  await expect(jsonExport).toBeVisible();
  await expect(jsonExport).toBeEnabled();

  const firstTab = tabs.nth(0);
  await firstTab.click();

  await expect(markdownExport).toBeVisible();
  await expect(markdownExport).toBeEnabled();
  await expect(jsonExport).toBeVisible();
  await expect(jsonExport).toBeEnabled();
});
