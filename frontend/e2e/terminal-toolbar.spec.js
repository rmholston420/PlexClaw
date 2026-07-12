import { test, expect } from '@playwright/test';
import { gotoMainUi, openTerminalDrawer } from './helpers/canonical-ui.js';

test('terminal toolbar copy and clear controls remain visible and enabled', async ({ page }) => {
  await gotoMainUi(page);

  const { terminalDrawer, terminalClear, terminalCopy } = await openTerminalDrawer(page);

  await expect(terminalDrawer).toBeVisible();
  await expect(terminalClear).toBeVisible();
  await expect(terminalClear).toBeEnabled();
  await expect(terminalCopy).toBeVisible();
  await expect(terminalCopy).toBeEnabled();
});
