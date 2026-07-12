import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 45000,
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:8020',
    headless: true,
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'bash ./run.sh',
    port: 8020,
    reuseExistingServer: true,
    cwd: '..',
    timeout: 120000,
  },
  projects: [
    {
      name: 'chromium-live',
      use: { browserName: 'chromium' },
    },
  ],
});
