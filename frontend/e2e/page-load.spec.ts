import { test, expect } from '@playwright/test';

/**
 * Simple page load tests - verify pages compile and render
 * These tests don't require authentication
 */

test.describe('Page Load Tests', () => {
  test('Login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveTitle(/.*Login.*|.*Consumer.*|.*Aquapurite.*/i);
    // Should have email and password fields
    await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('Home page redirects to login', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Should redirect to login for unauthenticated users
    expect(page.url()).toMatch(/login|signin/i);
  });
});
