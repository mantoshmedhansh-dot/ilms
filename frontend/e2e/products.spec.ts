import { test, expect } from '@playwright/test';

test.describe('Products Module', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('admin@consumer.com');
    await page.getByLabel(/password/i).fill('Admin@123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 30000 });
  });

  test.describe('Products List Page', () => {
    test('should display products page with header', async ({ page }) => {
      await page.goto('/products');
      await expect(page.getByRole('heading', { name: 'Products' })).toBeVisible();
      await expect(page.getByText('Manage your product catalog')).toBeVisible();
    });

    test('should have Add Product button', async ({ page }) => {
      await page.goto('/products');
      await expect(page.getByRole('link', { name: /add product/i })).toBeVisible();
    });

    test('should navigate to new product page', async ({ page }) => {
      await page.goto('/products');
      await page.getByRole('link', { name: /add product/i }).click();
      await expect(page).toHaveURL(/products\/new/);
    });

    test('should have search input', async ({ page }) => {
      await page.goto('/products');
      await expect(page.getByPlaceholder(/search products/i)).toBeVisible();
    });
  });

  test.describe('Create Product Page', () => {
    test('should display create product form', async ({ page }) => {
      await page.goto('/products/new');
      await expect(page.getByRole('heading', { name: 'Add New Product' })).toBeVisible();
    });

    test('should have all form sections', async ({ page }) => {
      await page.goto('/products/new');
      await expect(page.getByText('Basic Information')).toBeVisible();
      await expect(page.getByText('Pricing', { exact: true }).first()).toBeVisible();
      await expect(page.getByText('Dimensions & Shipping')).toBeVisible();
    });

    test('should have product name input', async ({ page }) => {
      await page.goto('/products/new');
      await expect(page.getByLabel(/product name/i)).toBeVisible();
    });

    test('should have SKU input with generate button', async ({ page }) => {
      await page.goto('/products/new');
      await expect(page.getByLabel(/sku/i).first()).toBeVisible();
      await expect(page.getByRole('button', { name: /generate/i })).toBeVisible();
    });

    test('should have category and brand selects', async ({ page }) => {
      await page.goto('/products/new');
      // Check that the Category and Brand labels exist in the form
      await expect(page.locator('label:has-text("Category")').first()).toBeVisible();
      await expect(page.locator('label:has-text("Brand")').first()).toBeVisible();
    });

    test('should have pricing inputs', async ({ page }) => {
      await page.goto('/products/new');
      await expect(page.getByLabel(/mrp/i)).toBeVisible();
      await expect(page.getByLabel(/selling price/i)).toBeVisible();
    });

    test('should have save button', async ({ page }) => {
      await page.goto('/products/new');
      await expect(page.getByRole('button', { name: /save product/i })).toBeVisible();
    });

    test('should have cancel button to go back', async ({ page }) => {
      await page.goto('/products/new');
      await page.getByRole('link', { name: /cancel/i }).click();
      await expect(page).toHaveURL(/products$/);
    });
  });

  test.describe('Categories Page', () => {
    test('should display categories page', async ({ page }) => {
      await page.goto('/products/categories');
      await expect(page.getByRole('heading', { name: 'Categories' })).toBeVisible();
    });

    test('should have Add Category button', async ({ page }) => {
      await page.goto('/products/categories');
      await expect(page.getByRole('button', { name: /add category/i })).toBeVisible();
    });

    test('should open create category dialog', async ({ page }) => {
      await page.goto('/products/categories');
      const addButton = page.getByRole('button', { name: /add category/i });
      await expect(addButton).toBeVisible();
      await addButton.click();
      // Wait for dialog to appear
      await page.waitForSelector('[role="dialog"]', { timeout: 10000 });
      await expect(page.locator('[role="dialog"]')).toBeVisible();
    });

    test('should display form after clicking add category button', async ({ page }) => {
      await page.goto('/products/categories');
      await page.getByRole('button', { name: /add category/i }).click();
      // Wait and check that dialog appeared - it will have a title
      await page.waitForTimeout(500);
      // Dialog should be present in the DOM
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Brands Page', () => {
    test('should display brands page', async ({ page }) => {
      await page.goto('/products/brands');
      await expect(page.getByRole('heading', { name: 'Brands' })).toBeVisible();
    });

    test('should have Add Brand button', async ({ page }) => {
      await page.goto('/products/brands');
      await expect(page.getByRole('button', { name: /add brand/i })).toBeVisible();
    });

    test('should open create brand dialog', async ({ page }) => {
      await page.goto('/products/brands');
      await page.getByRole('button', { name: /add brand/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByText('Create New Brand')).toBeVisible();
    });

    test('should have brand form fields in dialog', async ({ page }) => {
      await page.goto('/products/brands');
      await page.getByRole('button', { name: /add brand/i }).click();
      await expect(page.getByLabel(/name/i).first()).toBeVisible();
      await expect(page.getByLabel(/code/i).first()).toBeVisible();
      await expect(page.getByLabel(/description/i)).toBeVisible();
    });

    test('should close dialog on cancel', async ({ page }) => {
      await page.goto('/products/brands');
      await page.getByRole('button', { name: /add brand/i }).click();
      await page.getByRole('button', { name: /cancel/i }).click();
      await expect(page.getByRole('dialog')).not.toBeVisible();
    });
  });
});
