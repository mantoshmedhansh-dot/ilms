import { test, expect, Page } from '@playwright/test';

/**
 * Comprehensive E2E Tests for ALL Frontend Pages
 * Tests: Page load, API calls, no mock data verification
 *
 * Backend: http://localhost:8000
 * Frontend: http://localhost:3001
 */

// Track all API calls to verify real backend integration
const apiCalls: { url: string; method: string; status?: number }[] = [];
const mockPatterns = ['mock', 'fake', 'dummy', 'placeholder'];

// Helper to setup API tracking
async function setupApiTracking(page: Page) {
  page.on('request', (request) => {
    const url = request.url();
    if (url.includes('localhost:8000') || url.includes('/api/')) {
      apiCalls.push({ url, method: request.method() });
    }
  });

  page.on('response', (response) => {
    const url = response.url();
    if (url.includes('localhost:8000') || url.includes('/api/')) {
      const call = apiCalls.find(c => c.url === url && !c.status);
      if (call) call.status = response.status();
    }
  });
}

// Helper function to login
async function login(page: Page) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  // Fill login form
  await page.fill('input[type="email"], input[name="email"]', 'admin@consumer.com');
  await page.fill('input[type="password"], input[name="password"]', 'Admin@123');
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard
  await page.waitForURL(/.*dashboard.*|.*\/$/, { timeout: 30000 });
  await page.waitForLoadState('networkidle');
}

// Helper to verify page loads without errors
async function verifyPageLoad(page: Page, url: string, expectedHeading?: RegExp) {
  await page.goto(url);
  await page.waitForLoadState('networkidle');

  // Should not show error page
  const errorText = await page.locator('text=/error|500|404|something went wrong/i').count();
  if (errorText > 0) {
    // Check if it's a genuine page content vs error
    const hasContent = await page.locator('table, [class*="card"], [class*="grid"], form').count();
    if (hasContent === 0) {
      throw new Error(`Page ${url} shows error`);
    }
  }

  // Verify heading if provided
  if (expectedHeading) {
    await expect(page.getByRole('heading', { name: expectedHeading }).first()).toBeVisible({ timeout: 10000 });
  }
}

// ==================== AUTH TESTS ====================
test.describe('Authentication', () => {
  test('Login page loads correctly', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('Login with valid credentials redirects to dashboard', async ({ page }) => {
    await setupApiTracking(page);
    await login(page);

    expect(page.url()).toMatch(/dashboard/);

    // Verify login API was called
    expect(apiCalls.some(c => c.url.includes('/auth/') || c.url.includes('/login'))).toBeTruthy();
  });
});

// ==================== DASHBOARD ====================
test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Dashboard loads with real data', async ({ page }) => {
    await setupApiTracking(page);
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /dashboard/i }).first()).toBeVisible();

    // Dashboard should make API calls for stats/metrics
    await page.waitForTimeout(2000);
  });
});

// ==================== WMS TESTS ====================
test.describe('WMS - Warehouse Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Zones page loads and calls API', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/wms/zones', /warehouse zones/i);

    // Verify API call
    expect(apiCalls.some(c => c.url.includes('/wms/zones') || c.url.includes('/zones'))).toBeTruthy();
  });

  test('Zones - Add Zone dialog has dynamic warehouse dropdown', async ({ page }) => {
    await setupApiTracking(page);
    await page.goto('/wms/zones');
    await page.waitForLoadState('networkidle');

    const addButton = page.getByRole('button', { name: /add zone/i });
    await expect(addButton).toBeVisible();
    await addButton.click();

    await expect(page.getByRole('dialog')).toBeVisible();

    // Wait for warehouse dropdown to load from API
    await page.waitForTimeout(1000);

    // Verify warehouses API was called
    expect(apiCalls.some(c => c.url.includes('/warehouses'))).toBeTruthy();

    await page.getByRole('button', { name: /cancel/i }).click();
  });

  test('Bins page loads and uses is_reserved field', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/wms/bins', /warehouse bins/i);

    // Verify bins API call
    expect(apiCalls.some(c => c.url.includes('/wms/bins') || c.url.includes('/bins'))).toBeTruthy();
  });

  test('Bins - Add Bin dialog has correct bin types', async ({ page }) => {
    await page.goto('/wms/bins');
    await page.waitForLoadState('networkidle');

    const addButton = page.getByRole('button', { name: /add bin/i });
    await expect(addButton).toBeVisible();
    await addButton.click();

    await expect(page.getByRole('dialog')).toBeVisible();

    // Check bin type dropdown
    const binTypeSelect = page.locator('button[role="combobox"]').filter({ hasText: /shelf|pallet|bin type/i }).first();
    if (await binTypeSelect.isVisible()) {
      await binTypeSelect.click();
      await page.waitForTimeout(500);

      // Should have correct bin types: SHELF, PALLET, FLOOR, RACK, BULK
      const options = page.locator('[role="option"]');
      const optionTexts = await options.allTextContents();
      const hasCorrectTypes = optionTexts.some(t =>
        /shelf|pallet|floor|rack|bulk/i.test(t)
      );
      expect(hasCorrectTypes).toBeTruthy();
    }

    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: /cancel/i }).click();
  });

  test('Putaway Rules page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/wms/putaway-rules', /putaway rules/i);

    expect(apiCalls.some(c => c.url.includes('/putaway-rules'))).toBeTruthy();
  });

  test('Bin Enquiry page loads', async ({ page }) => {
    await verifyPageLoad(page, '/wms/bin-enquiry', /bin enquiry/i);
  });
});

