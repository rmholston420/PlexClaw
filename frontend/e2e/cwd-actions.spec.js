import { test, expect } from '@playwright/test';

test('cwd modal cancel and confirm controls close the modal', async ({ page }) => {
  await page.goto('/');

  const cwdPill = page.locator('#cwd-pill');
  const cwdModal = page.locator('#cwd-modal');
  const cwdCancel = page.locator('#cwd-cancel');
  const cwdConfirm = page.locator('#cwd-confirm');

  await expect(cwdPill).toBeVisible();

  await cwdPill.click();
  await expect(cwdModal).toHaveAttribute('aria-hidden', 'false');
  await expect(cwdCancel).toBeVisible();
  await expect(cwdConfirm).toBeVisible();

  await cwdCancel.click();
  await expect(cwdModal).toHaveAttribute('aria-hidden', 'true');

  await cwdPill.click();
  await expect(cwdModal).toHaveAttribute('aria-hidden', 'false');

  await cwdConfirm.click();
  await expect(cwdModal).toHaveAttribute('aria-hidden', 'true');
});
