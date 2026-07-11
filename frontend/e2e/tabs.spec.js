import { test, expect } from '@playwright/test';

test('new tab button causes an observable tab-state change', async ({ page }) => {
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
  const beforePressed = await tabButtons.evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute('aria-pressed') || '')
  );
  const beforeSelected = await tabButtons.evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute('aria-selected') || '')
  );

  await newTabButton.click();

  await expect
    .poll(async () => {
      const afterCount = await tabButtons.count();
      const afterLabels = await tabButtons.evaluateAll((nodes) =>
        nodes.map((node) => (node.textContent || '').trim())
      );
      const afterPressed = await tabButtons.evaluateAll((nodes) =>
        nodes.map((node) => node.getAttribute('aria-pressed') || '')
      );
      const afterSelected = await tabButtons.evaluateAll((nodes) =>
        nodes.map((node) => node.getAttribute('aria-selected') || '')
      );

      return JSON.stringify({
        beforeCount,
        afterCount,
        beforeLabels,
        afterLabels,
        beforePressed,
        afterPressed,
        beforeSelected,
        afterSelected,
      });
    })
    .not.toBe(
      JSON.stringify({
        beforeCount,
        afterCount: beforeCount,
        beforeLabels,
        afterLabels: beforeLabels,
        beforePressed,
        afterPressed: beforePressed,
        beforeSelected,
        afterSelected: beforeSelected,
      })
    );
});
