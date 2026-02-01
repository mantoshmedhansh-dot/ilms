import { test, expect } from '@playwright/test';

// Setup: Login before each test
test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('admin@consumer.com');
    await page.getByLabel(/password/i).fill('Admin@123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 30000 });
  });

  test('should display dashboard page', async ({ page }) => {
    // Check dashboard loaded
    await expect(page.locator('main')).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    // Check sidebar is visible
    await expect(page.locator('aside')).toBeVisible();
  });

  test('should display header', async ({ page }) => {
    // Check header elements
    await expect(page.locator('header')).toBeVisible();
  });
});
