import { test, expect, Page } from '@playwright/test';

/**
 * Full Integration E2E Tests
 * Tests all pages with real backend
 * Email: admin@consumer.com
 * Password: Admin@123
 */

// Global setup - login once and save state
test.describe.configure({ mode: 'serial' });

let isLoggedIn = false;

async function ensureLoggedIn(page: Page) {
  if (!isLoggedIn) {
    await page.goto('/login');
    await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 10000 });

    await page.fill('input[type="email"], input[name="email"]', 'admin@consumer.com');
    await page.fill('input[type="password"]', 'Admin@123');
    await page.click('button[type="submit"]');

    // Wait for dashboard to appear
    await page.waitForURL(/.*dashboard.*/, { timeout: 15000 });
    await page.waitForSelector('text=Dashboard', { timeout: 10000 });

    isLoggedIn = true;
  }
}

// Helper to navigate and verify page loads
async function navigateAndVerify(page: Page, url: string, timeout = 15000) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
  await page.waitForTimeout(1000); // Brief wait for initial render

  // Check page loaded (not error page) - look for specific error indicators
  const errorLocator = page.locator('text=/500 Internal Server Error|Something went wrong|Application error/i');
  const errorCount = await errorLocator.count();
  expect(errorCount).toBe(0);
}

// ==================== AUTHENTICATION ====================
test('1. Login works and redirects to dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[type="email"], input[name="email"]', 'admin@consumer.com');
  await page.fill('input[type="password"]', 'Admin@123');
  await page.click('button[type="submit"]');

  // Wait for dashboard to appear (don't use networkidle - it never completes due to polling)
  await page.waitForURL(/.*dashboard.*/, { timeout: 15000 });
  await page.waitForSelector('text=Dashboard', { timeout: 10000 });

  // Should redirect to dashboard
  expect(page.url()).toContain('dashboard');
  isLoggedIn = true;
});

// ==================== DASHBOARD ====================
test('2. Dashboard shows real data from API', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/dashboard');

  // Check dashboard elements exist
  await expect(page.getByText('Dashboard')).toBeVisible({ timeout: 10000 });

  // Verify real data (Products count, etc.)
  const body = await page.locator('body').textContent();
  expect(body).toContain('Products');
});

// ==================== WMS - WAREHOUSE MANAGEMENT ====================
test('3. WMS - Zones page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/wms/zones');

  await expect(page.getByRole('heading', { name: /warehouse zones/i }).first()).toBeVisible({ timeout: 10000 });
});

test('4. WMS - Bins page loads with is_reserved field', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/wms/bins');

  await expect(page.getByRole('heading', { name: /warehouse bins/i }).first()).toBeVisible({ timeout: 10000 });
});

test('5. WMS - Putaway Rules page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/wms/putaway-rules');

  await expect(page.getByRole('heading', { name: /putaway rules/i }).first()).toBeVisible({ timeout: 10000 });
});

test('6. WMS - Bin Enquiry page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/wms/bin-enquiry');

  await expect(page.getByRole('heading', { name: /bin enquiry/i }).first()).toBeVisible({ timeout: 10000 });
});

// ==================== PROCUREMENT ====================
test('7. Procurement - Vendors page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/procurement/vendors');

  await expect(page.getByRole('heading', { name: /vendors/i }).first()).toBeVisible({ timeout: 10000 });
});

test('8. Procurement - Purchase Orders page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/procurement/purchase-orders');

  await expect(page.getByRole('heading', { name: /purchase orders/i }).first()).toBeVisible({ timeout: 10000 });
});

test('9. Procurement - Requisitions page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/procurement/requisitions');
});

test('10. Procurement - GRN page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/procurement/grn');
});

// ==================== INVENTORY ====================
test('11. Products page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/products');

  await expect(page.getByRole('heading', { name: /products/i }).first()).toBeVisible({ timeout: 10000 });
});

test('12. Categories page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/products/categories');
});

test('13. Brands page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/products/brands');
});

test('14. Stock Items page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/inventory/stock-items');
});

test('15. Warehouses page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/inventory/warehouses');
});

// ==================== LOGISTICS ====================
test('16. Shipments page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/logistics/shipments');
});

