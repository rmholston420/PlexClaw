import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: [
    'runtime-telemetry-live.spec.js',
    'controls.spec.js',
    'composer.spec.js',
    'runtime-mode.spec.js',
    'exports.spec.js',
    'archive.spec.js',
    'archive-search.spec.js',
    'archive-refresh.spec.js',
    'terminal.spec.js',
    'terminal-toggle.spec.js',
    'terminal-clear.spec.js',
    'terminal-copy.spec.js',
    'terminal-toolbar.spec.js',
    'search-modal-diagnostic.spec.js',
  ],
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
