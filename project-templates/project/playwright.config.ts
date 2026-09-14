import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: '.ai-dlc/local/design/test-results',
  use: { baseURL: process.env.BASE_URL, viewport: { width: 1280, height: 800 } },
});
