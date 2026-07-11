import { test, expect } from '@playwright/test';

test('runtime mode controls are exposed in the current DOM', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const modeLabel = page.locator('#runtime-mode-label');
  const manualBtn = page.locator('#mode-manual-btn');
  const autoBtn = page.locator('#mode-auto-btn');

  await expect(modeLabel).toBeVisible();
  await expect(manualBtn).toBeVisible();
  await expect(autoBtn).toBeVisible();

  await expect(modeLabel).toHaveCount(1);
  await expect(manualBtn).toHaveCount(1);
  await expect(autoBtn).toHaveCount(1);

  await expect(modeLabel).not.toHaveText(/^\s*$/);
});
