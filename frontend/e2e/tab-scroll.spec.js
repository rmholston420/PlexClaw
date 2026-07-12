import { test, expect } from '@playwright/test';
import { gotoMainUi, createAdditionalTabs } from './helpers/canonical-ui.js';

test('tab scroll controls remain visible after creating multiple tabs', async ({ page }) => {
  await gotoMainUi(page);

  const { newTabBtn, tabs, tabbar, scrollLeft, scrollRight } = await createAdditionalTabs(page, 6);

  await expect(newTabBtn).toBeVisible();
  await expect(tabbar).toBeVisible();
  await expect(scrollLeft).toBeVisible();
  await expect(scrollRight).toBeVisible();
  await expect(tabs).toHaveCount(7);
});