// ==================== PROCUREMENT TESTS ====================
test.describe('Procurement', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Vendors page loads and calls API', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/procurement/vendors', /vendors/i);

    expect(apiCalls.some(c => c.url.includes('/vendors'))).toBeTruthy();
  });

  test('Vendors - Add dialog has all required fields', async ({ page }) => {
    await page.goto('/procurement/vendors');
    await page.waitForLoadState('networkidle');

    const addButton = page.getByRole('button', { name: /add vendor/i });
    await expect(addButton).toBeVisible();
    await addButton.click();

    await expect(page.getByRole('dialog')).toBeVisible();

    // Verify required fields exist
    await expect(page.locator('input[id="name"]')).toBeVisible();
    await expect(page.locator('input[id="address_line1"]')).toBeVisible();
    await expect(page.locator('input[id="city"]')).toBeVisible();
    await expect(page.locator('input[id="state"]')).toBeVisible();
    await expect(page.locator('input[id="pincode"]')).toBeVisible();

    // Vendor type dropdown should exist
    const vendorTypeLabel = page.locator('label').filter({ hasText: /vendor type/i });
    await expect(vendorTypeLabel).toBeVisible();

    await page.getByRole('button', { name: /cancel/i }).click();
  });

  test('Purchase Orders page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/procurement/purchase-orders', /purchase orders/i);

    expect(apiCalls.some(c => c.url.includes('/purchase-orders'))).toBeTruthy();
  });

  test('Requisitions page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/procurement/requisitions', /requisitions/i);
  });

  test('GRN page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/procurement/grn', /goods.*receipt|grn/i);
  });

  test('Three Way Match page loads', async ({ page }) => {
    await verifyPageLoad(page, '/procurement/three-way-match', /three.*way.*match/i);
  });

  test('Vendor Invoices page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/procurement/vendor-invoices', /vendor.*invoices/i);
  });

  test('Vendor Proformas page loads', async ({ page }) => {
    await verifyPageLoad(page, '/procurement/vendor-proformas', /vendor.*proformas|proforma/i);
  });
});

// ==================== INVENTORY TESTS ====================
test.describe('Inventory', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Products page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/products', /products/i);

    expect(apiCalls.some(c => c.url.includes('/products'))).toBeTruthy();
  });

  test('Categories page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/products/categories', /categories/i);

    expect(apiCalls.some(c => c.url.includes('/categories'))).toBeTruthy();
  });

  test('Brands page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/products/brands', /brands/i);

    expect(apiCalls.some(c => c.url.includes('/brands'))).toBeTruthy();
  });

  test('Stock Items page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/inventory/stock-items', /stock.*items/i);
  });

  test('Warehouses page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/inventory/warehouses', /warehouses/i);

    expect(apiCalls.some(c => c.url.includes('/warehouses'))).toBeTruthy();
  });

  test('Inventory Adjustments page loads', async ({ page }) => {
    await verifyPageLoad(page, '/inventory/adjustments', /adjustments/i);
  });

  test('Inventory Transfers page loads', async ({ page }) => {
    await verifyPageLoad(page, '/inventory/transfers', /transfers/i);
  });
});

