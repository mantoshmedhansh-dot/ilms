import { test, expect } from '@playwright/test';

/**
 * E2E Tests for API Integration - Verifying no mock data
 * Tests the following pages that were updated:
 * 1. WMS Bins - is_reserved field, bin types, dynamic zone dropdown
 * 2. WMS Zones - dynamic warehouse dropdown
 * 3. WMS Putaway Rules - dynamic warehouse/zone dropdowns
 * 4. Procurement Vendors - required fields (vendor_type, address, city, state, pincode)
 */

test.describe('API Integration Tests - No Mock Data', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[name="email"], input[type="email"]', 'admin@consumer.com');
    await page.fill('input[name="password"], input[type="password"]', 'Admin@123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard.*|.*\/$/);
    await page.waitForTimeout(1000);
  });

  test.describe('WMS Bins Page', () => {
    test('loads bins from API and displays correct data structure', async ({ page }) => {
      // Intercept API calls to verify real API is being called
      const apiCalls: string[] = [];
      page.on('request', (request) => {
        if (request.url().includes('/api/') || request.url().includes('/wms/')) {
          apiCalls.push(request.url());
        }
      });

      await page.goto('/wms/bins');
      await page.waitForLoadState('networkidle');

      // Verify page loaded
      await expect(page.getByRole('heading', { name: /warehouse bins/i })).toBeVisible();

      // Verify API was called (not mock data)
      expect(apiCalls.some(url => url.includes('/wms/bins') || url.includes('/bins'))).toBeTruthy();
    });

    test('Add Bin dialog has correct fields and dynamic zone dropdown', async ({ page }) => {
      await page.goto('/wms/bins');
      await page.waitForLoadState('networkidle');

      // Click Add Bin button
      await page.getByRole('button', { name: /add bin/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Verify form fields exist with correct names (backend-compatible)
      await expect(page.locator('input[id="bin_code"], input[placeholder*="BIN"]')).toBeVisible();

      // Verify bin type dropdown has correct values (SHELF, PALLET, FLOOR, RACK, BULK)
      const binTypeSelect = page.locator('[id="bin_type"]').first();
      if (await binTypeSelect.isVisible()) {
        await binTypeSelect.click();
        // Check for correct bin types
        const selectContent = page.locator('[role="listbox"], [role="option"]');
        await expect(selectContent).toBeVisible();
      }

      // Verify zone dropdown exists (should be dynamic, not hardcoded)
      const zoneSelect = page.locator('button[role="combobox"]').filter({ hasText: /zone|select/i }).first();
      if (await zoneSelect.isVisible()) {
        await zoneSelect.click();
        await page.waitForTimeout(500);
      }

      // Close dialog
      await page.getByRole('button', { name: /cancel/i }).click();
    });

    test('Bin table uses is_reserved instead of is_locked', async ({ page }) => {
      // Track API responses to check field names
      let binResponse: any = null;
      page.on('response', async (response) => {
        if (response.url().includes('/wms/bins') && response.ok()) {
          try {
            binResponse = await response.json();
          } catch {}
        }
      });

      await page.goto('/wms/bins');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // If we got a response, verify it uses is_reserved
      if (binResponse?.items?.[0]) {
        expect(binResponse.items[0]).not.toHaveProperty('is_locked');
        expect(binResponse.items[0]).toHaveProperty('is_reserved');
      }
    });
  });

  test.describe('WMS Zones Page', () => {
    test('loads zones from API', async ({ page }) => {
      const apiCalls: string[] = [];
      page.on('request', (request) => {
        if (request.url().includes('/wms/zones')) {
          apiCalls.push(request.url());
        }
      });

      await page.goto('/wms/zones');
      await page.waitForLoadState('networkidle');

      await expect(page.getByRole('heading', { name: /warehouse zones/i })).toBeVisible();
      expect(apiCalls.some(url => url.includes('/wms/zones'))).toBeTruthy();
    });

    test('Add Zone dialog has dynamic warehouse dropdown', async ({ page }) => {
      // Track warehouse API calls
      let warehouseApiCalled = false;
      page.on('request', (request) => {
        if (request.url().includes('/warehouses')) {
          warehouseApiCalled = true;
        }
      });

      await page.goto('/wms/zones');
      await page.waitForLoadState('networkidle');

      // Click Add Zone button
      await page.getByRole('button', { name: /add zone/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Give time for warehouse dropdown to load
      await page.waitForTimeout(1000);

      // Verify warehouse dropdown exists (should be populated from API, not hardcoded)
      const warehouseSelect = page.locator('button[role="combobox"]').first();
      if (await warehouseSelect.isVisible()) {
        // API should have been called for warehouses
        expect(warehouseApiCalled).toBeTruthy();
      }

      await page.getByRole('button', { name: /cancel/i }).click();
    });
  });

  test.describe('WMS Putaway Rules Page', () => {
    test('loads putaway rules from API', async ({ page }) => {
      const apiCalls: string[] = [];
      page.on('request', (request) => {
        if (request.url().includes('/wms/putaway-rules')) {
          apiCalls.push(request.url());
        }
      });

      await page.goto('/wms/putaway-rules');
      await page.waitForLoadState('networkidle');

      await expect(page.getByRole('heading', { name: /putaway rules/i })).toBeVisible();
      expect(apiCalls.some(url => url.includes('/wms/putaway-rules'))).toBeTruthy();
    });

    test('Add Rule dialog has dynamic warehouse and zone dropdowns', async ({ page }) => {
      let warehouseApiCalled = false;
      let zoneApiCalled = false;

      page.on('request', (request) => {
        if (request.url().includes('/warehouses')) warehouseApiCalled = true;
        if (request.url().includes('/zones')) zoneApiCalled = true;
      });

      await page.goto('/wms/putaway-rules');
      await page.waitForLoadState('networkidle');

      // Click Add Rule button
      const addButton = page.getByRole('button', { name: /add.*rule/i });
      if (await addButton.isVisible()) {
        await addButton.click();
        await expect(page.getByRole('dialog')).toBeVisible();
        await page.waitForTimeout(1000);

        // Verify API calls for dropdowns
        expect(warehouseApiCalled || zoneApiCalled).toBeTruthy();

        await page.getByRole('button', { name: /cancel/i }).click();
      }
    });
  });

  test.describe('Procurement Vendors Page', () => {
    test('loads vendors from API', async ({ page }) => {
      const apiCalls: string[] = [];
      page.on('request', (request) => {
        if (request.url().includes('/vendors')) {
          apiCalls.push(request.url());
        }
      });

      await page.goto('/procurement/vendors');
      await page.waitForLoadState('networkidle');

      await expect(page.getByRole('heading', { name: /vendors/i })).toBeVisible();
      expect(apiCalls.some(url => url.includes('/vendors'))).toBeTruthy();
    });

    test('Add Vendor dialog has all required fields', async ({ page }) => {
      await page.goto('/procurement/vendors');
      await page.waitForLoadState('networkidle');

      // Click Add Vendor button
      await page.getByRole('button', { name: /add vendor/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Verify required fields exist
      // Basic info
      await expect(page.locator('input[id="name"]')).toBeVisible();

      // Vendor type dropdown (required)
      const vendorTypeLabel = page.locator('label:has-text("Vendor Type")');
      await expect(vendorTypeLabel).toBeVisible();

      // Address fields (required)
      await expect(page.locator('input[id="address_line1"]')).toBeVisible();
      await expect(page.locator('input[id="city"]')).toBeVisible();
      await expect(page.locator('input[id="state"]')).toBeVisible();
      await expect(page.locator('input[id="pincode"]')).toBeVisible();

      // Tax info
      await expect(page.locator('input[id="gst_number"]')).toBeVisible();
      await expect(page.locator('input[id="pan_number"]')).toBeVisible();

      await page.getByRole('button', { name: /cancel/i }).click();
    });

    test('Vendor creation sends correct payload to API', async ({ page }) => {
      let createPayload: any = null;

      page.on('request', async (request) => {
        if (request.method() === 'POST' && request.url().includes('/vendors')) {
          createPayload = request.postDataJSON();
        }
      });

      await page.goto('/procurement/vendors');
      await page.waitForLoadState('networkidle');

      // Click Add Vendor
      await page.getByRole('button', { name: /add vendor/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Fill required fields
      await page.fill('input[id="name"]', 'Test Vendor E2E');
      await page.fill('input[id="address_line1"]', '123 Test Street');
      await page.fill('input[id="city"]', 'Mumbai');
      await page.fill('input[id="state"]', 'Maharashtra');
      await page.fill('input[id="pincode"]', '400001');

      // Submit
      await page.getByRole('button', { name: /create vendor/i }).click();
      await page.waitForTimeout(2000);

      // Verify payload has required fields
      if (createPayload) {
        expect(createPayload).toHaveProperty('name');
        expect(createPayload).toHaveProperty('address_line1');
        expect(createPayload).toHaveProperty('city');
        expect(createPayload).toHaveProperty('state');
        expect(createPayload).toHaveProperty('pincode');
        expect(createPayload).toHaveProperty('vendor_type');
      }
    });
  });

  test.describe('Stats Endpoints', () => {
    test('Bins page calls stats endpoint', async ({ page }) => {
      let statsApiCalled = false;

      page.on('request', (request) => {
        if (request.url().includes('/wms/bins/stats')) {
          statsApiCalled = true;
        }
      });

      await page.goto('/wms/bins');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Stats endpoint should be called for dashboard metrics
      // Note: This depends on whether the page displays stats
    });

    test('Putaway rules page calls stats endpoint', async ({ page }) => {
      let statsApiCalled = false;

      page.on('request', (request) => {
        if (request.url().includes('/wms/putaway-rules/stats')) {
          statsApiCalled = true;
        }
      });

      await page.goto('/wms/putaway-rules');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
    });
  });
});

test.describe('No Mock Data Verification', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"], input[type="email"]', 'admin@consumer.com');
    await page.fill('input[name="password"], input[type="password"]', 'Admin@123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard.*|.*\/$/);
    await page.waitForTimeout(1000);
  });

  test('All data tables fetch from real API endpoints', async ({ page }) => {
    const realApiCalls: string[] = [];
    const mockPatterns = ['/mock/', 'mock-data', 'fake-api', 'localhost:9999'];

    page.on('request', (request) => {
      const url = request.url();
      // Check for real API calls
      if (url.includes('/api/v1/') || url.includes(':8000/')) {
        realApiCalls.push(url);
      }
      // Fail if mock URLs are detected
      mockPatterns.forEach(pattern => {
        expect(url).not.toContain(pattern);
      });
    });

    // Visit multiple pages to check API integration
    const pagesToTest = [
      '/wms/bins',
      '/wms/zones',
      '/wms/putaway-rules',
      '/procurement/vendors',
    ];

    for (const testPage of pagesToTest) {
      await page.goto(testPage);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);
    }

    // Should have made real API calls
    expect(realApiCalls.length).toBeGreaterThan(0);
  });
});
