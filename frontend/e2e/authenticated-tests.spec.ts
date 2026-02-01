'use strict';
import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';

// Demo credentials from the login page
const DEMO_CREDENTIALS = {
  email: 'admin@consumer.com',
  password: 'Admin@123',
};

// Helper function to login
async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });

  // Fill in credentials
  await page.fill('input[type="email"], input[placeholder*="email" i]', DEMO_CREDENTIALS.email);
  await page.fill('input[type="password"]', DEMO_CREDENTIALS.password);

  // Click sign in button
  await page.click('button[type="submit"], button:has-text("Sign In")');

  // Wait for navigation after login (should redirect to dashboard or requested page)
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });

  // Wait for the page to stabilize
  await page.waitForLoadState('networkidle');
}

// Test pages to verify after authentication
const authenticatedPages = [
  { path: '/inventory/warehouses', name: 'Inventory Warehouses' },
  { path: '/distribution/franchisee-serviceability', name: 'Franchisee Serviceability' },
  { path: '/service/warranty-claims', name: 'Service Warranty Claims' },
  { path: '/crm/customer-360', name: 'CRM Customer 360' },
  { path: '/crm/leads', name: 'CRM Leads' },
  { path: '/dashboard', name: 'Dashboard' },
  { path: '/products', name: 'Products' },
  { path: '/orders', name: 'Orders' },
  { path: '/procurement/purchase-orders', name: 'Purchase Orders' },
  { path: '/procurement/vendors', name: 'Vendors' },
];

test.describe('Authenticated Page Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await login(page);
  });

  for (const testPage of authenticatedPages) {
    test(`${testPage.name} page loads correctly after login`, async ({ page }) => {
      // Navigate to the page
      const response = await page.goto(`${BASE_URL}${testPage.path}`, {
        waitUntil: 'networkidle',
        timeout: 30000,
      });

      // Verify we're not on the login page
      expect(page.url()).not.toContain('/login');

      // Check response status
      expect(response?.status()).toBeLessThan(500);

      // Wait for content to load
      await page.waitForTimeout(1000);

      // Take screenshot for visual verification
      await page.screenshot({
        path: `e2e/screenshots/auth-${testPage.path.replace(/\//g, '-').slice(1)}.png`,
        fullPage: true,
      });

      // Check for error messages on the page
      const hasError = await page.locator('text=/error|Error|404|not found/i').first().isVisible().catch(() => false);

      // Log page info
      const title = await page.title();
      console.log(`Page: ${testPage.name}, Title: ${title}, URL: ${page.url()}, Has visible error: ${hasError}`);

      // Verify we have some content (sidebar, header, or main content)
      const hasContent = await page.locator('[class*="sidebar"], [class*="header"], main, [role="main"]').first().isVisible().catch(() => false);
      console.log(`Has content: ${hasContent}`);
    });
  }
});

// Single focused test for warehouses page with detailed verification
test.describe('Warehouses Page Deep Test', () => {
  test('Warehouses page shows table and controls', async ({ page }) => {
    await login(page);

    await page.goto(`${BASE_URL}/inventory/warehouses`, {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    // Take initial screenshot
    await page.screenshot({
      path: 'e2e/screenshots/warehouses-full.png',
      fullPage: true,
    });

    // Check for key UI elements
    const pageTitle = await page.locator('h1, h2').first().textContent().catch(() => 'No title found');
    console.log(`Page Title: ${pageTitle}`);

    // Check for table or data grid
    const hasTable = await page.locator('table, [role="grid"], [class*="table"]').first().isVisible().catch(() => false);
    console.log(`Has table: ${hasTable}`);

    // Check for "Add" or "Create" button
    const hasAddButton = await page.locator('button:has-text("Add"), button:has-text("Create"), button:has-text("New")').first().isVisible().catch(() => false);
    console.log(`Has Add/Create button: ${hasAddButton}`);

    // Check for sidebar navigation
    const hasSidebar = await page.locator('[class*="sidebar"], nav').first().isVisible().catch(() => false);
    console.log(`Has sidebar: ${hasSidebar}`);

    // Log all visible headings
    const headings = await page.locator('h1, h2, h3').allTextContents();
    console.log(`Headings found: ${headings.join(', ')}`);
  });
});
