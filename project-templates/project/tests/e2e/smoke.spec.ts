import { test, expect } from '@playwright/test';

test('app root has a title and screenshot evidence', async ({ page }) => {
  test.skip(!process.env.BASE_URL, 'BASE_URL is unset; configure a running app for smoke.');
  await page.goto('/');
  await expect(page).toHaveTitle(/\S/);
  await page.screenshot({ path: '.ai-dlc/local/design/smoke/smoke.png' });
});
