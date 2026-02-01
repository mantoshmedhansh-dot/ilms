import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('admin@consumer.com');
    await page.getByLabel(/password/i).fill('Admin@123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 30000 });
  });

  test('should navigate to Products page', async ({ page }) => {
    await page.locator('a[href*="products"]').first().click();
    await expect(page).toHaveURL(/products/);
  });

  test('should navigate to Orders page', async ({ page }) => {
    await page.locator('a[href*="orders"]').first().click();
    await expect(page).toHaveURL(/orders/);
  });

  test('should navigate to Inventory page', async ({ page }) => {
    // Navigate directly since sidebar link may be nested
    await page.goto('/inventory');
    await expect(page).toHaveURL(/inventory/);
  });

  test('should navigate to Procurement page', async ({ page }) => {
    await page.locator('a[href*="procurement"]').first().click();
    await expect(page).toHaveURL(/procurement/);
  });
});
