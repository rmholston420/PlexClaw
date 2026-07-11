import { test, expect } from '@playwright/test';

test('terminal copy control remains usable after opening the drawer', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const terminalToggle = page.locator('#terminal-toggle');
  const terminalDrawer = page.locator('#terminal-drawer');
  const terminalCopy = page.locator('#terminal-copy');
  const terminalClear = page.locator('#terminal-clear');

  await expect(terminalToggle).toBeVisible();

  await terminalToggle.click();
  await expect(terminalDrawer).toBeVisible();
  await expect(terminalCopy).toBeVisible();
  await expect(terminalCopy).toBeEnabled();
  await expect(terminalClear).toBeVisible();
  await expect(terminalClear).toBeEnabled();

  await terminalCopy.click();

  await expect(terminalDrawer).toBeVisible();
  await expect(terminalCopy).toBeVisible();
  await expect(terminalCopy).toBeEnabled();
  await expect(terminalClear).toBeVisible();
  await expect(terminalClear).toBeEnabled();
});
