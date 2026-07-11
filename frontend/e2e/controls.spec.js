import { test, expect } from '@playwright/test';

test('observable controls respond in the DOM', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const manualBtn = page.locator('#mode-manual-btn');
  const autoBtn = page.locator('#mode-auto-btn');
  const errorsOnly = page.locator('#terminal-errors-only');
  const cwdPill = page.locator('#cwd-pill');
  const cwdModal = page.locator('#cwd-modal');

  await expect(manualBtn).toBeVisible();
  await expect(autoBtn).toBeVisible();
  await expect(errorsOnly).toBeVisible();
  await expect(cwdPill).toBeVisible();

  await manualBtn.click();
  await expect(manualBtn).toHaveAttribute('aria-pressed', /true|false/);

  await autoBtn.click();
  await expect(autoBtn).toHaveAttribute('aria-pressed', /true|false/);

  const beforeChecked = await errorsOnly.isChecked();
  await errorsOnly.click();
  expect(await errorsOnly.isChecked()).toBe(!beforeChecked);

  await cwdPill.click();
  await expect(cwdModal).toBeVisible();
});
