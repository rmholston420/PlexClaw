import { test, expect } from '@playwright/test';
import { gotoMainUi, openSearchModal } from './helpers/canonical-ui.js';

test('opening search modal moves focus to the modal search input', async ({ page }) => {
  await gotoMainUi(page);

  const { searchModal, searchInput } = await openSearchModal(page);

  await expect(searchModal).toBeVisible();
  await expect(searchInput).toBeFocused();
});
