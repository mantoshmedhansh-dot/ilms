import { test, expect } from '@playwright/test';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';

test.describe('WMS & OMS Pages', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"], input[type="email"]', 'admin@consumer.com');
    await page.fill('input[name="password"], input[type="password"]', 'Admin@123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard.*|.*\/$/);
    await page.waitForTimeout(1000); // Wait for auth to settle
  });

  test('Warehouse Zones page loads and has correct elements', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory/zones`);
    await page.waitForLoadState('networkidle');

    // Check page header (h1)
    await expect(page.getByRole('heading', { name: /warehouse zones/i })).toBeVisible();

    // Check Add Zone button exists
    await expect(page.getByRole('button', { name: /add zone/i })).toBeVisible();
  });

  test('Warehouse Bins page loads and has correct elements', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory/bins`);
    await page.waitForLoadState('networkidle');

    // Check page header (h1)
    await expect(page.getByRole('heading', { name: /warehouse bins/i })).toBeVisible();

    // Check Add Bin button exists
    await expect(page.getByRole('button', { name: /add bin/i })).toBeVisible();
  });

  test('Shipments page loads and displays shipment list', async ({ page }) => {
    await page.goto(`${BASE_URL}/logistics/shipments`);
    await page.waitForLoadState('networkidle');

    // Check page header (h1)
    await expect(page.getByRole('heading', { name: /shipments/i })).toBeVisible();

    // Check that data table or loading state is visible
    const tableOrLoader = page.locator('[class*="data-table"], table, [class*="skeleton"], [class*="loading"]');
    await expect(tableOrLoader.first()).toBeVisible();
  });

  test('Transporters page loads and Add button works', async ({ page }) => {
    await page.goto(`${BASE_URL}/logistics/transporters`);
    await page.waitForLoadState('networkidle');

    // Check page header (h1) - use heading role to be specific
    await expect(page.getByRole('heading', { name: /transporters/i })).toBeVisible();

    // Check Add Transporter button exists
    const addButton = page.getByRole('button', { name: /add transporter/i });
    await expect(addButton).toBeVisible();

    // Click the Add button
    await addButton.click();

    // Check that the dialog opens
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.locator('text=Add New Transporter')).toBeVisible();

    // Check required form fields
    await expect(page.locator('input[placeholder="BlueDart"]')).toBeVisible();
    await expect(page.locator('input[placeholder="BD"]')).toBeVisible();

    // Close dialog
    await page.getByRole('button', { name: /cancel/i }).click();
  });

  test('Manifests page loads and Create button works', async ({ page }) => {
    await page.goto(`${BASE_URL}/logistics/manifests`);
    await page.waitForLoadState('networkidle');

    // Check page header (h1)
    await expect(page.getByRole('heading', { name: /manifests/i })).toBeVisible();

    // Check Create Manifest button exists
    const createButton = page.getByRole('button', { name: /create manifest/i });
    await expect(createButton).toBeVisible();

    // Click the Create button
    await createButton.click();

    // Check that the dialog opens
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.locator('text=Create New Manifest')).toBeVisible();

    // Close dialog
    await page.getByRole('button', { name: /cancel/i }).click();
  });

  test('Zones page - Add Zone dialog works', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory/zones`);
    await page.waitForLoadState('networkidle');

    // Click Add Zone button
    await page.getByRole('button', { name: /add zone/i }).click();

    // Check dialog opens
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.locator('text=Create New Zone')).toBeVisible();

    // Close dialog
    await page.getByRole('button', { name: /cancel/i }).click();
  });

  test('Bins page - Add Bin dialog works', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory/bins`);
    await page.waitForLoadState('networkidle');

    // Click Add Bin button
    await page.getByRole('button', { name: /add bin/i }).click();

    // Check dialog opens
    await expect(page.getByRole('dialog')).toBeVisible();

    // Close dialog
    await page.getByRole('button', { name: /cancel/i }).click();
  });

  test('Shipments page - has filter controls', async ({ page }) => {
    await page.goto(`${BASE_URL}/logistics/shipments`);
    await page.waitForLoadState('networkidle');

    // Check page header
    await expect(page.getByRole('heading', { name: /shipments/i })).toBeVisible();

    // Check that select dropdown exists (for status filter)
    const selectTrigger = page.locator('button[role="combobox"], [data-state]').first();
    await expect(selectTrigger).toBeVisible();
  });
});
