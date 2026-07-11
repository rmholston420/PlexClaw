import { test, expect } from '@playwright/test';

test('clicking a session tab activates it after creating a new tab', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const newTabBtn = page.locator('#new-tab-btn');
  const tabButtons = page.locator('.session-tab');

  await expect(newTabBtn).toBeVisible();
  await expect(tabButtons).toHaveCount(1);

  const firstTab = tabButtons.nth(0);
  await expect(firstTab).toHaveAttribute('aria-selected', 'true');

  await newTabBtn.click();
  await expect(tabButtons).toHaveCount(2);

  const secondTab = tabButtons.nth(1);
  await secondTab.click();

  await expect(secondTab).toHaveAttribute('aria-selected', 'true');
  await expect(firstTab).toHaveAttribute('aria-selected', 'false');
});
