import { test, expect } from '@playwright/test';

test('observable controls respond in the DOM', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const manualBtn = page.locator('#mode-manual-btn');
  const autoBtn = page.locator('#mode-auto-btn');
  const cwdPill = page.locator('#cwd-pill');
  const cwdModal = page.locator('#cwd-modal');
  const cwdClose = page.locator('#cwd-close');
  const cwdCancel = page.locator('#cwd-cancel');

  await expect(manualBtn).toBeVisible();
  await expect(autoBtn).toBeVisible();
  await expect(cwdPill).toBeVisible();

  await manualBtn.click();
  await expect(manualBtn).toBeVisible();

  await autoBtn.click();
  await expect(autoBtn).toBeVisible();

  await cwdPill.click();
  await expect(cwdModal).toBeVisible();

  if (await cwdClose.count()) {
    await cwdClose.click();
  } else {
    await cwdCancel.click();
  }

  await expect(cwdModal).not.toBeVisible();
});
