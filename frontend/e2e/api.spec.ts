import { test, expect } from '@playwright/test';

const API_URL = 'http://localhost:8000/api/v1';

test.describe('API Tests', () => {
  let accessToken: string;

  test.beforeAll(async ({ request }) => {
    // Get auth token
    const response = await request.post(`${API_URL}/auth/login`, {
      data: {
        email: 'admin@consumer.com',
        password: 'Admin@123',
      },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    accessToken = data.access_token;
  });

  test('should get products list', async ({ request }) => {
    const response = await request.get(`${API_URL}/products`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('items');
  });

  test('should get categories list', async ({ request }) => {
    const response = await request.get(`${API_URL}/categories`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    expect(response.ok()).toBeTruthy();
  });

  test('should get orders list', async ({ request }) => {
    const response = await request.get(`${API_URL}/orders`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('items');
  });

  test('should get warehouses list', async ({ request }) => {
    const response = await request.get(`${API_URL}/warehouses`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    expect(response.ok()).toBeTruthy();
  });

  test('should get current user via /auth/me', async ({ request }) => {
    const response = await request.get(`${API_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.email).toBe('admin@consumer.com');
  });

  test('should get vendors list', async ({ request }) => {
    const response = await request.get(`${API_URL}/vendors`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    expect(response.ok()).toBeTruthy();
  });

  test('should get roles list', async ({ request }) => {
    const response = await request.get(`${API_URL}/roles`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    expect(response.ok()).toBeTruthy();
  });
});
