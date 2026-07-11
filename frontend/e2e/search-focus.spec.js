import { test, expect } from '@playwright/test';
import { gotoCanonicalUi, openSearchModal } from './helpers/canonical-ui.js';

test('opening search modal moves focus to the modal search input', async ({ page }) => {
  await gotoCanonicalUi(page);

  const { searchModal, searchInput } = await openSearchModal(page);

  await expect(searchModal).toBeVisible();
  await expect(searchInput).toBeFocused();
});
