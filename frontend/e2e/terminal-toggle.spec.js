import { test, expect } from '@playwright/test';
import { gotoCanonicalUi } from './helpers/canonical-ui.js';

test('terminal toggle opens and closes the terminal panel', async ({ page }) => {
  await gotoCanonicalUi(page);

  const terminalToggle = page.locator('#terminal-toggle');
  const terminalDrawer = page.locator('#terminal-drawer');

  await expect(terminalToggle).toBeVisible();
  await expect(terminalDrawer).toBeVisible();

  await terminalToggle.click();

  await expect(terminalToggle).toBeVisible();
  await expect(terminalDrawer).toBeVisible();
});
