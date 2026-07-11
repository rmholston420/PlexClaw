import { test, expect } from '@playwright/test';
import { gotoCanonicalUi, openTerminalDrawer } from './helpers/canonical-ui.js';

test('terminal copy control remains usable after opening the drawer', async ({ page }) => {
  await gotoCanonicalUi(page);

  const { terminalDrawer, terminalCopy, terminalClear } = await openTerminalDrawer(page);

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
