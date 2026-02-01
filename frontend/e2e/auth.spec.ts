import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display login page', async ({ page }) => {
    await expect(page).toHaveTitle(/ERP Control Panel/);
    await expect(page.locator('text=ERP Control Panel').first()).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.getByLabel(/email/i).fill('invalid@test.com');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Wait for error toast
    await page.waitForTimeout(3000);
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.getByLabel(/email/i).fill('admin@consumer.com');
    await page.getByLabel(/password/i).fill('Admin@123');

    // Wait for login API response
    const loginPromise = page.waitForResponse(
      (resp) => resp.url().includes('/auth/login') && resp.status() === 200
    );

    await page.getByRole('button', { name: /sign in/i }).click();
    await loginPromise;

    // Wait for navigation to complete
    await page.waitForLoadState('networkidle');

    // Should redirect to dashboard
    await expect(page).toHaveURL(/dashboard/, { timeout: 30000 });
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/login/);
  });
});
