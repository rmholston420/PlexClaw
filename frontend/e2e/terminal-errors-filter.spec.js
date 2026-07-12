import { test, expect } from '@playwright/test';

test('terminal errors-only filter toggles cleanly after opening the drawer', async ({ page }) => {
  await page.goto('/');

  const terminalToggle = page.locator('#terminal-toggle');
  const terminalDrawer = page.locator('#terminal-drawer');
  const errorsOnly = page.locator('#terminal-errors-only');

  await expect(terminalToggle).toBeVisible();

  await terminalToggle.click();
  await expect(terminalDrawer).toBeVisible();
  await expect(errorsOnly).toBeVisible();

  await expect(errorsOnly).not.toBeChecked();
  await errorsOnly.check();
  await expect(errorsOnly).toBeChecked();

  await errorsOnly.uncheck();
  await expect(errorsOnly).not.toBeChecked();
});
