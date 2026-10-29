import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: false,
  use: {
    baseURL: process.env.SITE_URL || 'http://127.0.0.1:4321',
    channel: 'msedge',
    viewport: { width: 1440, height: 900 },
  },
  reporter: 'list',
});
