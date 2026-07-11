import { test, expect } from '@playwright/test';

test('Ctrl/Cmd+F opens the search modal and focuses the search input', async ({ page, browserName }) => {
  await page.goto('/plexclaw-ui-canonical.html');

  const searchModal = page.locator('#search-modal');
  const searchInput = page.locator('#search-input-modal');

  await expect(searchModal).toHaveAttribute('aria-hidden', 'true');

  const modifier = process.platform === 'darwin' ? 'Meta' : 'Control';
  await page.keyboard.press(`${modifier}+f`);

  await expect(searchModal).toHaveAttribute('aria-hidden', 'false');
  await expect(searchInput).toBeFocused();
});
