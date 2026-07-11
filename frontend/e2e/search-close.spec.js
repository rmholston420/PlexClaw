import { test, expect } from '@playwright/test';
import { gotoCanonicalUi, openSearchModal } from './helpers/canonical-ui.js';

test('search close button closes the search modal', async ({ page }) => {
  await gotoCanonicalUi(page);

  const { searchModal } = await openSearchModal(page);
  const searchClose = page.locator('#search-close');

  await expect(searchModal).toHaveAttribute('aria-hidden', 'false');
  await expect(searchClose).toBeVisible();

  await searchClose.click();

  await expect(searchModal).toHaveAttribute('aria-hidden', 'true');
});
