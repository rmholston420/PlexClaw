import { test, expect } from '@playwright/test';

test('tab scroll controls remain visible after creating multiple tabs', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const newTabBtn = page.locator('#new-tab-btn');
  const scrollLeft = page.locator('#tab-scroll-left');
  const scrollRight = page.locator('#tab-scroll-right');
  const tabbar = page.locator('#tabbar');
  const tabs = page.locator('.session-tab');

  await expect(newTabBtn).toBeVisible();
  await expect(scrollLeft).toBeVisible();
  await expect(scrollRight).toBeVisible();
  await expect(tabbar).toBeVisible();

  for (let i = 0; i < 6; i += 1) {
    await newTabBtn.click();
  }

  await expect(tabs).toHaveCount(7);
  await expect(scrollLeft).toBeVisible();
  await expect(scrollRight).toBeVisible();
  await expect(tabbar).toBeVisible();
});