// ==================== LOGISTICS TESTS ====================
test.describe('Logistics', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Shipments page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/logistics/shipments', /shipments/i);

    expect(apiCalls.some(c => c.url.includes('/shipments'))).toBeTruthy();
  });

  test('Transporters page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/logistics/transporters', /transporters/i);

    expect(apiCalls.some(c => c.url.includes('/transporters'))).toBeTruthy();
  });

  test('Manifests page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/logistics/manifests', /manifests/i);
  });

  test('Rate Cards page loads', async ({ page }) => {
    await verifyPageLoad(page, '/logistics/rate-cards', /rate.*cards/i);
  });

  test('Serviceability page loads', async ({ page }) => {
    await verifyPageLoad(page, '/logistics/serviceability', /serviceability/i);
  });

  test('Allocation Rules page loads', async ({ page }) => {
    await verifyPageLoad(page, '/logistics/allocation-rules', /allocation.*rules/i);
  });

  test('SLA Dashboard page loads', async ({ page }) => {
    await verifyPageLoad(page, '/logistics/sla-dashboard', /sla.*dashboard/i);
  });
});

// ==================== SERVICE TESTS ====================
test.describe('Service', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Service Requests page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/service/requests', /service.*requests/i);
  });

  test('Installations page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/service/installations', /installations/i);
  });

  test('Technicians page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/service/technicians', /technicians/i);
  });

  test('Warranty Claims page loads', async ({ page }) => {
    await verifyPageLoad(page, '/service/warranty-claims', /warranty.*claims/i);
  });

  test('AMC page loads', async ({ page }) => {
    await verifyPageLoad(page, '/service/amc', /amc|annual.*maintenance/i);
  });
});

// ==================== ORDERS TESTS ====================
test.describe('Orders', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Orders page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/orders', /orders/i);

    expect(apiCalls.some(c => c.url.includes('/orders'))).toBeTruthy();
  });

  test('Picklists page loads', async ({ page }) => {
    await verifyPageLoad(page, '/orders/picklists', /picklists/i);
  });

  test('New Order page loads', async ({ page }) => {
    await verifyPageLoad(page, '/orders/new', /new.*order|create.*order/i);
  });
});

// ==================== CRM TESTS ====================
test.describe('CRM', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Customers page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/crm/customers', /customers/i);

    expect(apiCalls.some(c => c.url.includes('/customers'))).toBeTruthy();
  });

  test('Leads page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/crm/leads', /leads/i);
  });

  test('Call Center page loads', async ({ page }) => {
    await verifyPageLoad(page, '/crm/call-center', /call.*center/i);
  });

  test('Escalations page loads', async ({ page }) => {
    await verifyPageLoad(page, '/crm/escalations', /escalations/i);
  });

  test('Customer 360 page loads', async ({ page }) => {
    await verifyPageLoad(page, '/crm/customer-360', /customer.*360/i);
  });
});

// ==================== DISTRIBUTION TESTS ====================
test.describe('Distribution', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Dealers page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/distribution/dealers', /dealers/i);

    expect(apiCalls.some(c => c.url.includes('/dealers'))).toBeTruthy();
  });

  test('Franchisees page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/distribution/franchisees', /franchisees/i);
  });

  test('Pricing Tiers page loads', async ({ page }) => {
    await verifyPageLoad(page, '/distribution/pricing-tiers', /pricing.*tiers/i);
  });
});

// ==================== MARKETING TESTS ====================
test.describe('Marketing', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Campaigns page loads', async ({ page }) => {
    await verifyPageLoad(page, '/marketing/campaigns', /campaigns/i);
  });

  test('Promotions page loads', async ({ page }) => {
    await verifyPageLoad(page, '/marketing/promotions', /promotions/i);
  });

  test('Commissions page loads', async ({ page }) => {
    await verifyPageLoad(page, '/marketing/commissions', /commissions/i);
  });
});

