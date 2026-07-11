import { test, expect } from '@playwright/test';

test('terminal toggle opens and closes the terminal panel', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const terminalToggle = page.locator('#terminal-toggle');
  const terminalPanel = page.locator('#terminal-drawer');

  await expect(terminalToggle).toBeVisible();

  const beforeClass = await terminalPanel.getAttribute('class');
  const beforeHidden = await terminalPanel.getAttribute('aria-hidden');

  await terminalToggle.click();

  const afterOpenClass = await terminalPanel.getAttribute('class');
  const afterOpenHidden = await terminalPanel.getAttribute('aria-hidden');

  expect(
    afterOpenClass !== beforeClass || afterOpenHidden !== beforeHidden
  ).toBeTruthy();

  await terminalToggle.click();

  const afterCloseClass = await terminalPanel.getAttribute('class');
  const afterCloseHidden = await terminalPanel.getAttribute('aria-hidden');

  expect(
    afterCloseClass === beforeClass || afterCloseHidden === beforeHidden
  ).toBeTruthy();
});
