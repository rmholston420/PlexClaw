import { test, expect } from '@playwright/test';

test('clicking a session tab activates it after creating a new tab', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const newTabBtn = page.locator('#new-tab-btn');
  const tabButtons = page.locator('.session-tab');

  await expect(newTabBtn).toBeVisible();
  await expect(tabButtons).toHaveCount(1);

  const firstTab = tabButtons.nth(0);
  await expect(firstTab).toHaveClass(/active/);

  await newTabBtn.click();
  await expect(tabButtons).toHaveCount(2);

  const secondTab = tabButtons.nth(1);
  await expect(secondTab).toHaveClass(/active/);
  await expect(firstTab).not.toHaveClass(/active/);

  await firstTab.click();

  await expect(firstTab).toHaveClass(/active/);
  await expect(secondTab).not.toHaveClass(/active/);
});
