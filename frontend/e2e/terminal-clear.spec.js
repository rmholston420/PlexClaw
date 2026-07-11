import { test, expect } from '@playwright/test';

test('terminal clear control remains usable after opening the drawer', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const terminalToggle = page.locator('#terminal-toggle');
  const terminalDrawer = page.locator('#terminal-drawer');
  const terminalClear = page.locator('#terminal-clear');
  const terminalCopy = page.locator('#terminal-copy');

  await expect(terminalToggle).toBeVisible();

  await terminalToggle.click();
  await expect(terminalDrawer).toBeVisible();
  await expect(terminalClear).toBeVisible();
  await expect(terminalClear).toBeEnabled();
  await expect(terminalCopy).toBeVisible();
  await expect(terminalCopy).toBeEnabled();

  await terminalClear.click();

  await expect(terminalDrawer).toBeVisible();
  await expect(terminalClear).toBeVisible();
  await expect(terminalClear).toBeEnabled();
  await expect(terminalCopy).toBeVisible();
  await expect(terminalCopy).toBeEnabled();
});