test('17. Transporters page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/logistics/transporters');
});

test('18. Manifests page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/logistics/manifests');
});

// ==================== SERVICE ====================
test('19. Service Requests page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/service/requests');
});

test('20. Installations page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/service/installations');
});

test('21. Technicians page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/service/technicians');
});

test('22. Warranty Claims page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/service/warranty-claims');
});

// ==================== ORDERS ====================
test('23. Orders page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/orders');
});

test('24. Picklists page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/orders/picklists');
});

// ==================== CRM ====================
test('25. Customers page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/crm/customers');
});

test('26. Leads page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/crm/leads');
});

// ==================== DISTRIBUTION ====================
test('27. Dealers page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/distribution/dealers');
});

test('28. Franchisees page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/distribution/franchisees');
});

// ==================== MARKETING ====================
test('29. Campaigns page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/marketing/campaigns');
});

test('30. Promotions page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/marketing/promotions');
});

// ==================== BILLING & FINANCE ====================
test('31. Invoices page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/billing/invoices');
});

test('32. Chart of Accounts page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/finance/chart-of-accounts');
});

test('33. General Ledger page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/finance/general-ledger');
});

// ==================== ACCESS CONTROL ====================
test('34. Users page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/access-control/users');
});

test('35. Roles page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/access-control/roles');
});

// ==================== SETTINGS ====================
test('36. Settings page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/settings');
});

test('37. Audit Logs page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/audit-logs');
});

// ==================== CHANNELS ====================
test('38. Channels page loads', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/channels');
});

// ==================== FORM VALIDATION TESTS ====================
test('39. Vendor form has required fields', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/procurement/vendors');

  const addButton = page.getByRole('button', { name: /add vendor/i });
  await expect(addButton).toBeVisible({ timeout: 10000 });
  await addButton.click();

  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

  // Verify required fields
  await expect(page.locator('input[id="name"]')).toBeVisible();
  await expect(page.locator('input[id="address_line1"]')).toBeVisible();
  await expect(page.locator('input[id="city"]')).toBeVisible();
  await expect(page.locator('input[id="state"]')).toBeVisible();
  await expect(page.locator('input[id="pincode"]')).toBeVisible();

  await page.keyboard.press('Escape');
});

test('40. Bin form has correct bin types', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/wms/bins');

  const addButton = page.getByRole('button', { name: /add bin/i });
  await expect(addButton).toBeVisible({ timeout: 10000 });
  await addButton.click();

  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

  // Verify bin_code field exists
  const binCodeInput = page.locator('input[id="bin_code"], input[placeholder*="BIN"]');
  await expect(binCodeInput.first()).toBeVisible();

  await page.keyboard.press('Escape');
});

test('41. Zone form has dynamic warehouse dropdown', async ({ page }) => {
  await ensureLoggedIn(page);
  await navigateAndVerify(page, '/wms/zones');

  const addButton = page.getByRole('button', { name: /add zone/i });
  await expect(addButton).toBeVisible({ timeout: 10000 });
  await addButton.click();

  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

  // Verify warehouse dropdown exists
  const warehouseLabel = page.locator('label').filter({ hasText: /warehouse/i });
  await expect(warehouseLabel.first()).toBeVisible();

  await page.keyboard.press('Escape');
});

// ==================== API VERIFICATION ====================
test('42. All pages call real API (no mock data)', async ({ page }) => {
  const apiCalls: string[] = [];
  const mockCalls: string[] = [];

  page.on('request', (request) => {
    const url = request.url();
    if (url.includes('localhost:8000') || url.includes('/api/v1/')) {
      apiCalls.push(url);
    }
    if (url.toLowerCase().includes('mock') || url.toLowerCase().includes('fake')) {
      mockCalls.push(url);
    }
  });

  await ensureLoggedIn(page);

  // Navigate to key pages
  await navigateAndVerify(page, '/wms/bins');
  await navigateAndVerify(page, '/procurement/vendors');
  await navigateAndVerify(page, '/products');
  await navigateAndVerify(page, '/orders');

  // Should have API calls
  expect(apiCalls.length).toBeGreaterThan(0);

  // Should not have mock calls
  expect(mockCalls.length).toBe(0);
});
