import { test, expect } from '@playwright/test';

test('new tab button creates and activates a new tab', async ({ page }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const newTabButton = page.locator('#new-tab-btn');
  const tabButtons = page.locator('#tabbar button');

  await expect(newTabButton).toBeVisible();
  await expect(newTabButton).toBeEnabled();
  await expect(tabButtons.first()).toBeVisible();

  const beforeCount = await tabButtons.count();
  const beforeLabels = await tabButtons.evaluateAll((nodes) =>
    nodes.map((node) => (node.textContent || '').trim())
  );

  await newTabButton.click();

  await expect(tabButtons).toHaveCount(beforeCount + 1);

  const afterLabels = await tabButtons.evaluateAll((nodes) =>
    nodes.map((node) => (node.textContent || '').trim())
  );
  expect(afterLabels.length).toBe(beforeLabels.length + 1);
  expect(afterLabels).not.toEqual(beforeLabels);

  await expect(tabButtons.last()).toBeVisible();
});
