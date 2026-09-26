import { test, expect } from '@playwright/test';

if (!process.env.BASE_URL?.trim()) {
  throw new Error('Frontend smoke requires BASE_URL for a running app; start the app and set BASE_URL.');
}

test('app root has a title and screenshot evidence', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/\S/);
  await page.screenshot({ path: '.ai-dlc/local/design/smoke/smoke.png' });
});
