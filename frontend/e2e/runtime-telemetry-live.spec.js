import { test, expect } from '@playwright/test';

test('live runtime telemetry surfaces are visible and can expand', async ({ page }) => {
  await page.goto('/');

  const runtimeShell = page.locator('#runtime-meta-shell');
  const runtimeToggle = page.locator('#runtime-meta-toggle');
  const runtimePanel = page.locator('#runtime-meta-panel');
  const hookList = page.locator('#hook-list');
  const completionStopReason = page.locator('#completion-stop-reason');
  const completionInputTokens = page.locator('#completion-input-tokens');
  const completionOutputTokens = page.locator('#completion-output-tokens');
  const sessionCwdMeta = page.locator('#session-cwd-meta');
  const sessionRuntimeMeta = page.locator('#session-runtime-meta');
  const sessionConfigMeta = page.locator('#session-config-meta');

  await expect(runtimeShell).toBeVisible();
  await expect(runtimeToggle).toBeVisible();
  await expect(runtimePanel).toBeHidden();

  await runtimeToggle.click();

  await expect(runtimeShell).toHaveClass(/expanded/);
  await expect(runtimeToggle).toHaveAttribute('aria-expanded', 'true');
  await expect(runtimePanel).toBeVisible();

  await expect(page.locator('#provider-runtime-meta')).toBeVisible();
  await expect(page.locator('#tool-runtime-meta')).toBeVisible();
  await expect(page.locator('#provider-base-url-meta')).toBeVisible();
  await expect(page.locator('#provider-reason-meta')).toBeVisible();

  await expect(sessionCwdMeta).toBeVisible();
  await expect(sessionRuntimeMeta).toBeVisible();
  await expect(sessionConfigMeta).toBeVisible();

  await expect(hookList).toBeVisible();
  await expect(completionStopReason).toBeVisible();
  await expect(completionInputTokens).toBeVisible();
  await expect(completionOutputTokens).toBeVisible();

  await expect(completionStopReason).toContainText(/No completion yet|end_turn|stop|completed/i);
  await expect(completionInputTokens).toContainText(/--|\d|K|M/i);
  await expect(completionOutputTokens).toContainText(/--|\d|K|M/i);
});
