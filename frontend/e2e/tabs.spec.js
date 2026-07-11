import { test, expect } from '@playwright/test';

test('new tab button renders a new session tab and marks it active', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const newTabButton = page.locator('#new-tab-btn');
  const sessionTabs = page.locator('#tabbar .session-tab');
  const activeSessionTab = page.locator('#tabbar .session-tab.active');

  await expect(newTabButton).toBeVisible();
  await expect(newTabButton).toBeEnabled();

  const beforeCount = await sessionTabs.count();

  await newTabButton.click();

  await expect(sessionTabs).toHaveCount(beforeCount + 1);
  await expect(activeSessionTab).toHaveCount(1);
  await expect(sessionTabs.last()).toHaveClass(/active/);
  await expect(sessionTabs.last()).toContainText(/Tab\s+\d+/);
});
