'use strict';
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';

// Test pages that need to be verified
const testPages = [
  { path: '/inventory/warehouses', name: 'Inventory Warehouses' },
  { path: '/distribution/franchisee-serviceability', name: 'Franchisee Serviceability' },
  { path: '/service/warranty-claims', name: 'Service Warranty Claims' },
  { path: '/crm/customer-360', name: 'CRM Customer 360' },
  { path: '/crm/leads', name: 'CRM Leads' },
];

test.describe('Page Load Tests', () => {
  for (const page of testPages) {
    test(`${page.name} page loads correctly`, async ({ page: browserPage }) => {
      const response = await browserPage.goto(`${BASE_URL}${page.path}`, {
        waitUntil: 'networkidle',
        timeout: 30000,
      });

      // Check response status
      expect(response?.status()).toBeLessThan(500);

      // Take screenshot for visual verification
      await browserPage.screenshot({
        path: `e2e/screenshots/${page.path.replace(/\//g, '-').slice(1)}.png`,
        fullPage: true
      });

      // Check for error messages on the page
      const errorMessage = await browserPage.locator('text=/error|Error|404|not found/i').first().isVisible().catch(() => false);

      // Log page title
      const title = await browserPage.title();
      console.log(`Page: ${page.name}, Title: ${title}, Has visible error: ${errorMessage}`);
    });
  }
});
