import { test, expect } from '@playwright/test';

test('diagnose search modal wiring', async ({ page }) => {
  const logs = [];
  page.on('console', msg => logs.push(`console:${msg.type()}:${msg.text()}`));
  page.on('pageerror', err => logs.push(`pageerror:${err.message}`));

  await page.goto('/plexclaw-ui-canonical.html');

  const before = await page.evaluate(() => {
    const btn = document.getElementById('open-search');
    const modal = document.getElementById('search-modal');
    return {
      buttonExists: !!btn,
      modalExists: !!modal,
      modalAria: modal?.getAttribute('aria-hidden'),
      modalHiddenClass: modal?.classList.contains('hidden'),
      buttonDatasetBound: btn?.dataset.bound || null,
    };
  });

  await page.locator('#open-search').click();

  const afterClick = await page.evaluate(() => {
    const modal = document.getElementById('search-modal');
    return {
      modalAria: modal?.getAttribute('aria-hidden'),
      modalHiddenClass: modal?.classList.contains('hidden'),
    };
  });

  await page.evaluate(() => {
    document.getElementById('open-search')?.click();
  });

  const afterDomClick = await page.evaluate(() => {
    const modal = document.getElementById('search-modal');
    return {
      modalAria: modal?.getAttribute('aria-hidden'),
      modalHiddenClass: modal?.classList.contains('hidden'),
    };
  });

  console.log('BEFORE=' + JSON.stringify(before));
  console.log('AFTER_CLICK=' + JSON.stringify(afterClick));
  console.log('AFTER_DOM_CLICK=' + JSON.stringify(afterDomClick));
  for (const line of logs) console.log('LOG=' + line);

  expect(before.buttonExists).toBe(true);
  expect(before.modalExists).toBe(true);
});