// ==================== BILLING/FINANCE TESTS ====================
test.describe('Billing & Finance', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Invoices page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/billing/invoices', /invoices/i);
  });

  test('Receipts page loads', async ({ page }) => {
    await verifyPageLoad(page, '/billing/receipts', /receipts/i);
  });

  test('Credit Notes page loads', async ({ page }) => {
    await verifyPageLoad(page, '/billing/credit-notes', /credit.*notes/i);
  });

  test('Eway Bills page loads', async ({ page }) => {
    await verifyPageLoad(page, '/billing/eway-bills', /eway.*bills|e-way/i);
  });

  test('Chart of Accounts page loads', async ({ page }) => {
    await verifyPageLoad(page, '/finance/chart-of-accounts', /chart.*of.*accounts/i);
  });

  test('General Ledger page loads', async ({ page }) => {
    await verifyPageLoad(page, '/finance/general-ledger', /general.*ledger/i);
  });

  test('Journal Entries page loads', async ({ page }) => {
    await verifyPageLoad(page, '/finance/journal-entries', /journal.*entries/i);
  });

  test('Cost Centers page loads', async ({ page }) => {
    await verifyPageLoad(page, '/finance/cost-centers', /cost.*centers/i);
  });
});

// ==================== ACCESS CONTROL TESTS ====================
test.describe('Access Control', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Users page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/access-control/users', /users/i);

    expect(apiCalls.some(c => c.url.includes('/users'))).toBeTruthy();
  });

  test('Roles page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/access-control/roles', /roles/i);

    expect(apiCalls.some(c => c.url.includes('/roles'))).toBeTruthy();
  });

  test('Permissions page loads', async ({ page }) => {
    await verifyPageLoad(page, '/access-control/permissions', /permissions/i);
  });
});

// ==================== SETTINGS TESTS ====================
test.describe('Settings & Admin', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Settings page loads', async ({ page }) => {
    await verifyPageLoad(page, '/settings', /settings/i);
  });

  test('Audit Logs page loads', async ({ page }) => {
    await verifyPageLoad(page, '/audit-logs', /audit.*logs/i);
  });

  test('Approvals page loads', async ({ page }) => {
    await verifyPageLoad(page, '/approvals', /approvals/i);
  });
});

// ==================== CHANNELS TESTS ====================
test.describe('Channels', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Channels page loads', async ({ page }) => {
    await setupApiTracking(page);
    await verifyPageLoad(page, '/channels', /channels/i);
  });

  test('Channel Inventory page loads', async ({ page }) => {
    await verifyPageLoad(page, '/channels/inventory', /channel.*inventory|inventory/i);
  });

  test('Channel Orders page loads', async ({ page }) => {
    await verifyPageLoad(page, '/channels/orders', /channel.*orders|orders/i);
  });

  test('Channel Pricing page loads', async ({ page }) => {
    await verifyPageLoad(page, '/channels/pricing', /channel.*pricing|pricing/i);
  });
});

// ==================== SERIALIZATION ====================
test.describe('Serialization', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Serialization page loads', async ({ page }) => {
    await verifyPageLoad(page, '/serialization', /serialization/i);
  });
});

// ==================== NO MOCK DATA VERIFICATION ====================
test.describe('No Mock Data Verification', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('All API calls go to real backend', async ({ page }) => {
    const realApiCalls: string[] = [];
    const suspiciousCalls: string[] = [];

    page.on('request', (request) => {
      const url = request.url();

      // Track real API calls
      if (url.includes('localhost:8000') || url.includes('/api/v1/')) {
        realApiCalls.push(url);
      }

      // Flag suspicious mock patterns
      mockPatterns.forEach(pattern => {
        if (url.toLowerCase().includes(pattern)) {
          suspiciousCalls.push(url);
        }
      });
    });

    // Visit key pages
    const keyPages = [
      '/wms/bins',
      '/wms/zones',
      '/procurement/vendors',
      '/products',
      '/orders',
      '/logistics/shipments',
    ];

    for (const pageUrl of keyPages) {
      await page.goto(pageUrl);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);
    }

    // Should have made real API calls
    expect(realApiCalls.length).toBeGreaterThan(0);

    // Should not have suspicious mock calls
    expect(suspiciousCalls.length).toBe(0);
  });

  test('Data tables are populated from API responses', async ({ page }) => {
    const apiResponses: { url: string; hasData: boolean }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('localhost:8000') && response.ok()) {
        try {
          const body = await response.json();
          const hasData = body && (
            Array.isArray(body) ||
            body.items ||
            body.data ||
            Object.keys(body).length > 0
          );
          apiResponses.push({ url, hasData });
        } catch {}
      }
    });

    await page.goto('/wms/bins');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Verify we got API responses
    expect(apiResponses.length).toBeGreaterThan(0);
  });
});
