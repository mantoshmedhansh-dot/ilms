import apiClient from './client';
import { PaginatedResponse, User, Role, Permission, Product, Category, Brand, Order, Customer, Warehouse, StockItem, StockMovement, Vendor, PurchaseOrder, ServiceRequest, Dealer } from '@/types';

// Export auth API
export { authApi } from './auth';

// Users API
export const usersApi = {
  list: async (params?: { page?: number; size?: number; search?: string; is_active?: boolean }) => {
    const { data } = await apiClient.get<PaginatedResponse<User>>('/users', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<User>(`/users/${id}`);
    return data;
  },
  create: async (user: Partial<User> & { password: string }) => {
    const { data } = await apiClient.post<User>('/users', user);
    return data;
  },
  update: async (id: string, user: Partial<User>) => {
    const { data } = await apiClient.put<User>(`/users/${id}`, user);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/users/${id}`);
  },
  assignRoles: async (userId: string, roleIds: string[]) => {
    const { data } = await apiClient.put<User>(`/users/${userId}/roles`, { role_ids: roleIds });
    return data;
  },
  adminResetPassword: async (userId: string, newPassword: string) => {
    const { data } = await apiClient.post('/auth/admin-reset-password', { user_id: userId, new_password: newPassword });
    return data;
  },
};

// Roles API
// Valid role levels (strings expected by backend)
const VALID_ROLE_LEVELS = ['SUPER_ADMIN', 'DIRECTOR', 'HEAD', 'MANAGER', 'EXECUTIVE'];

export const rolesApi = {
  list: async (params?: { page?: number; size?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Role>>('/roles', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Role>(`/roles/${id}`);
    return data;
  },
  create: async (role: {
    name: string;
    code?: string;
    description?: string;
    level?: string;
    permission_ids?: string[];
  }) => {
    // Backend expects level as string: "SUPER_ADMIN", "DIRECTOR", "HEAD", "MANAGER", "EXECUTIVE"
    const levelValue = VALID_ROLE_LEVELS.includes(role.level || '')
      ? role.level
      : 'EXECUTIVE';

    const payload = {
      name: role.name,
      code: role.code || role.name.toUpperCase().replace(/\s+/g, '_'),
      level: levelValue,
      description: role.description || undefined,
      permission_ids: role.permission_ids || [],
    };
    const { data } = await apiClient.post<Role>('/roles', payload);
    return data;
  },
  update: async (id: string, role: Partial<Role>) => {
    const { data } = await apiClient.put<Role>(`/roles/${id}`, role);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/roles/${id}`);
  },
  assignPermissions: async (roleId: string, permissionIds: string[]) => {
    const { data } = await apiClient.put<Role>(`/roles/${roleId}/permissions`, { permission_ids: permissionIds });
    return data;
  },
};

// Permissions API
export const permissionsApi = {
  list: async (params?: { module?: string }) => {
    const { data } = await apiClient.get<{ items: Permission[]; total: number }>('/permissions', { params });
    return data.items;  // Backend returns {items: [...], total: N}, extract items
  },
  getModules: async () => {
    const { data } = await apiClient.get<string[]>('/permissions/modules');
    return data;
  },
  getByModule: async (): Promise<Record<string, Permission[]>> => {
    try {
      // Backend returns: { modules: [...], total_permissions: N }
      // Frontend expects: { module_name: [...permissions] }
      interface BackendModule {
        module_id: string;
        module_name: string;
        module_code: string;
        permissions: Permission[];
      }
      interface BackendResponse {
        modules: BackendModule[];
        total_permissions: number;
      }

      const { data } = await apiClient.get<BackendResponse>('/permissions/by-module');

      // Transform backend response to frontend format
      const grouped: Record<string, Permission[]> = {};
      if (data.modules && Array.isArray(data.modules)) {
        data.modules.forEach((moduleGroup) => {
          const moduleName = moduleGroup.module_name || moduleGroup.module_code || 'general';
          grouped[moduleName] = moduleGroup.permissions || [];
        });
      }
      return grouped;
    } catch {
      // Fallback: fetch all permissions and group by module on client
      const response = await apiClient.get<{ items: Permission[]; total: number } | Permission[]>('/permissions');
      const permissions = Array.isArray(response.data) ? response.data : response.data.items;
      const grouped: Record<string, Permission[]> = {};
      permissions.forEach((permission) => {
        // Handle module as string or object
        const moduleCode = typeof permission.module === 'string'
          ? permission.module
          : (permission.module?.code || 'general');
        if (!grouped[moduleCode]) {
          grouped[moduleCode] = [];
        }
        grouped[moduleCode].push(permission);
      });
      return grouped;
    }
  },
};

// Products API
export const productsApi = {
  list: async (params?: { page?: number; size?: number; search?: string; category_id?: string; brand_id?: string; status?: string; is_active?: boolean; is_featured?: boolean; is_bestseller?: boolean; is_new_arrival?: boolean; min_price?: number; max_price?: number; sort_by?: string; sort_order?: string }) => {
    const { data } = await apiClient.get<PaginatedResponse<Product>>('/products', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Product>(`/products/${id}`);
    return data;
  },
  getBySku: async (sku: string) => {
    const { data } = await apiClient.get<Product>(`/products/sku/${sku}`);
    return data;
  },
  getBySlug: async (slug: string) => {
    const { data } = await apiClient.get<Product>(`/products/slug/${slug}`);
    return data;
  },
  getStats: async () => {
    const { data } = await apiClient.get('/products/stats');
    return data;
  },
  create: async (product: Partial<Product>) => {
    const { data } = await apiClient.post<Product>('/products', product);
    return data;
  },
  update: async (id: string, product: Partial<Product>) => {
    const { data } = await apiClient.put<Product>(`/products/${id}`, product);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/products/${id}`);
  },
  // Product Images
  addImage: async (productId: string, image: { image_url: string; thumbnail_url?: string; alt_text?: string; is_primary?: boolean; sort_order?: number }) => {
    const { data } = await apiClient.post(`/products/${productId}/images`, image);
    return data;
  },
  deleteImage: async (productId: string, imageId: string) => {
    await apiClient.delete(`/products/${productId}/images/${imageId}`);
  },
  setPrimaryImage: async (productId: string, imageId: string) => {
    const { data } = await apiClient.put(`/products/${productId}/images/${imageId}/primary`);
    return data;
  },
  // Product Variants
  addVariant: async (productId: string, variant: { name: string; sku: string; attributes?: Record<string, string>; mrp?: number; selling_price?: number; stock_quantity?: number; image_url?: string }) => {
    const { data } = await apiClient.post(`/products/${productId}/variants`, variant);
    return data;
  },
  updateVariant: async (productId: string, variantId: string, variant: Partial<{ name: string; sku: string; attributes?: Record<string, string>; mrp?: number; selling_price?: number; stock_quantity?: number; image_url?: string; is_active?: boolean }>) => {
    const { data } = await apiClient.put(`/products/${productId}/variants/${variantId}`, variant);
    return data;
  },
  deleteVariant: async (productId: string, variantId: string) => {
    await apiClient.delete(`/products/${productId}/variants/${variantId}`);
  },
  // Product Specifications
  addSpecification: async (productId: string, spec: { group_name?: string; key: string; value: string; sort_order?: number }) => {
    const { data } = await apiClient.post(`/products/${productId}/specifications`, spec);
    return data;
  },
  updateSpecification: async (productId: string, specId: string, spec: Partial<{ group_name?: string; key: string; value: string; sort_order?: number }>) => {
    const { data } = await apiClient.put(`/products/${productId}/specifications/${specId}`, spec);
    return data;
  },
  deleteSpecification: async (productId: string, specId: string) => {
    await apiClient.delete(`/products/${productId}/specifications/${specId}`);
  },
  // Product Documents
  addDocument: async (productId: string, doc: { title: string; document_type?: string; file_url: string; file_size_bytes?: number; mime_type?: string }) => {
    const { data } = await apiClient.post(`/products/${productId}/documents`, doc);
    return data;
  },
  deleteDocument: async (productId: string, docId: string) => {
    await apiClient.delete(`/products/${productId}/documents/${docId}`);
  },
  // Product Costing (COGS) API
  getCost: async (productId: string, params?: { variant_id?: string; warehouse_id?: string }) => {
    const { data } = await apiClient.get<{
      id: string;
      product_id: string;
      variant_id?: string;
      warehouse_id?: string;
      valuation_method: string;
      average_cost: number;
      last_purchase_cost?: number;
      standard_cost?: number;
      quantity_on_hand: number;
      total_value: number;
      last_grn_id?: string;
      last_calculated_at?: string;
      cost_variance?: number;
      cost_variance_percentage?: number;
      cost_history?: Array<{
        date: string;
        grn_id: string;
        grn_number: string;
        quantity: number;
        unit_cost: number;
        old_qty: number;
        old_avg: number;
        new_qty: number;
        new_avg: number;
      }>;
      created_at: string;
      updated_at: string;
    }>(`/products/${productId}/cost`, { params });
    return data;
  },
  getCostHistory: async (productId: string, params?: { variant_id?: string; warehouse_id?: string; limit?: number }) => {
    const { data } = await apiClient.get<{
      product_id: string;
      product_name?: string;
      sku?: string;
      current_average_cost: number;
      quantity_on_hand: number;
      entries: Array<{
        date: string;
        quantity: number;
        unit_cost: number;
        grn_id?: string;
        grn_number?: string;
        running_average: number;
        old_qty?: number;
        old_avg?: number;
      }>;
      total_entries: number;
    }>(`/products/${productId}/cost-history`, { params });
    return data;
  },
  calculateWeightedAverage: async (productId: string, data: { new_quantity: number; new_unit_cost: number; variant_id?: string; warehouse_id?: string }) => {
    const { data: result } = await apiClient.post<{
      product_id: string;
      old_quantity: number;
      old_average_cost: number;
      old_total_value: number;
      new_quantity: number;
      new_unit_cost: number;
      new_purchase_value: number;
      resulting_quantity: number;
      resulting_average_cost: number;
      resulting_total_value: number;
    }>(`/products/${productId}/calculate-cost`, data);
    return result;
  },
  setStandardCost: async (productId: string, standardCost: number, params?: { variant_id?: string; warehouse_id?: string }) => {
    const { data } = await apiClient.put<{
      message: string;
      product_id: string;
      standard_cost: number;
      average_cost: number;
      variance?: number;
      variance_percentage?: number;
    }>(`/products/${productId}/standard-cost`, null, { params: { ...params, standard_cost: standardCost } });
    return data;
  },
};

// Categories API
export const categoriesApi = {
  list: async (params?: { page?: number; size?: number; parent_id?: string; include_inactive?: boolean }) => {
    const { data } = await apiClient.get<PaginatedResponse<Category>>('/categories', { params });
    return data;
  },
  // Get only ROOT categories (parent_id IS NULL) - for cascading dropdown first level
  getRoots: async () => {
    const { data } = await apiClient.get<PaginatedResponse<Category>>('/categories/roots');
    return data;
  },
  // Get children of a parent category - for cascading dropdown second level
  getChildren: async (parentId: string) => {
    const { data } = await apiClient.get<PaginatedResponse<Category>>(`/categories/${parentId}/children`);
    return data;
  },
  getTree: async () => {
    const { data } = await apiClient.get('/categories/tree');
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Category>(`/categories/${id}`);
    return data;
  },
  getBySlug: async (slug: string) => {
    const { data } = await apiClient.get<Category>(`/categories/slug/${slug}`);
    return data;
  },
  create: async (category: Partial<Category>) => {
    const { data } = await apiClient.post<Category>('/categories', category);
    return data;
  },
  update: async (id: string, category: Partial<Category>) => {
    const { data } = await apiClient.put<Category>(`/categories/${id}`, category);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/categories/${id}`);
  },
};

// Brands API
export const brandsApi = {
  list: async (params?: { page?: number; size?: number; is_active?: boolean }) => {
    const { data } = await apiClient.get<PaginatedResponse<Brand>>('/brands', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Brand>(`/brands/${id}`);
    return data;
  },
  create: async (brand: {
    name: string;
    code?: string;
    slug?: string;
    description?: string;
    logo_url?: string;
    is_active?: boolean;
  }) => {
    // Transform frontend fields to backend required fields
    // Backend requires: name and slug
    const payload = {
      name: brand.name,
      slug: brand.slug || brand.code?.toLowerCase() || brand.name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''),
      description: brand.description || undefined,
      logo_url: brand.logo_url || undefined,
      is_active: brand.is_active ?? true,
    };
    const { data } = await apiClient.post<Brand>('/brands', payload);
    return data;
  },
  update: async (id: string, brand: Partial<Brand>) => {
    const { data } = await apiClient.put<Brand>(`/brands/${id}`, brand);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/brands/${id}`);
  },
};

// Orders API
export const ordersApi = {
  list: async (params?: { page?: number; size?: number; status?: string; search?: string; channel?: string }) => {
    const { data } = await apiClient.get<PaginatedResponse<Order>>('/orders', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Order>(`/orders/${id}`);
    return data;
  },
  create: async (order: Partial<Order>) => {
    const { data } = await apiClient.post<Order>('/orders', order);
    return data;
  },
  updateStatus: async (id: string, status: string, notes?: string) => {
    const { data } = await apiClient.put<Order>(`/orders/${id}/status`, { status, notes });
    return data;
  },
  cancel: async (id: string, reason: string) => {
    const { data } = await apiClient.post<Order>(`/orders/${id}/cancel`, { reason });
    return data;
  },
};

// Customers API
export const customersApi = {
  list: async (params?: { page?: number; size?: number; search?: string; customer_type?: string }) => {
    const { data } = await apiClient.get<PaginatedResponse<Customer>>('/customers', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Customer>(`/customers/${id}`);
    return data;
  },
  get360View: async (id: string) => {
    const { data } = await apiClient.get(`/customers/${id}/360`);
    return data;
  },
  create: async (customer: {
    name?: string;
    first_name?: string;
    last_name?: string;
    phone: string;
    email?: string;
    customer_type?: string;
    address_line1?: string;
    address_line2?: string;
    city?: string;
    state?: string;
    pincode?: string;
    gst_number?: string;
    notes?: string;
  }) => {
    // Transform frontend fields to backend required fields
    // Backend expects first_name, not name
    const nameParts = (customer.name || '').trim().split(' ');
    const payload = {
      first_name: customer.first_name || nameParts[0] || 'Customer',
      last_name: customer.last_name || nameParts.slice(1).join(' ') || undefined,
      phone: customer.phone,
      email: customer.email || undefined,
      customer_type: customer.customer_type || 'INDIVIDUAL',
      address_line1: customer.address_line1 || undefined,
      address_line2: customer.address_line2 || undefined,
      city: customer.city || undefined,
      state: customer.state || undefined,
      pincode: customer.pincode || undefined,
      gstin: customer.gst_number || undefined,
      notes: customer.notes || undefined,
    };
    const { data } = await apiClient.post<Customer>('/customers', payload);
    return data;
  },
  update: async (id: string, customer: Partial<Customer>) => {
    const { data } = await apiClient.put<Customer>(`/customers/${id}`, customer);
    return data;
  },
  searchByPhone: async (phone: string) => {
    // Search customers by phone number
    const { data } = await apiClient.get<PaginatedResponse<Customer>>('/customers', { params: { search: phone, size: 10 } });
    return data.items;
  },
  getByPhone: async (phone: string) => {
    try {
      const { data } = await apiClient.get<Customer>(`/customers/phone/${encodeURIComponent(phone)}`);
      return data;
    } catch (error) {
      // Only return null for 404 (not found), throw for other errors
      if ((error as { response?: { status?: number } })?.response?.status === 404) {
        return null;
      }
      console.error('Failed to fetch customer by phone:', error);
      throw error;
    }
  },
};

// Warehouses API
export const warehousesApi = {
  list: async (params?: { page?: number; size?: number; type?: string; is_active?: boolean }) => {
    const { data } = await apiClient.get<PaginatedResponse<Warehouse>>('/warehouses', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Warehouse>(`/warehouses/${id}`);
    return data;
  },
  create: async (warehouse: {
    name: string;
    code: string;
    type?: string;
    address?: string;
    city?: string;
    state?: string;
    pincode?: string;
    capacity?: number;
    is_active?: boolean;
  }) => {
    // Transform frontend fields to backend fields
    const payload = {
      name: warehouse.name,
      code: warehouse.code,
      warehouse_type: (warehouse.type || 'MAIN').toUpperCase(),
      address_line1: warehouse.address || '',
      city: warehouse.city,
      state: warehouse.state,
      pincode: warehouse.pincode,
      total_capacity: warehouse.capacity || 0,
      is_active: warehouse.is_active ?? true,
    };
    const { data } = await apiClient.post<Warehouse>('/warehouses', payload);
    return data;
  },
  update: async (id: string, warehouse: Partial<{
    name: string;
    code: string;
    type: string;
    address: string;
    city: string;
    state: string;
    pincode: string;
    capacity: number;
    is_active: boolean;
  }>) => {
    // Transform frontend fields to backend fields
    const payload: Record<string, unknown> = {};
    if (warehouse.name !== undefined) payload.name = warehouse.name;
    if (warehouse.code !== undefined) payload.code = warehouse.code;
    if (warehouse.type !== undefined) payload.warehouse_type = warehouse.type.toUpperCase();
    if (warehouse.address !== undefined) payload.address_line1 = warehouse.address;
    if (warehouse.city !== undefined) payload.city = warehouse.city;
    if (warehouse.state !== undefined) payload.state = warehouse.state;
    if (warehouse.pincode !== undefined) payload.pincode = warehouse.pincode;
    if (warehouse.capacity !== undefined) payload.total_capacity = warehouse.capacity;
    if (warehouse.is_active !== undefined) payload.is_active = warehouse.is_active;
    const { data } = await apiClient.put<Warehouse>(`/warehouses/${id}`, payload);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/warehouses/${id}`);
  },
  dropdown: async () => {
    // Use dedicated dropdown endpoint for better performance
    const { data } = await apiClient.get<Array<{ id: string; name: string; code: string; warehouse_type: string }>>('/warehouses/dropdown');
    return data;
  },
  getNextCode: async (): Promise<string> => {
    // Get next auto-generated warehouse code (WH001, WH002, etc.)
    const { data } = await apiClient.get<{ code: string }>('/warehouses/next-code');
    return data.code;
  },
};

// Channels API
export const channelsApi = {
  list: async (params?: { page?: number; size?: number; channel_type?: string; status?: string; search?: string }) => {
    const { data } = await apiClient.get('/channels', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/channels/${id}`);
    return data;
  },
  create: async (channel: { name: string; channel_type: string; description?: string }) => {
    const { data } = await apiClient.post('/channels', channel);
    return data;
  },
  update: async (id: string, channel: Partial<{
    name: string;
    channel_type: string;
    description?: string;
    status?: string;
    commission_percentage?: number;
    fixed_fee_per_order?: number;
    payment_cycle_days?: number;
    price_markup_percentage?: number;
    price_discount_percentage?: number;
    tax_inclusive_pricing?: boolean;
    collect_tcs?: boolean;
    tcs_rate?: number;
  }>) => {
    const { data } = await apiClient.put(`/channels/${id}`, channel);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/channels/${id}`);
  },
  dropdown: async () => {
    // Return channels for dropdown selection
    const { data } = await apiClient.get<Array<{ id: string; code: string; name: string; type: string }>>('/channels/dropdown');
    return data;
  },
  activate: async (id: string) => {
    const { data } = await apiClient.post(`/channels/${id}/activate`);
    return data;
  },
  deactivate: async (id: string) => {
    const { data } = await apiClient.post(`/channels/${id}/deactivate`);
    return data;
  },

  // Channel Pricing
  pricing: {
    list: async (channelId: string, params?: { skip?: number; limit?: number; product_id?: string; is_active?: boolean }) => {
      const { data } = await apiClient.get(`/channels/${channelId}/pricing`, { params });
      return data;
    },
    create: async (channelId: string, pricing: {
      product_id: string;
      variant_id?: string;
      mrp: number;
      selling_price: number;
      transfer_price?: number;
      discount_percentage?: number;
      max_discount_percentage?: number;
      is_active?: boolean;
      is_listed?: boolean;
      effective_from?: string;
      effective_to?: string;
    }) => {
      const { data } = await apiClient.post(`/channels/${channelId}/pricing`, pricing);
      return data;
    },
    update: async (channelId: string, pricingId: string, pricing: {
      mrp?: number;
      selling_price?: number;
      transfer_price?: number;
      discount_percentage?: number;
      max_discount_percentage?: number;
      is_active?: boolean;
      is_listed?: boolean;
      effective_from?: string;
      effective_to?: string;
    }) => {
      const { data } = await apiClient.put(`/channels/${channelId}/pricing/${pricingId}`, pricing);
      return data;
    },
    delete: async (channelId: string, pricingId: string) => {
      await apiClient.delete(`/channels/${channelId}/pricing/${pricingId}`);
    },
    sync: async (channelId: string, productIds?: string[]) => {
      const { data } = await apiClient.post(`/channels/${channelId}/pricing/sync`, { product_ids: productIds });
      return data;
    },
    bulk: async (channelId: string, items: Array<{
      product_id: string;
      mrp: number;
      selling_price: number;
      transfer_price?: number;
      max_discount_percentage?: number;
      is_active?: boolean;
    }>) => {
      const { data } = await apiClient.post(`/channels/${channelId}/pricing/bulk`, { items });
      return data;
    },
    export: async (channelId: string) => {
      // Get all pricing for export
      const { data } = await apiClient.get(`/channels/${channelId}/pricing`, { params: { limit: 1000 } });
      return data;
    },
    // Compare pricing across channels for a product
    compare: async (productId: string) => {
      const { data } = await apiClient.get(`/pricing/compare/${productId}`);
      return data;
    },
    // Get comparison for multiple products
    compareMultiple: async (productIds: string[]) => {
      const { data } = await apiClient.post('/pricing/compare', { product_ids: productIds });
      return data;
    },
    // Copy pricing from one channel to another
    copyFrom: async (destinationChannelId: string, sourceChannelId: string, overwrite: boolean = false) => {
      const { data } = await apiClient.post(
        `/channels/${destinationChannelId}/pricing/copy-from/${sourceChannelId}`,
        null,
        { params: { overwrite } }
      );
      return data;
    },
  },

  // Pricing Rules
  pricingRules: {
    list: async (params?: { page?: number; size?: number; channel_id?: string; rule_type?: string; is_active?: boolean }) => {
      const { data } = await apiClient.get('/channels/pricing-rules', { params });
      return data;
    },
    getById: async (ruleId: string) => {
      const { data } = await apiClient.get(`/channels/pricing-rules/${ruleId}`);
      return data;
    },
    create: async (rule: {
      code: string;
      name: string;
      description?: string;
      rule_type: string;
      channel_id?: string;
      category_id?: string;
      product_id?: string;
      conditions: Record<string, unknown>;
      discount_type: string;
      discount_value: number;
      effective_from?: string;
      effective_to?: string;
      priority?: number;
      is_combinable?: boolean;
      is_active?: boolean;
    }) => {
      const { data } = await apiClient.post('/channels/pricing-rules', rule);
      return data;
    },
    update: async (ruleId: string, rule: Partial<{
      name: string;
      description: string;
      conditions: Record<string, unknown>;
      discount_type: string;
      discount_value: number;
      effective_from: string;
      effective_to: string;
      priority: number;
      is_combinable: boolean;
      is_active: boolean;
    }>) => {
      const { data } = await apiClient.put(`/channels/pricing-rules/${ruleId}`, rule);
      return data;
    },
    delete: async (ruleId: string) => {
      await apiClient.delete(`/channels/pricing-rules/${ruleId}`);
    },
  },

  // Pricing History
  pricingHistory: {
    list: async (params?: { page?: number; size?: number; entity_type?: string; entity_id?: string; channel_id?: string }) => {
      const { data } = await apiClient.get('/channels/pricing-history', { params });
      return data;
    },
  },

  // Channel Inventory
  inventory: {
    list: async (channelId: string, params?: { skip?: number; limit?: number; product_id?: string; warehouse_id?: string }) => {
      const { data } = await apiClient.get(`/channels/${channelId}/inventory`, { params });
      return data;
    },
    listAll: async (params?: { page?: number; size?: number; channel_id?: string; sync_status?: string; product_id?: string }) => {
      const { data } = await apiClient.get('/channels/inventory', { params });
      return data;
    },
    stats: async (channelId?: string) => {
      const { data } = await apiClient.get('/channels/inventory/stats', { params: channelId ? { channel_id: channelId } : undefined });
      return data;
    },
    create: async (channelId: string, inventory: {
      product_id: string;
      warehouse_id: string;
      variant_id?: string;
      allocated_quantity: number;
      buffer_quantity?: number;
    }) => {
      const { data } = await apiClient.post(`/channels/${channelId}/inventory`, inventory);
      return data;
    },
    update: async (channelId: string, inventoryId: string, inventory: {
      allocated_quantity?: number;
      buffer_quantity?: number;
      reserved_quantity?: number;
      is_active?: boolean;
    }) => {
      const { data } = await apiClient.put(`/channels/${channelId}/inventory/${inventoryId}`, inventory);
      return data;
    },
    delete: async (channelId: string, inventoryId: string) => {
      await apiClient.delete(`/channels/${channelId}/inventory/${inventoryId}`);
    },
    sync: async (channelId: string, productIds?: string[]) => {
      const { data } = await apiClient.post(`/channels/${channelId}/inventory/sync`, { product_ids: productIds });
      return data;
    },
    syncSingle: async (inventoryId: string) => {
      const { data } = await apiClient.post(`/channels/inventory/${inventoryId}/sync`);
      return data;
    },
    syncAll: async (channelId?: string) => {
      const { data } = await apiClient.post('/channels/inventory/sync-all', undefined, { params: channelId ? { channel_id: channelId } : undefined });
      return data;
    },
    updateBuffer: async (inventoryId: string, bufferStock: number) => {
      const { data } = await apiClient.put(`/channels/inventory/${inventoryId}/buffer`, undefined, { params: { buffer_stock: bufferStock } });
      return data;
    },
  },

  // Channel Orders
  orders: {
    list: async (channelId: string, params?: { skip?: number; limit?: number; status?: string; start_date?: string; end_date?: string; search?: string }) => {
      const { data } = await apiClient.get(`/channels/${channelId}/orders`, { params });
      return data;
    },
    create: async (channelId: string, order: {
      order_id: string;
      channel_order_id: string;
      channel_order_item_id?: string;
      channel_selling_price: number;
      channel_shipping_fee?: number;
      channel_commission?: number;
      channel_tcs?: number;
      net_receivable: number;
      channel_status?: string;
      raw_order_data?: Record<string, unknown>;
    }) => {
      const { data } = await apiClient.post(`/channels/${channelId}/orders`, order);
      return data;
    },
    update: async (channelId: string, orderId: string, order: {
      channel_status?: string;
      settlement_id?: string;
      settlement_date?: string;
      is_settled?: boolean;
    }) => {
      const { data } = await apiClient.put(`/channels/${channelId}/orders/${orderId}`, order);
      return data;
    },
    delete: async (channelId: string, orderId: string) => {
      await apiClient.delete(`/channels/${channelId}/orders/${orderId}`);
    },
    sync: async (channelId: string, params?: { start_date?: string; end_date?: string }) => {
      const { data } = await apiClient.post(`/channels/${channelId}/orders/sync`, undefined, { params });
      return data;
    },
    convert: async (channelId: string, orderId: string) => {
      const { data } = await apiClient.post(`/channels/${channelId}/orders/${orderId}/convert`);
      return data;
    },
  },

  // Reports
  reports: {
    summary: async (startDate: string, endDate: string) => {
      const { data } = await apiClient.get('/channels/reports/summary', { params: { start_date: startDate, end_date: endDate } });
      return data;
    },
    inventoryStatus: async (channelId?: string) => {
      const { data } = await apiClient.get('/channels/reports/inventory-status', { params: channelId ? { channel_id: channelId } : undefined });
      return data;
    },
  },
};

// Inventory API
export const inventoryApi = {
  getStock: async (params?: {
    page?: number;
    size?: number;
    warehouse_id?: string;
    product_id?: string;
    status?: string;
    view?: 'aggregate' | 'serialized';
    item_type?: string;
    grn_number?: string;
    serial_number?: string;
  }) => {
    const { data } = await apiClient.get<PaginatedResponse<StockItem>>('/inventory/stock-items', { params });
    return data;
  },
  getStockSummary: async () => {
    // Dashboard Summary page - calls /dashboard-stats for stats
    const { data } = await apiClient.get('/inventory/dashboard-stats');
    return data;
  },
  getInventorySummaryList: async (params?: { page?: number; size?: number; warehouse_id?: string }) => {
    // Paginated list of inventory summary records
    const { data } = await apiClient.get('/inventory/summary', { params });
    return data;
  },
  getLowStock: async () => {
    const { data } = await apiClient.get('/inventory/low-stock');
    return data;
  },
  getStats: async () => {
    // Stock Items page stats - returns total_skus, in_stock, low_stock, out_of_stock
    const { data } = await apiClient.get('/inventory/stats');
    return data;
  },
  adjustStock: async (adjustment: { product_id: string; warehouse_id: string; quantity: number; reason: string }) => {
    const { data } = await apiClient.post('/inventory/adjust', adjustment);
    return data;
  },
  getMovements: async (params?: {
    page?: number;
    size?: number;
    warehouse_id?: string;
    product_id?: string;
    movement_type?: string;
    date_from?: string;
    date_to?: string;
  }) => {
    const { data } = await apiClient.get<PaginatedResponse<StockMovement>>('/inventory/movements', { params });
    return data;
  },
};

// Vendors API
// Helper to transform vendor response from backend to frontend format
// Maps backend field names to frontend expected names with aliases
const transformVendorResponse = (vendor: Record<string, unknown>): Vendor => {
  const vendorCode = (vendor.vendor_code || vendor.code || '') as string;
  const gstin = (vendor.gstin || vendor.gst_number) as string | undefined;
  const pan = (vendor.pan || vendor.pan_number) as string | undefined;
  const grade = (vendor.grade || vendor.tier) as Vendor['grade'];

  return {
    id: vendor.id as string,
    name: vendor.name as string,
    // Backend field + alias
    vendor_code: vendorCode,
    code: vendorCode,
    // Legal/trade names
    legal_name: vendor.legal_name as string | undefined,
    trade_name: vendor.trade_name as string | undefined,
    // Vendor type
    vendor_type: vendor.vendor_type as Vendor['vendor_type'],
    // Contact
    email: vendor.email as string | undefined,
    phone: vendor.phone as string | undefined,
    contact_person: vendor.contact_person as string | undefined,
    // Tax IDs with aliases
    gstin: gstin,
    gst_number: gstin,
    pan: pan,
    pan_number: pan,
    // Status and grade with alias
    status: (vendor.status || 'ACTIVE') as Vendor['status'],
    grade: grade,
    tier: grade,
    // Address
    address_line1: vendor.address_line1 as string | undefined,
    address_line2: vendor.address_line2 as string | undefined,
    city: vendor.city as string | undefined,
    state: vendor.state as string | undefined,
    pincode: vendor.pincode as string | undefined,
    country: vendor.country as string | undefined,
    // Bank Details
    bank_name: vendor.bank_name as string | undefined,
    bank_branch: vendor.bank_branch as string | undefined,
    bank_account_number: vendor.bank_account_number as string | undefined,
    bank_ifsc: vendor.bank_ifsc as string | undefined,
    bank_account_type: vendor.bank_account_type as Vendor['bank_account_type'],
    beneficiary_name: vendor.beneficiary_name as string | undefined,
    // Supplier code for barcode
    supplier_code: vendor.supplier_code as string | undefined,
    // Timestamps
    created_at: vendor.created_at as string,
  };
};

export const vendorsApi = {
  list: async (params?: { page?: number; size?: number; limit?: number; status?: string; search?: string }) => {
    // Backend uses 'limit', not 'size'
    const apiParams = {
      ...params,
      limit: params?.limit || params?.size || 100,
      skip: params?.page ? (params.page - 1) * (params?.limit || params?.size || 100) : 0,
    };
    delete (apiParams as Record<string, unknown>).size;
    delete (apiParams as Record<string, unknown>).page;
    const { data } = await apiClient.get<{ items: Record<string, unknown>[]; total: number; pages: number }>('/vendors', { params: apiParams });
    return {
      ...data,
      items: data.items.map(transformVendorResponse),
    };
  },
  getDropdown: async (params?: { vendor_type?: string; active_only?: boolean }) => {
    const { data } = await apiClient.get<Record<string, unknown>[]>('/vendors/dropdown', { params });
    return data.map(transformVendorResponse);
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Record<string, unknown>>(`/vendors/${id}`);
    return transformVendorResponse(data);
  },
  getNextCode: async (vendorType: string = 'MANUFACTURER') => {
    const { data } = await apiClient.get<{ next_code: string; prefix: string }>('/vendors/next-code', {
      params: { vendor_type: vendorType }
    });
    return data;
  },
  create: async (vendor: {
    name: string;
    code?: string;
    vendor_code?: string;
    email?: string;
    phone?: string;
    gst_number?: string;
    gstin?: string;
    pan_number?: string;
    pan?: string;
    tier?: string;
    grade?: string;
    vendor_type?: string;
    contact_person?: string;
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
    country?: string;
    // Bank Details
    bank_name?: string;
    bank_branch?: string;
    bank_account_number?: string;
    bank_ifsc?: string;
    bank_account_type?: string;
    beneficiary_name?: string;
  }) => {
    // Transform frontend fields to backend required fields
    // Handle field name aliases (frontend -> backend)
    const payload = {
      name: vendor.name,
      legal_name: vendor.name, // Use name as legal_name
      vendor_type: vendor.vendor_type || 'MANUFACTURER',
      address_line1: vendor.address_line1,
      address_line2: vendor.address_line2 || undefined,
      city: vendor.city,
      state: vendor.state,
      pincode: vendor.pincode,
      country: vendor.country || 'India',
      contact_person: vendor.contact_person || undefined,
      email: vendor.email || undefined,
      phone: vendor.phone || undefined,
      // Map frontend aliases to backend field names
      gstin: vendor.gstin || vendor.gst_number || undefined,
      pan: vendor.pan || vendor.pan_number || undefined,
      grade: vendor.grade || vendor.tier || undefined,
      // Bank Details
      bank_name: vendor.bank_name || undefined,
      bank_branch: vendor.bank_branch || undefined,
      bank_account_number: vendor.bank_account_number || undefined,
      bank_ifsc: vendor.bank_ifsc || undefined,
      bank_account_type: vendor.bank_account_type || undefined,
      beneficiary_name: vendor.beneficiary_name || undefined,
    };
    const { data } = await apiClient.post<Record<string, unknown>>('/vendors', payload);
    return transformVendorResponse(data);
  },
  update: async (id: string, vendor: Partial<Vendor>) => {
    // Transform frontend field names to backend field names
    const payload: Record<string, unknown> = { ...vendor };
    // Handle field name aliases (frontend -> backend)
    if (vendor.gst_number && !vendor.gstin) {
      payload.gstin = vendor.gst_number;
      delete payload.gst_number;
    }
    if (vendor.pan_number && !vendor.pan) {
      payload.pan = vendor.pan_number;
      delete payload.pan_number;
    }
    if (vendor.tier && !vendor.grade) {
      payload.grade = vendor.tier;
      delete payload.tier;
    }
    if (vendor.code && !vendor.vendor_code) {
      payload.vendor_code = vendor.code;
      delete payload.code;
    }
    const { data } = await apiClient.put<Record<string, unknown>>(`/vendors/${id}`, payload);
    return transformVendorResponse(data);
  },
  delete: async (id: string) => {
    await apiClient.delete(`/vendors/${id}`);
  },
};

// Purchase Requisitions API
export interface PurchaseRequisition {
  id: string;
  requisition_number: string;
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED' | 'CONVERTED' | 'CANCELLED';
  requesting_department?: string;
  priority?: string;
  reason?: string;
  request_date: string;
  required_by_date?: string;
  delivery_warehouse_id: string;
  delivery_warehouse_name?: string;
  estimated_total?: number;
  approved_by?: string;
  approved_at?: string;
  items: Array<{
    id: string;
    product_id: string;
    product_name: string;
    sku: string;
    quantity_requested: number;
    estimated_unit_price?: number;
    uom?: string;
    preferred_vendor_id?: string;
    preferred_vendor_name?: string;
    notes?: string;
    monthly_quantities?: Record<string, number>;
  }>;
  created_at: string;
  updated_at: string;
}

export const purchaseRequisitionsApi = {
  getNextNumber: async () => {
    const { data } = await apiClient.get<{ next_number: string; prefix: string }>('/purchase/requisitions/next-number');
    return data;
  },
  list: async (params?: { page?: number; size?: number; status?: string; warehouse_id?: string }) => {
    const queryParams: Record<string, unknown> = {};
    if (params?.page !== undefined) queryParams.skip = (params.page - 1) * (params.size || 50);
    if (params?.size) queryParams.limit = params.size;
    if (params?.status) queryParams.status = params.status;
    if (params?.warehouse_id) queryParams.warehouse_id = params.warehouse_id;
    const { data } = await apiClient.get<{ items: PurchaseRequisition[]; total: number }>('/purchase/requisitions', { params: queryParams });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<PurchaseRequisition>(`/purchase/requisitions/${id}`);
    return data;
  },
  // Get open (approved but not converted) PRs for PO creation
  getOpenForPO: async () => {
    const { data } = await apiClient.get<{ items: PurchaseRequisition[]; total: number }>('/purchase/requisitions', {
      params: { status: 'APPROVED', limit: 100 }
    });
    return data.items;
  },
  create: async (pr: Partial<PurchaseRequisition>) => {
    const { data } = await apiClient.post<PurchaseRequisition>('/purchase/requisitions', pr);
    return data;
  },
  submit: async (id: string) => {
    const { data } = await apiClient.post<PurchaseRequisition>(`/purchase/requisitions/${id}/submit`);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post<PurchaseRequisition>(`/purchase/requisitions/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post<PurchaseRequisition>(`/purchase/requisitions/${id}/reject`, { reason });
    return data;
  },
  cancel: async (id: string, reason: string) => {
    const { data } = await apiClient.post<PurchaseRequisition>(`/purchase/requisitions/${id}/cancel`, { reason });
    return data;
  },
  convertToPO: async (id: string, data?: { vendor_id?: string }) => {
    const { data: result } = await apiClient.post<PurchaseOrder>(`/purchase/requisitions/${id}/convert-to-po`, data);
    return result;
  },
};

// Purchase Orders API
export const purchaseOrdersApi = {
  getNextNumber: async () => {
    const { data } = await apiClient.get<{ next_number: string; prefix: string }>('/purchase/orders/next-number');
    return data;
  },
  getNextSerial: async () => {
    const { data } = await apiClient.get<{ last_serial: number; next_serial: number; message: string }>('/purchase/orders/next-serial');
    return data;
  },
  list: async (params?: { page?: number; size?: number; status?: string; vendor_id?: string }) => {
    const { data } = await apiClient.get<PaginatedResponse<PurchaseOrder>>('/purchase/orders', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<PurchaseOrder>(`/purchase/orders/${id}`);
    return data;
  },
  create: async (po: Partial<PurchaseOrder>) => {
    try {
      const { data } = await apiClient.post<PurchaseOrder>('/purchase/orders', po);
      return data;
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string }; status?: number }; message?: string };
      const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to create purchase order';
      console.error('PO Creation Error:', {
        status: axiosError.response?.status,
        detail: axiosError.response?.data,
        message: axiosError.message,
      });
      throw new Error(errorMessage);
    }
  },
  update: async (id: string, po: Partial<PurchaseOrder>) => {
    const { data } = await apiClient.put<PurchaseOrder>(`/purchase/orders/${id}`, po);
    return data;
  },
  submit: async (id: string) => {
    const { data } = await apiClient.post<PurchaseOrder>(`/purchase/orders/${id}/submit`);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post<PurchaseOrder>(`/purchase/orders/${id}/approve`, { action: "APPROVE" });
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post<PurchaseOrder>(`/purchase/orders/${id}/reject`, { reason });
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/purchase/orders/${id}`);
  },
  download: async (id: string) => {
    const { data } = await apiClient.get<string>(`/purchase/orders/${id}/download`);
    return data;
  },
  // Admin status update (Super Admin only)
  adminUpdateStatus: async (id: string, newStatus: string, reason?: string) => {
    const params = new URLSearchParams({ new_status: newStatus });
    if (reason) params.append('reason', reason);
    const { data } = await apiClient.put<PurchaseOrder>(`/purchase/admin/orders/${id}/status?${params.toString()}`);
    return data;
  },
};

// Service Requests API
export const serviceRequestsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; type?: string; priority?: string }) => {
    const { data } = await apiClient.get<PaginatedResponse<ServiceRequest>>('/service-requests', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<ServiceRequest>(`/service-requests/${id}`);
    return data;
  },
  create: async (request: Record<string, unknown>) => {
    const { data } = await apiClient.post<ServiceRequest>('/service-requests', request);
    return data;
  },
  update: async (id: string, request: Record<string, unknown>) => {
    const { data } = await apiClient.put<ServiceRequest>(`/service-requests/${id}`, request);
    return data;
  },
  assignTechnician: async (id: string, technicianId: string) => {
    const { data } = await apiClient.post<ServiceRequest>(`/service-requests/${id}/assign`, { technician_id: technicianId });
    return data;
  },
  updateStatus: async (id: string, status: string, notes?: string) => {
    const { data } = await apiClient.put<ServiceRequest>(`/service-requests/${id}/status`, { status, notes });
    return data;
  },
};

// ==================== AMC (ANNUAL MAINTENANCE CONTRACT) API ====================
export const amcApi = {
  // Plans
  listPlans: async () => {
    const { data } = await apiClient.get('/amc/plans');
    return data;
  },
  getPlan: async (planId: string) => {
    const { data } = await apiClient.get(`/amc/plans/${planId}`);
    return data;
  },
  createPlan: async (plan: {
    name: string;
    code?: string;
    duration_months: number;
    visits_included: number;
    price: number;
    discount_percentage?: number;
    parts_covered?: boolean;
    labor_covered?: boolean;
    priority_support?: boolean;
    description?: string;
    applicable_products?: string[];
  }) => {
    const { data } = await apiClient.post('/amc/plans', plan);
    return data;
  },
  updatePlan: async (planId: string, plan: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/amc/plans/${planId}`, plan);
    return data;
  },

  // Contracts
  listContracts: async (params?: {
    page?: number;
    size?: number;
    status?: string;
    customer_id?: string;
    plan_id?: string;
    expiring_within_days?: number;
  }) => {
    const { data } = await apiClient.get('/amc/contracts', { params });
    return data;
  },
  getContract: async (contractId: string) => {
    const { data } = await apiClient.get(`/amc/contracts/${contractId}`);
    return data;
  },
  getContractStats: async () => {
    const { data } = await apiClient.get('/amc/contracts/stats');
    return data;
  },
  createContract: async (contract: {
    customer_id: string;
    plan_id: string;
    device_serial?: string;
    installation_id?: string;
    start_date?: string;
    payment_mode?: string;
    notes?: string;
  }) => {
    const { data } = await apiClient.post('/amc/contracts', contract);
    return data;
  },
  activateContract: async (contractId: string, paymentDetails?: { payment_reference?: string; payment_mode?: string }) => {
    const { data } = await apiClient.post(`/amc/contracts/${contractId}/activate`, null, {
      params: paymentDetails
    });
    return data;
  },
  renewContract: async (contractId: string, renewalDetails?: { new_plan_id?: string; payment_reference?: string }) => {
    const { data } = await apiClient.post(`/amc/contracts/${contractId}/renew`, null, {
      params: renewalDetails
    });
    return data;
  },
  useService: async (contractId: string, serviceData: { service_type: string; notes?: string }) => {
    const { data } = await apiClient.post(`/amc/contracts/${contractId}/use-service`, serviceData);
    return data;
  },
};

// Dealers API
export const dealersApi = {
  list: async (params?: { page?: number; size?: number; type?: string; status?: string }) => {
    const { data } = await apiClient.get<PaginatedResponse<Dealer>>('/dealers', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get<Dealer>(`/dealers/${id}`);
    return data;
  },
  create: async (dealer: {
    name: string;
    code?: string;
    type?: string;
    email: string;
    phone: string;
    gst_number: string;
    pan: string;
    contact_person: string;
    pricing_tier?: string;
    credit_limit?: number;
    address_line1: string;
    city: string;
    district: string;
    state: string;
    state_code: string;
    pincode: string;
    region: string;
  }) => {
    // Transform frontend fields to backend required fields
    const payload = {
      name: dealer.name,
      legal_name: dealer.name,
      dealer_type: dealer.type || 'DEALER',
      gstin: dealer.gst_number,
      pan: dealer.pan,
      contact_person: dealer.contact_person || dealer.name,
      email: dealer.email,
      phone: dealer.phone,
      registered_address_line1: dealer.address_line1,
      registered_city: dealer.city,
      registered_district: dealer.district,
      registered_state: dealer.state,
      registered_state_code: dealer.state_code,
      registered_pincode: dealer.pincode,
      region: dealer.region,
      state: dealer.state,
      tier: dealer.pricing_tier || 'STANDARD',
      credit_limit: dealer.credit_limit || 0,
    };
    const { data } = await apiClient.post<Dealer>('/dealers', payload);
    return data;
  },
  update: async (id: string, dealer: Partial<Dealer>) => {
    const { data } = await apiClient.put<Dealer>(`/dealers/${id}`, dealer);
    return data;
  },
  getLedger: async (id: string, params?: { skip?: number; limit?: number; start_date?: string; end_date?: string }) => {
    const { data } = await apiClient.get<{
      items: DealerCreditTransaction[];
      total: number;
      total_debit: number;
      total_credit: number;
      closing_balance: number;
    }>(`/dealers/${id}/ledger`, { params });
    return data;
  },
  getTargets: async (id: string, params?: { year?: number }) => {
    const { data } = await apiClient.get<DealerTarget[]>(`/dealers/${id}/targets`, { params });
    return data;
  },
  recordPayment: async (id: string, payment: {
    transaction_type: string;
    transaction_date: string;
    reference_type: string;
    reference_number: string;
    debit_amount: number;
    credit_amount: number;
    payment_mode?: string;
    payment_reference?: string;
    narration?: string;
  }) => {
    const { data } = await apiClient.post<DealerCreditTransaction>(`/dealers/${id}/payment`, payment);
    return data;
  },
  createTarget: async (id: string, target: {
    target_period: string;
    target_year: number;
    target_month?: number;
    target_quarter?: number;
    target_type: string;
    revenue_target: number;
    quantity_target: number;
    incentive_percentage?: number;
  }) => {
    const { data } = await apiClient.post<DealerTarget>(`/dealers/${id}/targets`, { dealer_id: id, ...target });
    return data;
  },
  getSchemes: async (params?: { scheme_type?: string; is_active?: boolean }) => {
    const { data } = await apiClient.get<{ items: DealerScheme[]; total: number }>('/dealers/schemes', { params });
    return data;
  },
};

// Dealer types for API
interface DealerCreditTransaction {
  id: string;
  dealer_id: string;
  transaction_type: string;
  transaction_date: string;
  reference_type: string;
  reference_number: string;
  debit_amount: number;
  credit_amount: number;
  balance: number;
  payment_mode?: string;
  narration?: string;
  created_at: string;
}

interface DealerTarget {
  id: string;
  dealer_id: string;
  target_period: string;
  target_year: number;
  target_month?: number;
  target_quarter?: number;
  revenue_target: number;
  quantity_target: number;
  revenue_achieved: number;
  quantity_achieved: number;
  revenue_achievement_percentage: number;
  quantity_achievement_percentage: number;
  incentive_earned: number;
  is_incentive_paid: boolean;
  created_at: string;
}

interface DealerScheme {
  id: string;
  scheme_code: string;
  scheme_name: string;
  description?: string;
  scheme_type: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  rules: Record<string, unknown>;
  total_budget?: number;
  utilized_budget: number;
}

// DMS (Distribution Management System) API
export const dmsApi = {
  getDashboard: async () => {
    const { data } = await apiClient.get('/dealers/dms/dashboard');
    return data;
  },
  listOrders: async (params?: { page?: number; size?: number; dealer_id?: string; status?: string; date_from?: string; date_to?: string }) => {
    const { data } = await apiClient.get('/dealers/dms/orders', { params });
    return data;
  },
  getOrder: async (orderId: string) => {
    const { data } = await apiClient.get(`/dealers/dms/orders/${orderId}`);
    return data;
  },
  createOrder: async (dealerId: string, order: { items: Array<{ product_id: string; variant_id?: string; quantity: number }>; notes?: string; payment_terms?: string }) => {
    const { data } = await apiClient.post(`/dealers/${dealerId}/orders`, order);
    return data;
  },
};

// Dashboard API - aggregates data from multiple real endpoints
export const dashboardApi = {
  getStats: async () => {
    // Aggregate stats from multiple real endpoints
    const [ordersRes, productsRes, inventoryRes, serviceRes] = await Promise.allSettled([
      apiClient.get('/orders/stats'),
      apiClient.get('/products/stats'),
      apiClient.get('/inventory/stats'),
      apiClient.get('/service-requests/stats'),
    ]);

    // Log any failed requests for debugging
    if (ordersRes.status === 'rejected') console.warn('Orders stats failed:', ordersRes.reason);
    if (productsRes.status === 'rejected') console.warn('Products stats failed:', productsRes.reason);
    if (inventoryRes.status === 'rejected') console.warn('Inventory stats failed:', inventoryRes.reason);
    if (serviceRes.status === 'rejected') console.warn('Service stats failed:', serviceRes.reason);

    const ordersData = ordersRes.status === 'fulfilled' ? ordersRes.value.data : {};
    const productsData = productsRes.status === 'fulfilled' ? productsRes.value.data : {};
    const inventoryData = inventoryRes.status === 'fulfilled' ? inventoryRes.value.data : {};
    const serviceData = serviceRes.status === 'fulfilled' ? serviceRes.value.data : {};

    return {
      total_orders: ordersData.total_orders || ordersData.total || 0,
      total_revenue: ordersData.total_revenue || 0,
      pending_orders: ordersData.pending_orders || ordersData.pending || 0,
      total_products: productsData.total_products || productsData.total || 0,
      total_customers: ordersData.total_customers || 0,
      low_stock_items: inventoryData.low_stock || inventoryData.low_stock_count || 0,
      pending_service_requests: serviceData.pending_requests || serviceData.pending || 0,
      shipments_in_transit: ordersData.shipments_in_transit || ordersData.in_transit || 0,
      orders_change: ordersData.orders_change || ordersData.change_percent || 0,
      revenue_change: ordersData.revenue_change || ordersData.revenue_change_percent || 0,
      customers_change: ordersData.customers_change || ordersData.customers_change_percent || 0,
      // Include error flags so UI can show warnings
      _errors: {
        orders: ordersRes.status === 'rejected',
        products: productsRes.status === 'rejected',
        inventory: inventoryRes.status === 'rejected',
        service: serviceRes.status === 'rejected',
      },
    };
  },
  getOrderStats: async () => {
    const { data } = await apiClient.get('/orders/stats');
    return data;
  },
  getRevenueStats: async () => {
    const { data } = await apiClient.get('/orders/stats');
    return data;
  },
  getRecentActivity: async (limit: number = 10) => {
    try {
      const { data } = await apiClient.get(`/orders/recent-activity?limit=${limit}`);
      return data.items || [];
    } catch (error) {
      console.warn('Recent activity endpoint not available:', error);
      return [];
    }
  },
  getTopSellingProducts: async (limit: number = 5) => {
    try {
      const { data } = await apiClient.get(`/products/top-selling?limit=${limit}`);
      return data.items || [];
    } catch (error) {
      console.warn('Top selling products endpoint not available:', error);
      return [];
    }
  },
  getSalesTrend: async (days: number = 7) => {
    try {
      const { data } = await apiClient.get(`/dashboard/sales/trend?days=${days}`);
      // API returns { labels: [], orders: [], revenue: [] } — transform to array format
      if (data.labels && Array.isArray(data.labels)) {
        return data.labels.map((label: string, i: number) => ({
          date: new Date(label).toLocaleDateString('en-US', { month: 'short', day: '2-digit' }),
          revenue: data.revenue?.[i] || 0,
          orders: data.orders?.[i] || 0,
        }));
      }
      return data.items || data.trend || data || [];
    } catch (error) {
      console.warn('Sales trend endpoint not available:', error);
      return [];
    }
  },
  getOrderStatusDistribution: async () => {
    try {
      const { data } = await apiClient.get('/dashboard/orders/status-distribution');
      return data.items || data.distribution || data || [];
    } catch (error) {
      console.warn('Order status distribution endpoint not available:', error);
      return [];
    }
  },
  getCategorySales: async (limit: number = 5) => {
    try {
      const { data } = await apiClient.get(`/dashboard/categories/sales?limit=${limit}`);
      return data.items || data.categories || data || [];
    } catch (error) {
      console.warn('Category sales endpoint not available:', error);
      return [];
    }
  },
};

// Approvals API
export const approvalsApi = {
  getPending: async () => {
    try {
      const { data } = await apiClient.get('/approvals/pending');
      return data;
    } catch (error) {
      // Return empty with error flag for 404 (endpoint may not exist yet)
      if ((error as { response?: { status?: number } })?.response?.status === 404) {
        console.warn('Approvals pending endpoint not available');
        return { items: [], total: 0, _notAvailable: true };
      }
      console.error('Failed to fetch pending approvals:', error);
      throw error;
    }
  },
  getDashboard: async () => {
    try {
      const { data } = await apiClient.get('/approvals/dashboard');
      return data;
    } catch (error) {
      // Return defaults with error flag for 404
      if ((error as { response?: { status?: number } })?.response?.status === 404) {
        console.warn('Approvals dashboard endpoint not available');
        return { pending: 0, approved: 0, rejected: 0, _notAvailable: true };
      }
      console.error('Failed to fetch approvals dashboard:', error);
      throw error;
    }
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/approvals/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/approvals/${id}/reject`, { reason });
    return data;
  },
};

// Audit Logs API
export const auditLogsApi = {
  list: async (params?: { page?: number; size?: number; entity_type?: string; user_id?: string; action?: string }) => {
    try {
      // Try the dedicated audit logs endpoint first
      const { data } = await apiClient.get('/audit-logs', { params });
      return data;
    } catch (error) {
      // Fallback to access-control activity logs if audit-logs doesn't exist
      if ((error as { response?: { status?: number } })?.response?.status === 404) {
        try {
          const { data } = await apiClient.get('/access-control/access/user-access-summary', { params });
          return { items: data.activity || [], total: data.activity?.length || 0, pages: 1 };
        } catch (fallbackError) {
          console.warn('Audit logs endpoints not available:', fallbackError);
          return { items: [], total: 0, pages: 0, _notAvailable: true };
        }
      }
      console.error('Failed to fetch audit logs:', error);
      throw error;
    }
  },
};

// WMS Zones API
export const zonesApi = {
  list: async (params?: { page?: number; size?: number; warehouse_id?: string }) => {
    const { data } = await apiClient.get('/wms/zones', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/wms/zones/${id}`);
    return data;
  },
  create: async (zone: { name: string; code: string; warehouse_id: string; zone_type?: string; description?: string; is_active?: boolean }) => {
    const { data } = await apiClient.post('/wms/zones', zone);
    return data;
  },
  update: async (id: string, zone: Partial<{ name: string; code: string; zone_type?: string; description?: string; is_active?: boolean }>) => {
    const { data } = await apiClient.put(`/wms/zones/${id}`, zone);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/wms/zones/${id}`);
  },
};

// WMS Bins API
export const binsApi = {
  list: async (params?: { page?: number; size?: number; warehouse_id?: string; zone_id?: string }) => {
    const { data } = await apiClient.get('/wms/bins', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/wms/bins/${id}`);
    return data;
  },
  create: async (bin: { name: string; code: string; zone_id: string; aisle?: string; rack?: string; level?: string; position?: string; capacity?: number; is_active?: boolean }) => {
    const { data } = await apiClient.post('/wms/bins', bin);
    return data;
  },
  bulkCreate: async (data: { zone_id: string; prefix: string; aisles: number; racks_per_aisle: number; levels_per_rack: number; positions_per_level: number }) => {
    const { data: response } = await apiClient.post('/wms/bins/bulk', data);
    return response;
  },
  update: async (id: string, bin: Partial<{ name: string; code: string; aisle?: string; rack?: string; level?: string; position?: string; capacity?: number; is_active?: boolean }>) => {
    const { data } = await apiClient.put(`/wms/bins/${id}`, bin);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/wms/bins/${id}`);
  },
  enquiry: async (binCode: string) => {
    const { data } = await apiClient.get(`/wms/bins/enquiry/${binCode}`);
    return data;
  },
};

// Transporters API
export const transportersApi = {
  list: async (params?: { page?: number; size?: number; is_active?: boolean }) => {
    const { data } = await apiClient.get('/transporters', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/transporters/${id}`);
    return data;
  },
  create: async (transporter: { name: string; code: string; transporter_type?: string; contact_name?: string; contact_phone?: string; contact_email?: string; address?: string; tracking_url_template?: string; is_active?: boolean }) => {
    const { data } = await apiClient.post('/transporters', transporter);
    return data;
  },
  update: async (id: string, transporter: Partial<{ name: string; code: string; transporter_type?: string; contact_name?: string; contact_phone?: string; contact_email?: string; address?: string; tracking_url_template?: string; is_active?: boolean }>) => {
    const { data } = await apiClient.put(`/transporters/${id}`, transporter);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/transporters/${id}`);
  },
};

// Shipments API
export const shipmentsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; transporter_id?: string; warehouse_id?: string; order_id?: string }) => {
    const { data } = await apiClient.get('/shipments', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/shipments/${id}`);
    return data;
  },
  create: async (shipment: { order_id: string; warehouse_id: string; transporter_id?: string; ship_to_name: string; ship_to_phone: string; ship_to_address: string; ship_to_city: string; ship_to_state: string; ship_to_pincode: string; weight_kg?: number; no_of_boxes?: number }) => {
    const { data } = await apiClient.post('/shipments', shipment);
    return data;
  },
  update: async (id: string, shipment: Partial<{ transporter_id?: string; awb_number?: string; expected_delivery_date?: string }>) => {
    const { data } = await apiClient.put(`/shipments/${id}`, shipment);
    return data;
  },
  updateStatus: async (id: string, status: string, remarks?: string) => {
    const { data } = await apiClient.put(`/shipments/${id}/status`, { status, remarks });
    return data;
  },
  addTracking: async (id: string, tracking: { status: string; location?: string; remarks?: string; event_time?: string }) => {
    const { data } = await apiClient.post(`/shipments/${id}/tracking`, tracking);
    return data;
  },
  getTracking: async (id: string) => {
    const { data } = await apiClient.get(`/shipments/${id}/tracking`);
    return data;
  },
  markDelivered: async (id: string, podData?: { receiver_name?: string; receiver_phone?: string; pod_image_url?: string; delivery_notes?: string }) => {
    const { data } = await apiClient.post(`/shipments/${id}/deliver`, podData);
    return data;
  },
  initiateRTO: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/shipments/${id}/rto`, { reason });
    return data;
  },
  getSlaDashboard: async () => {
    const { data } = await apiClient.get('/shipments/sla/dashboard');
    return data;
  },
  getAtRiskShipments: async (daysThreshold?: number) => {
    const { data } = await apiClient.get('/shipments/sla/at-risk', { params: { days_threshold: daysThreshold } });
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/shipments/${id}`);
  },
  downloadLabel: async (id: string) => {
    const { data } = await apiClient.get<string>(`/shipments/${id}/label/download`);
    return data;
  },
  downloadInvoice: async (id: string) => {
    const { data } = await apiClient.get<string>(`/shipments/${id}/invoice/download`);
    return data;
  },
  // E-Way Bill Integration
  generateEwayBill: async (id: string, ewayBillData: {
    transporter_id?: string;
    transporter_name?: string;
    transporter_gstin?: string;
    vehicle_number?: string;
    vehicle_type?: string;
    transport_mode?: string;
    distance_km?: number;
  }) => {
    const { data } = await apiClient.post(`/shipments/${id}/generate-eway-bill`, ewayBillData);
    return data;
  },
  updateEwayBillVehicle: async (id: string, vehicleData: {
    vehicle_number: string;
    vehicle_type?: string;
    reason?: string;
  }) => {
    const { data } = await apiClient.post(`/shipments/${id}/update-eway-bill-vehicle`, vehicleData);
    return data;
  },
  getEwayBillStatus: async (id: string) => {
    const { data } = await apiClient.get(`/shipments/${id}/eway-bill-status`);
    return data;
  },
};

// Manifests API
export const manifestsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; warehouse_id?: string; transporter_id?: string }) => {
    const { data } = await apiClient.get('/manifests', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/manifests/${id}`);
    return data;
  },
  create: async (manifest: { warehouse_id: string; transporter_id: string; business_type?: string; manifest_date?: string; vehicle_number?: string; driver_name?: string; driver_phone?: string; remarks?: string }) => {
    const { data } = await apiClient.post('/manifests', manifest);
    return data;
  },
  update: async (id: string, manifest: Partial<{ vehicle_number?: string; driver_name?: string; driver_phone?: string; remarks?: string }>) => {
    const { data } = await apiClient.put(`/manifests/${id}`, manifest);
    return data;
  },
  addShipments: async (id: string, shipmentIds: string[]) => {
    const { data } = await apiClient.post(`/manifests/${id}/add-shipments`, { shipment_ids: shipmentIds });
    return data;
  },
  removeShipments: async (id: string, shipmentIds: string[]) => {
    const { data } = await apiClient.post(`/manifests/${id}/remove-shipments`, { shipment_ids: shipmentIds });
    return data;
  },
  scan: async (id: string, scanData: { awb_number?: string; shipment_id?: string; barcode?: string }) => {
    const { data } = await apiClient.post(`/manifests/${id}/scan`, scanData);
    return data;
  },
  confirm: async (id: string, confirmData?: { vehicle_number?: string; driver_name?: string; driver_phone?: string; remarks?: string }) => {
    const { data } = await apiClient.post(`/manifests/${id}/confirm`, confirmData);
    return data;
  },
  handover: async (id: string, handoverRemarks?: string) => {
    const { data } = await apiClient.post(`/manifests/${id}/handover`, { handover_remarks: handoverRemarks });
    return data;
  },
  cancel: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/manifests/${id}/cancel`, { reason });
    return data;
  },
  getPrintData: async (id: string) => {
    const { data } = await apiClient.get(`/manifests/${id}/print`);
    return data;
  },
};

// Stock Transfers API
export const transfersApi = {
  list: async (params?: { page?: number; size?: number; status?: string; from_warehouse_id?: string; to_warehouse_id?: string }) => {
    const { data } = await apiClient.get('/transfers', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/transfers/${id}`);
    return data;
  },
  create: async (transfer: { from_warehouse_id: string; to_warehouse_id: string; items: { product_id: string; quantity: number }[]; notes?: string }) => {
    const { data } = await apiClient.post('/transfers', transfer);
    return data;
  },
  submit: async (id: string) => {
    const { data } = await apiClient.post(`/transfers/${id}/submit`);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/transfers/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/transfers/${id}/reject`, { reason });
    return data;
  },
  ship: async (id: string) => {
    const { data } = await apiClient.post(`/transfers/${id}/ship`);
    return data;
  },
  receive: async (id: string, items?: { stock_item_id: string; received_quantity: number }[]) => {
    const { data } = await apiClient.post(`/transfers/${id}/receive`, { items });
    return data;
  },
};

// ============================================
// FINANCE / ACCOUNTING API
// ============================================

// Chart of Accounts API
export const accountsApi = {
  list: async (params?: { page?: number; size?: number; type?: string; is_active?: boolean }) => {
    const { data } = await apiClient.get('/accounting/accounts', { params });
    return data;
  },
  getTree: async () => {
    const { data } = await apiClient.get('/accounting/accounts/tree');
    return data;
  },
  getDropdown: async () => {
    const { data } = await apiClient.get('/accounting/accounts/dropdown');
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/accounting/accounts/${id}`);
    return data;
  },
  create: async (account: {
    code: string;
    name: string;
    type: string;
    account_sub_type?: string;
    parent_id?: string;
    description?: string;
    is_group?: boolean;
  }) => {
    const { data } = await apiClient.post('/accounting/accounts', account);
    return data;
  },
  update: async (id: string, account: Partial<{
    account_name?: string;
    description?: string;
    is_active?: boolean;
  }>) => {
    const { data } = await apiClient.put(`/accounting/accounts/${id}`, account);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/accounting/accounts/${id}`);
  },
};

// Financial Periods API
export const periodsApi = {
  list: async (params?: { page?: number; size?: number; year_id?: string }) => {
    const { data } = await apiClient.get('/accounting/periods', { params });
    return data;
  },
  listPeriods: async (yearId?: string) => {
    const { data } = await apiClient.get('/accounting/periods', { params: { year_id: yearId } });
    return data;
  },
  listYears: async () => {
    const { data } = await apiClient.get('/accounting/fiscal-years');
    return data;
  },
  getCurrent: async () => {
    const { data } = await apiClient.get('/accounting/periods/current');
    return data;
  },
  create: async (period: { name: string; code: string; financial_year: string; period_type: string; start_date: string; end_date: string }) => {
    const { data } = await apiClient.post('/accounting/periods', period);
    return data;
  },
  createYear: async (year: { name: string; code?: string; start_date: string; end_date: string }) => {
    const { data } = await apiClient.post('/accounting/fiscal-years', year);
    return data;
  },
  close: async (id: string) => {
    const { data } = await apiClient.post(`/accounting/periods/${id}/close`);
    return data;
  },
  closePeriod: async (id: string) => {
    const { data } = await apiClient.post(`/accounting/periods/${id}/close`);
    return data;
  },
  reopenPeriod: async (id: string) => {
    const { data } = await apiClient.post(`/accounting/periods/${id}/reopen`);
    return data;
  },
  lockPeriod: async (id: string) => {
    const { data } = await apiClient.post(`/accounting/periods/${id}/lock`);
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/accounting/periods/${id}`);
    return data;
  },
  update: async (id: string, period: { status?: string }) => {
    const { data } = await apiClient.put(`/accounting/periods/${id}`, period);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/accounting/periods/${id}`);
  },
};

// Cost Centers API
export const costCentersApi = {
  list: async (params?: { page?: number; size?: number; is_active?: boolean }) => {
    const { data } = await apiClient.get('/accounting/cost-centers', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/accounting/cost-centers/${id}`);
    return data;
  },
  create: async (costCenter: {
    code: string;
    name: string;
    cost_center_type: string;
    parent_id?: string;
    description?: string;
    annual_budget?: number;
  }) => {
    const { data } = await apiClient.post('/accounting/cost-centers', costCenter);
    return data;
  },
  update: async (id: string, costCenter: Partial<{
    name: string;
    description?: string;
    annual_budget?: number;
    is_active?: boolean;
  }>) => {
    const { data } = await apiClient.put(`/accounting/cost-centers/${id}`, costCenter);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/accounting/cost-centers/${id}`);
  },
};

// Journal Entries API
// Valid entry types for journal entries
const JOURNAL_ENTRY_TYPES = ['MANUAL', 'SALES', 'PURCHASE', 'RECEIPT', 'PAYMENT', 'ADJUSTMENT', 'CLOSING'];

export const journalEntriesApi = {
  list: async (params?: { page?: number; size?: number; status?: string }) => {
    const { data } = await apiClient.get('/accounting/journals', { params });
    return data;
  },
  getPendingApproval: async () => {
    const { data } = await apiClient.get('/accounting/journals/pending-approval');
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/accounting/journals/${id}`);
    return data;
  },
  create: async (entry: {
    entry_date: string;
    narration: string;
    entry_type?: string;
    source_type?: string;
    source_number?: string;
    lines: { account_id: string; debit?: number; credit?: number; debit_amount?: number; credit_amount?: number; description?: string; narration?: string }[]
  }) => {
    // Backend expects: entry_type (required), entry_date, narration, lines
    // entry_type must be one of: MANUAL, SALES, PURCHASE, RECEIPT, PAYMENT, ADJUSTMENT, CLOSING
    const payload = {
      entry_type: JOURNAL_ENTRY_TYPES.includes(entry.entry_type || '') ? entry.entry_type : 'MANUAL',
      entry_date: entry.entry_date,
      narration: entry.narration,
      source_type: entry.source_type || undefined,
      source_number: entry.source_number || undefined,
      lines: entry.lines.map(l => ({
        account_id: l.account_id,
        debit_amount: l.debit ?? l.debit_amount ?? 0,
        credit_amount: l.credit ?? l.credit_amount ?? 0,
        description: l.narration ?? l.description,
      })),
    };
    const { data } = await apiClient.post('/accounting/journals', payload);
    return data;
  },
  submit: async (id: string, remarks?: string) => {
    // Backend expects JournalSubmitRequest body with optional remarks
    const { data } = await apiClient.post(`/accounting/journals/${id}/submit`, { remarks: remarks || null });
    return data;
  },
  approve: async (id: string, remarks?: string, autoPost: boolean = true) => {
    // Backend expects JournalApproveRequest body with optional remarks and auto_post
    const { data } = await apiClient.post(`/accounting/journals/${id}/approve`, { remarks: remarks || null, auto_post: autoPost });
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/accounting/journals/${id}/reject`, { reason });
    return data;
  },
  resubmit: async (id: string, remarks?: string) => {
    // Backend expects JournalSubmitRequest body with optional remarks
    const { data } = await apiClient.post(`/accounting/journals/${id}/resubmit`, { remarks: remarks || null });
    return data;
  },
  post: async (id: string) => {
    const { data } = await apiClient.post(`/accounting/journals/${id}/post`);
    return data;
  },
  reverse: async (id: string, reversal_date: string, reason: string) => {
    const { data } = await apiClient.post(`/accounting/journals/${id}/reverse`, { reversal_date, reason });
    return data;
  },
  update: async (id: string, entry: {
    entry_date?: string;
    narration?: string;
    source_number?: string;
    lines?: { account_id: string; debit_amount: number; credit_amount: number; description?: string }[];
  }) => {
    const { data } = await apiClient.put(`/accounting/journals/${id}`, entry);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/accounting/journals/${id}`);
  },
};

// General Ledger API
export const ledgerApi = {
  getAccountLedger: async (accountId: string, params?: { from_date?: string; to_date?: string; page?: number; size?: number }) => {
    const { data } = await apiClient.get(`/accounting/ledger/${accountId}`, { params });
    return data;
  },
};

// Financial Reports API
export const reportsApi = {
  getTrialBalance: async (params?: { as_of_date?: string; period_id?: string }) => {
    const { data } = await apiClient.get('/accounting/reports/trial-balance', { params });
    return data;
  },
  getBalanceSheet: async (params?: { as_of_date?: string; period_id?: string }) => {
    const { data } = await apiClient.get('/accounting/reports/balance-sheet', { params });
    return data;
  },
  getProfitLoss: async (params?: { from_date?: string; to_date?: string; period_id?: string }) => {
    const { data } = await apiClient.get('/accounting/reports/profit-loss', { params });
    return data;
  },
};

// Tax Configuration API (HSN-based GST configuration)
export const taxConfigApi = {
  list: async () => {
    const { data } = await apiClient.get('/accounting/tax-configs');
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/accounting/tax-configs/${id}`);
    return data;
  },
  create: async (config: {
    hsn_code: string;
    description: string;
    gst_rate: number;
    cgst_rate: number;
    sgst_rate: number;
    igst_rate: number;
    cess_rate?: number;
    is_service?: boolean;
    is_exempt?: boolean;
    is_nil_rated?: boolean;
    is_non_gst?: boolean;
    reverse_charge?: boolean;
    is_active?: boolean;
  }) => {
    const { data } = await apiClient.post('/accounting/tax-configs', config);
    return data;
  },
  update: async (id: string, config: Partial<{
    description?: string;
    gst_rate?: number;
    cgst_rate?: number;
    sgst_rate?: number;
    igst_rate?: number;
    cess_rate?: number;
    is_active?: boolean;
  }>) => {
    const { data } = await apiClient.put(`/accounting/tax-configs/${id}`, config);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/accounting/tax-configs/${id}`);
  },
};

// ============================================
// BILLING API
// ============================================

// Invoices API
export const invoicesApi = {
  list: async (params?: { page?: number; size?: number; status?: string; customer_id?: string }) => {
    const { data } = await apiClient.get('/billing/invoices', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/billing/invoices/${id}`);
    return data;
  },
  create: async (invoice: { customer_id: string; invoice_date: string; due_date: string; items: { product_id: string; quantity: number; unit_price: number; tax_rate: number }[]; notes?: string }) => {
    const { data } = await apiClient.post('/billing/invoices', invoice);
    return data;
  },
  generateIRN: async (id: string) => {
    const { data } = await apiClient.post(`/billing/invoices/${id}/generate-irn`);
    return data;
  },
  cancelIRN: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/billing/invoices/${id}/cancel-irn`, { reason });
    return data;
  },
  download: async (id: string) => {
    const { data } = await apiClient.get(`/billing/invoices/${id}/download`);
    return data;
  },
  print: async (id: string) => {
    const { data } = await apiClient.get(`/billing/invoices/${id}/print`);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/billing/invoices/${id}`);
  },
};

// Credit/Debit Notes API
export const creditDebitNotesApi = {
  list: async (params?: { page?: number; size?: number; type?: string; status?: string }) => {
    const { data } = await apiClient.get('/billing/credit-debit-notes', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/billing/credit-debit-notes/${id}`);
    return data;
  },
  create: async (note: { type: 'CREDIT' | 'DEBIT'; invoice_id?: string; customer_id: string; reason: string; credit_note_date?: string; subtotal?: number; tax_amount?: number; total_amount?: number; lines?: { description: string; quantity: number; unit_price: number; amount?: number; tax_rate?: number; tax_amount?: number }[]; items?: { description: string; quantity: number; unit_price: number; tax_rate?: number }[] }) => {
    const { data } = await apiClient.post('/billing/credit-debit-notes', note);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/billing/credit-debit-notes/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/billing/credit-debit-notes/${id}/reject`, { reason });
    return data;
  },
  apply: async (id: string, invoiceId: string) => {
    const { data } = await apiClient.post(`/billing/credit-debit-notes/${id}/apply`, { invoice_id: invoiceId });
    return data;
  },
  cancel: async (id: string) => {
    const { data } = await apiClient.post(`/billing/credit-debit-notes/${id}/cancel`);
    return data;
  },
  download: async (id: string) => {
    const { data } = await apiClient.get<string>(`/billing/credit-debit-notes/${id}/download`);
    return data;
  },
};

// E-Way Bills API
export const ewayBillsApi = {
  list: async (params?: { page?: number; size?: number; status?: string }) => {
    const { data } = await apiClient.get('/billing/eway-bills', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/billing/eway-bills/${id}`);
    return data;
  },
  create: async (ewb: { invoice_id: string; transporter_id?: string; vehicle_number?: string; distance_km: number }) => {
    const { data } = await apiClient.post('/billing/eway-bills', ewb);
    return data;
  },
  generate: async (ewbData: string | { invoice_id: string; from_gstin?: string; to_gstin?: string; from_place?: string; to_place?: string; transport_mode?: string; vehicle_type?: string; vehicle_number?: string; transporter_name?: string; distance_km?: number }) => {
    if (typeof ewbData === 'string') {
      const { data } = await apiClient.post(`/billing/eway-bills/${ewbData}/generate`);
      return data;
    } else {
      // Create and generate in one step
      const { data } = await apiClient.post('/billing/eway-bills/generate', ewbData);
      return data;
    }
  },
  updateVehicle: async (id: string, vehicleData: { vehicle_number: string; transporter_id?: string; reason?: string }) => {
    const { data } = await apiClient.put(`/billing/eway-bills/${id}/update-vehicle`, vehicleData);
    return data;
  },
  cancel: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/billing/eway-bills/${id}/cancel`, { reason });
    return data;
  },
  print: async (id: string) => {
    const { data } = await apiClient.get(`/billing/eway-bills/${id}/print`);
    return data;
  },
  extendValidity: async (id: string, extendData: { reason: string; from_place?: string; extend_by_km?: number }) => {
    const { data } = await apiClient.post(`/billing/eway-bills/${id}/extend`, extendData);
    return data;
  },
  download: async (id: string) => {
    const { data } = await apiClient.get<string>(`/billing/eway-bills/${id}/print`);
    return data;
  },
};

// Payment Receipts API
export const receiptsApi = {
  list: async (params?: { page?: number; size?: number; customer_id?: string }) => {
    const { data } = await apiClient.get('/billing/receipts', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/billing/receipts/${id}`);
    return data;
  },
  create: async (receipt: { customer_id: string; invoice_id?: string; amount: number; payment_mode: string; reference_number?: string; payment_date: string; notes?: string }) => {
    const { data } = await apiClient.post('/billing/receipts', receipt);
    return data;
  },
};

// ============================================
// PROCUREMENT API
// ============================================

// GRN (Goods Receipt Note) API
export const grnApi = {
  list: async (params?: { page?: number; size?: number; status?: string; po_id?: string; warehouse_id?: string }) => {
    const { data } = await apiClient.get('/purchase/grn', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/purchase/grn/${id}`);
    return data;
  },
  create: async (grn: {
    purchase_order_id: string;
    warehouse_id: string;
    grn_date: string;
    vendor_challan_number?: string;
    vendor_challan_date?: string;
    transporter_name?: string;
    vehicle_number?: string;
    lr_number?: string;
    e_way_bill_number?: string;
    qc_required?: boolean;
    receiving_remarks?: string;
    items: {
      po_item_id: string;
      product_id: string;
      variant_id?: string;
      product_name: string;
      sku: string;
      quantity_expected: number;
      quantity_received: number;
      quantity_accepted?: number;
      quantity_rejected?: number;
      uom?: string;
      batch_number?: string;
      serial_numbers?: string[];
      remarks?: string;
    }[];
  }) => {
    const { data } = await apiClient.post('/purchase/grn', grn);
    return data;
  },
  scanSerial: async (id: string, scanData: { serial_number: string }) => {
    const { data } = await apiClient.post(`/purchase/grn/${id}/scan`, scanData);
    return data;
  },
  addItem: async (id: string, item: { product_id: string; received_quantity: number; rejected_quantity?: number; rejection_reason?: string }) => {
    const { data } = await apiClient.post(`/purchase/grn/${id}/items`, item);
    return data;
  },
  updateItem: async (id: string, itemId: string, item: { received_quantity?: number; rejected_quantity?: number; rejection_reason?: string; qc_status?: string }) => {
    const { data } = await apiClient.put(`/purchase/grn/${id}/items/${itemId}`, item);
    return data;
  },
  complete: async (id: string) => {
    const { data } = await apiClient.post(`/purchase/grn/${id}/complete`);
    return data;
  },
  cancel: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/purchase/grn/${id}/cancel`, { reason });
    return data;
  },
  getSerials: async (id: string) => {
    const { data } = await apiClient.get(`/purchase/grn/${id}/serials`);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/purchase/grn/${id}`);
  },
  download: async (id: string) => {
    const { data } = await apiClient.get<string>(`/purchase/grn/${id}/download`);
    return data;
  },
};

// Sales Return Notes (SRN) API
export const srnApi = {
  getNextNumber: async () => {
    const { data } = await apiClient.get('/purchase/srn/next-number');
    return data;
  },
  list: async (params?: {
    page?: number;
    size?: number;
    status?: string;
    customer_id?: string;
    order_id?: string;
    warehouse_id?: string;
    return_reason?: string;
    pickup_status?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
  }) => {
    const { data } = await apiClient.get('/purchase/srn', { params });
    return data;
  },
  listPendingPickups: async (params?: { page?: number; size?: number }) => {
    const { data } = await apiClient.get('/purchase/srn/pending-pickups', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/purchase/srn/${id}`);
    return data;
  },
  create: async (srn: {
    srn_date: string;
    order_id?: string;
    invoice_id?: string;
    customer_id: string;
    warehouse_id: string;
    return_reason: string;
    return_reason_detail?: string;
    resolution_type?: string;
    pickup_required?: boolean;
    pickup_scheduled_date?: string;
    pickup_address?: Record<string, unknown>;
    pickup_contact_name?: string;
    pickup_contact_phone?: string;
    qc_required?: boolean;
    receiving_remarks?: string;
    items: {
      order_item_id?: string;
      invoice_item_id?: string;
      product_id: string;
      variant_id?: string;
      product_name: string;
      sku: string;
      hsn_code?: string;
      serial_numbers?: string[];
      quantity_sold: number;
      quantity_returned: number;
      unit_price: number;
      uom?: string;
      remarks?: string;
    }[];
  }) => {
    const { data } = await apiClient.post('/purchase/srn', srn);
    return data;
  },
  schedulePickup: async (id: string, request: {
    pickup_date: string;
    pickup_slot?: string;
    pickup_address?: Record<string, unknown>;
    pickup_contact_name?: string;
    pickup_contact_phone?: string;
    courier_id?: string;
  }) => {
    const { data } = await apiClient.post(`/purchase/srn/${id}/schedule-pickup`, request);
    return data;
  },
  updatePickup: async (id: string, request: {
    pickup_status?: string;
    courier_id?: string;
    courier_name?: string;
    courier_tracking_number?: string;
  }) => {
    const { data } = await apiClient.post(`/purchase/srn/${id}/update-pickup`, request);
    return data;
  },
  receive: async (id: string, request: {
    receiving_remarks?: string;
    photos_urls?: string[];
  }) => {
    const { data } = await apiClient.post(`/purchase/srn/${id}/receive`, request);
    return data;
  },
  processQC: async (id: string, request: {
    item_results: {
      item_id: string;
      qc_result?: string;
      item_condition?: string;
      restock_decision?: string;
      quantity_accepted?: number;
      quantity_rejected?: number;
      rejection_reason?: string;
    }[];
    overall_remarks?: string;
  }) => {
    const { data } = await apiClient.post(`/purchase/srn/${id}/qc`, request);
    return data;
  },
  processPutaway: async (id: string, request: {
    item_locations: {
      item_id: string;
      bin_id?: string;
      bin_location?: string;
    }[];
  }) => {
    const { data } = await apiClient.post(`/purchase/srn/${id}/putaway`, request);
    return data;
  },
  resolve: async (id: string, request: {
    resolution_type: string;
    notes?: string;
  }) => {
    const { data } = await apiClient.post(`/purchase/srn/${id}/resolve`, request);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/purchase/srn/${id}`);
  },
  download: async (id: string) => {
    const { data } = await apiClient.get<string>(`/purchase/srn/${id}/download`);
    return data;
  },
};

// Vendor Proformas API
export const vendorProformasApi = {
  list: async (params?: { page?: number; size?: number; status?: string; vendor_id?: string }) => {
    const { data } = await apiClient.get('/purchase/vendor-proformas', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/purchase/vendor-proformas/${id}`);
    return data;
  },
  create: async (proforma: { vendor_id: string; proforma_number: string; proforma_date: string; due_date: string; items: { product_id: string; quantity: number; unit_price: number; gst_rate: number }[]; notes?: string }) => {
    const { data } = await apiClient.post('/purchase/vendor-proformas', proforma);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/purchase/vendor-proformas/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/purchase/vendor-proformas/${id}/reject`, { reason });
    return data;
  },
  convertToPO: async (id: string) => {
    const { data } = await apiClient.post(`/purchase/vendor-proformas/${id}/convert-to-po`);
    return data;
  },
};

// Vendor Invoices API
export const vendorInvoicesApi = {
  list: async (params?: { page?: number; size?: number; status?: string; vendor_id?: string }) => {
    const { data } = await apiClient.get('/purchase/vendor-invoices', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/purchase/vendor-invoices/${id}`);
    return data;
  },
  create: async (invoice: { vendor_id: string; po_id: string; grn_id: string; invoice_number: string; invoice_date: string; due_date: string; items: { grn_item_id: string; quantity: number; unit_price: number; gst_rate: number }[]; notes?: string }) => {
    const { data } = await apiClient.post('/purchase/vendor-invoices', invoice);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/purchase/vendor-invoices/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/purchase/vendor-invoices/${id}/reject`, { reason });
    return data;
  },
  markPaid: async (id: string, paymentData: { payment_date: string; payment_reference: string; payment_mode: string }) => {
    const { data } = await apiClient.post(`/purchase/vendor-invoices/${id}/mark-paid`, paymentData);
    return data;
  },
};

// Three-Way Match API
export const threeWayMatchApi = {
  list: async (params?: { page?: number; size?: number; status?: string }) => {
    const { data } = await apiClient.get('/purchase/three-way-match', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/purchase/three-way-match/${id}`);
    return data;
  },
  match: async (matchData: { po_id: string; grn_id: string; vendor_invoice_id: string }) => {
    const { data } = await apiClient.post('/purchase/three-way-match', matchData);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/purchase/three-way-match/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/purchase/three-way-match/${id}/reject`, { reason });
    return data;
  },
};

// ============================================
// LOGISTICS API
// ============================================

// Rate Cards API - D2C (Direct to Consumer)
export const rateCardsApi = {
  // Legacy API compatibility (uses D2C as default)
  list: async (params?: { page?: number; size?: number; transporter_id?: string; is_active?: boolean; service_type?: string }) => {
    const { data } = await apiClient.get('/rate-cards/d2c', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/rate-cards/d2c/${id}`);
    return data;
  },
  create: async (rateCard: Record<string, unknown>) => {
    const { data } = await apiClient.post('/rate-cards/d2c', rateCard);
    return data;
  },
  update: async (id: string, rateCard: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/rate-cards/d2c/${id}`, rateCard);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/rate-cards/d2c/${id}`);
  },
  calculate: async (params: { origin_pincode: string; destination_pincode: string; weight_kg: number; payment_mode?: string; order_value?: number }) => {
    const { data } = await apiClient.post('/rate-cards/calculate', params);
    return data;
  },

  // D2C Rate Cards (Courier Partners)
  d2c: {
    list: async (params?: { page?: number; size?: number; transporter_id?: string; service_type?: string; is_active?: boolean; effective_date?: string }) => {
      const { data } = await apiClient.get('/rate-cards/d2c', { params });
      return data;
    },
    getById: async (id: string) => {
      const { data } = await apiClient.get(`/rate-cards/d2c/${id}`);
      return data;
    },
    create: async (rateCard: Record<string, unknown>) => {
      const { data } = await apiClient.post('/rate-cards/d2c', rateCard);
      return data;
    },
    update: async (id: string, rateCard: Record<string, unknown>) => {
      const { data } = await apiClient.put(`/rate-cards/d2c/${id}`, rateCard);
      return data;
    },
    delete: async (id: string, hardDelete?: boolean) => {
      await apiClient.delete(`/rate-cards/d2c/${id}`, { params: { hard_delete: hardDelete } });
    },
    addSlab: async (rateCardId: string, slab: Record<string, unknown>) => {
      const { data } = await apiClient.post(`/rate-cards/d2c/${rateCardId}/slabs`, slab);
      return data;
    },
    bulkAddSlabs: async (rateCardId: string, slabs: Record<string, unknown>[], replaceExisting?: boolean) => {
      const { data } = await apiClient.post(`/rate-cards/d2c/${rateCardId}/slabs/bulk`, { slabs }, { params: { replace_existing: replaceExisting } });
      return data;
    },
    deleteSlab: async (rateCardId: string, slabId: string) => {
      await apiClient.delete(`/rate-cards/d2c/${rateCardId}/slabs/${slabId}`);
    },
    addSurcharge: async (rateCardId: string, surcharge: Record<string, unknown>) => {
      const { data } = await apiClient.post(`/rate-cards/d2c/${rateCardId}/surcharges`, surcharge);
      return data;
    },
    bulkAddSurcharges: async (rateCardId: string, surcharges: Record<string, unknown>[], replaceExisting?: boolean) => {
      const { data } = await apiClient.post(`/rate-cards/d2c/${rateCardId}/surcharges/bulk`, { surcharges }, { params: { replace_existing: replaceExisting } });
      return data;
    },
    deleteSurcharge: async (rateCardId: string, surchargeId: string) => {
      await apiClient.delete(`/rate-cards/d2c/${rateCardId}/surcharges/${surchargeId}`);
    },
  },

  // B2B Rate Cards (LTL/PTL)
  b2b: {
    list: async (params?: { page?: number; size?: number; transporter_id?: string; service_type?: string; is_active?: boolean }) => {
      const { data } = await apiClient.get('/rate-cards/b2b', { params });
      return data;
    },
    getById: async (id: string) => {
      const { data } = await apiClient.get(`/rate-cards/b2b/${id}`);
      return data;
    },
    create: async (rateCard: Record<string, unknown>) => {
      const { data } = await apiClient.post('/rate-cards/b2b', rateCard);
      return data;
    },
    update: async (id: string, rateCard: Record<string, unknown>) => {
      const { data } = await apiClient.put(`/rate-cards/b2b/${id}`, rateCard);
      return data;
    },
    delete: async (id: string, hardDelete?: boolean) => {
      await apiClient.delete(`/rate-cards/b2b/${id}`, { params: { hard_delete: hardDelete } });
    },
    addSlab: async (rateCardId: string, slab: Record<string, unknown>) => {
      const { data } = await apiClient.post(`/rate-cards/b2b/${rateCardId}/slabs`, slab);
      return data;
    },
    bulkAddSlabs: async (rateCardId: string, slabs: Record<string, unknown>[], replaceExisting?: boolean) => {
      const { data } = await apiClient.post(`/rate-cards/b2b/${rateCardId}/slabs/bulk`, { slabs }, { params: { replace_existing: replaceExisting } });
      return data;
    },
    deleteSlab: async (rateCardId: string, slabId: string) => {
      await apiClient.delete(`/rate-cards/b2b/${rateCardId}/slabs/${slabId}`);
    },
  },

  // FTL Rate Cards (Full Truck Load)
  ftl: {
    list: async (params?: { page?: number; size?: number; transporter_id?: string; rate_type?: string; is_active?: boolean }) => {
      const { data } = await apiClient.get('/rate-cards/ftl', { params });
      return data;
    },
    getById: async (id: string) => {
      const { data } = await apiClient.get(`/rate-cards/ftl/${id}`);
      return data;
    },
    create: async (rateCard: Record<string, unknown>) => {
      const { data } = await apiClient.post('/rate-cards/ftl', rateCard);
      return data;
    },
    update: async (id: string, rateCard: Record<string, unknown>) => {
      const { data } = await apiClient.put(`/rate-cards/ftl/${id}`, rateCard);
      return data;
    },
    delete: async (id: string, hardDelete?: boolean) => {
      await apiClient.delete(`/rate-cards/ftl/${id}`, { params: { hard_delete: hardDelete } });
    },
    addLane: async (rateCardId: string, lane: Record<string, unknown>) => {
      const { data } = await apiClient.post(`/rate-cards/ftl/${rateCardId}/lanes`, lane);
      return data;
    },
    bulkAddLanes: async (rateCardId: string, laneRates: Record<string, unknown>[], replaceExisting?: boolean) => {
      const { data } = await apiClient.post(`/rate-cards/ftl/${rateCardId}/lanes/bulk`, { lane_rates: laneRates }, { params: { replace_existing: replaceExisting } });
      return data;
    },
    deleteLane: async (rateCardId: string, laneId: string) => {
      await apiClient.delete(`/rate-cards/ftl/${rateCardId}/lanes/${laneId}`);
    },
    searchLanes: async (params?: { origin_city?: string; destination_city?: string; vehicle_type?: string; rate_card_id?: string; page?: number; size?: number }) => {
      const { data } = await apiClient.get('/rate-cards/ftl/lanes/search', { params });
      return data;
    },
  },

  // Zone Mappings
  zones: {
    list: async (params?: { page?: number; size?: number; origin_state?: string; destination_state?: string; zone?: string }) => {
      const { data } = await apiClient.get('/rate-cards/zones', { params });
      return data;
    },
    lookup: async (originPincode: string, destinationPincode: string) => {
      const { data } = await apiClient.get('/rate-cards/zones/lookup', { params: { origin_pincode: originPincode, destination_pincode: destinationPincode } });
      return data;
    },
    create: async (mapping: Record<string, unknown>) => {
      const { data } = await apiClient.post('/rate-cards/zones', mapping);
      return data;
    },
    bulkCreate: async (mappings: Record<string, unknown>[], skipDuplicates?: boolean) => {
      const { data } = await apiClient.post('/rate-cards/zones/bulk', { mappings }, { params: { skip_duplicates: skipDuplicates } });
      return data;
    },
    delete: async (id: string) => {
      await apiClient.delete(`/rate-cards/zones/${id}`);
    },
  },

  // Vehicle Types (FTL)
  vehicleTypes: {
    list: async (params?: { page?: number; size?: number; category?: string; is_active?: boolean }) => {
      const { data } = await apiClient.get('/rate-cards/vehicle-types', { params });
      return data;
    },
    getById: async (id: string) => {
      const { data } = await apiClient.get(`/rate-cards/vehicle-types/${id}`);
      return data;
    },
    create: async (vehicleType: Record<string, unknown>) => {
      const { data } = await apiClient.post('/rate-cards/vehicle-types', vehicleType);
      return data;
    },
    update: async (id: string, vehicleType: Record<string, unknown>) => {
      const { data } = await apiClient.put(`/rate-cards/vehicle-types/${id}`, vehicleType);
      return data;
    },
    delete: async (id: string) => {
      await apiClient.delete(`/rate-cards/vehicle-types/${id}`);
    },
  },

  // Carrier Performance
  performance: {
    list: async (params?: { page?: number; size?: number; transporter_id?: string; zone?: string; period_start?: string }) => {
      const { data } = await apiClient.get('/rate-cards/carriers/performance', { params });
      return data;
    },
    getByCarrier: async (transporterId: string, params?: { period_start?: string; period_end?: string; zone?: string }) => {
      const { data } = await apiClient.get(`/rate-cards/carriers/${transporterId}/performance`, { params });
      return data;
    },
  },

  // Summary
  summary: async (transporterId?: string) => {
    const { data } = await apiClient.get('/rate-cards/summary', { params: { transporter_id: transporterId } });
    return data;
  },
  dropdown: async (segment: 'd2c' | 'b2b' | 'ftl', transporterId?: string, isActive?: boolean) => {
    const { data } = await apiClient.get('/rate-cards/dropdown', { params: { segment, transporter_id: transporterId, is_active: isActive } });
    return data;
  },

  // Pricing Engine
  pricing: {
    calculateRate: async (params: {
      origin_pincode: string;
      destination_pincode: string;
      weight_kg: number;
      length_cm?: number;
      width_cm?: number;
      height_cm?: number;
      payment_mode?: 'PREPAID' | 'COD';
      order_value?: number;
      channel?: string;
      declared_value?: number;
      is_fragile?: boolean;
      num_packages?: number;
      service_type?: string;
      transporter_ids?: string[];
    }) => {
      const { data } = await apiClient.post('/rate-cards/calculate-rate', params);
      return data;
    },
    compareCarriers: async (
      params: {
        origin_pincode: string;
        destination_pincode: string;
        weight_kg: number;
        length_cm?: number;
        width_cm?: number;
        height_cm?: number;
        payment_mode?: 'PREPAID' | 'COD';
        order_value?: number;
        channel?: string;
        declared_value?: number;
        is_fragile?: boolean;
        num_packages?: number;
        service_type?: string;
        transporter_ids?: string[];
      },
      strategy?: 'CHEAPEST_FIRST' | 'FASTEST_FIRST' | 'BEST_SLA' | 'BALANCED'
    ) => {
      const { data } = await apiClient.post('/rate-cards/compare-carriers', params, { params: { strategy } });
      return data;
    },
    allocate: async (params: {
      origin_pincode: string;
      destination_pincode: string;
      weight_kg: number;
      length_cm?: number;
      width_cm?: number;
      height_cm?: number;
      payment_mode?: 'PREPAID' | 'COD';
      order_value?: number;
      channel?: string;
      declared_value?: number;
      is_fragile?: boolean;
      num_packages?: number;
      service_type?: string;
      transporter_ids?: string[];
      strategy?: 'CHEAPEST_FIRST' | 'FASTEST_FIRST' | 'BEST_SLA' | 'BALANCED';
    }) => {
      const { data } = await apiClient.post('/rate-cards/allocate', params);
      return data;
    },
  },
};

// Serviceability API
export const serviceabilityApi = {
  list: async (params?: { page?: number; size?: number; transporter_id?: string; is_active?: boolean }) => {
    const { data } = await apiClient.get('/serviceability', { params });
    return data;
  },
  check: async (pincode: string) => {
    const { data } = await apiClient.get(`/serviceability/check/${pincode}`);
    return data;
  },
  bulkCheck: async (pincodes: string[]) => {
    const { data } = await apiClient.post('/serviceability/bulk-check', { pincodes });
    return data;
  },
  create: async (serviceability: { pincode: string; city: string; state: string; region?: string; transporter_ids?: string[]; prepaid_available?: boolean; cod_available?: boolean; is_active?: boolean }) => {
    const { data } = await apiClient.post('/serviceability', serviceability);
    return data;
  },
  update: async (id: string, serviceability: Partial<{ city: string; state: string; region?: string; transporter_ids?: string[]; prepaid_available?: boolean; cod_available?: boolean; is_active?: boolean }>) => {
    const { data } = await apiClient.put(`/serviceability/${id}`, serviceability);
    return data;
  },
  bulkImport: async (file: FormData) => {
    const { data } = await apiClient.post('/serviceability/bulk-import', file, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  getDashboard: async () => {
    const { data } = await apiClient.get('/serviceability/dashboard');
    return data;
  },
  // Allocation
  allocateOrder: async (request: {
    order_id: string;
    customer_pincode: string;
    channel_code?: string;
    payment_mode?: string;
    order_value?: number;
    items?: { product_id: string; quantity: number }[];
    weight_kg?: number;
    dimensions?: { length: number; width: number; height: number };
    allocation_strategy?: 'CHEAPEST_FIRST' | 'FASTEST_FIRST' | 'BEST_SLA' | 'BALANCED';
  }) => {
    const { data } = await apiClient.post('/serviceability/allocate', request);
    return data;
  },
  getAllocationLogs: async (params?: {
    order_id?: string;
    is_successful?: boolean;
    limit?: number;
  }) => {
    const { data } = await apiClient.get('/serviceability/allocation-logs', { params });
    return data;
  },
  // Allocation Rules
  getAllocationRules: async (params?: { channel_code?: string; is_active?: boolean }) => {
    const { data } = await apiClient.get('/serviceability/allocation-rules', { params });
    return data;
  },
  createAllocationRule: async (rule: {
    name: string;
    description?: string;
    channel_code?: string;
    priority: number;
    allocation_type: string;
    fixed_warehouse_id?: string;
    priority_factors?: string[];
    min_order_value?: number;
    max_order_value?: number;
    payment_mode?: string;
    allow_split?: boolean;
    max_splits?: number;
    is_active?: boolean;
  }) => {
    const { data } = await apiClient.post('/serviceability/allocation-rules', rule);
    return data;
  },
  updateAllocationRule: async (id: string, rule: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/serviceability/allocation-rules/${id}`, rule);
    return data;
  },
  deleteAllocationRule: async (id: string) => {
    await apiClient.delete(`/serviceability/allocation-rules/${id}`);
  },
};

// ============================================
// SERIALIZATION API (Barcode Generation)
// ============================================

// Serial Number Types
export interface SerialPreview {
  supplier_code: string;
  model_code: string;
  year_code: string;
  month_code: string;
  current_last_serial: number;
  preview_barcodes: string[];
}

export interface GeneratedSerialSummary {
  model_code: string;
  quantity: number;
  start_serial: number;
  end_serial: number;
  start_barcode: string;
  end_barcode: string;
}

export interface POSerialsResponse {
  po_id: string;
  total: number;
  by_status: Record<string, number>;
  serials: Array<{
    id: string;
    barcode: string;
    model_code: string;
    serial_number: number;
    status: string;
    product_sku?: string;
  }>;
}

export interface ModelCodeReference {
  id: string;
  fg_code: string;
  model_code: string;
  item_type: string;
  product_id?: string;
  product_sku?: string;
  description?: string;
  is_active: boolean;
}

export interface SupplierCode {
  id: string;
  code: string;
  name: string;
  vendor_id?: string;
  is_active: boolean;
}

// Serialization API
export const serializationApi = {
  // Preview codes without saving
  preview: async (params: { supplier_code: string; model_code: string; quantity?: number }): Promise<SerialPreview> => {
    const { data } = await apiClient.post<SerialPreview>('/serialization/preview', params);
    return data;
  },

  // Generate serial numbers for a PO (when PO is sent to vendor)
  generate: async (params: {
    po_id: string;
    supplier_code: string;
    items: Array<{
      po_item_id?: string;
      product_id?: string;
      product_sku?: string;
      model_code: string;
      quantity: number;
      item_type?: string;
    }>;
  }) => {
    const { data } = await apiClient.post('/serialization/generate', params);
    return data;
  },

  // Get serials for a PO
  getByPO: async (poId: string, params?: { status?: string; limit?: number; offset?: number }): Promise<POSerialsResponse> => {
    const { data } = await apiClient.get<POSerialsResponse>(`/serialization/po/${poId}`, { params });
    return data;
  },

  // Export serials for a PO as CSV
  exportPOSerials: async (poId: string, format: 'csv' | 'txt' = 'csv') => {
    const { data } = await apiClient.get(`/serialization/po/${poId}/export`, { params: { format } });
    return data;
  },

  // Mark serials as sent to vendor
  markSentToVendor: async (poId: string) => {
    const { data } = await apiClient.post(`/serialization/po/${poId}/send-to-vendor`);
    return data;
  },

  // Get sequence status (to know next available serial)
  getSequenceStatus: async (modelCode: string, supplierCode: string) => {
    const { data } = await apiClient.get(`/serialization/sequence/${modelCode}`, { params: { supplier_code: supplierCode } });
    return data;
  },

  // Lookup a serial by barcode
  lookup: async (barcode: string) => {
    const { data } = await apiClient.get(`/serialization/lookup/${barcode}`);
    return data;
  },

  // Validate a barcode
  validate: async (barcode: string) => {
    const { data } = await apiClient.post(`/serialization/validate/${barcode}`);
    return data;
  },

  // Get dashboard stats
  getDashboard: async () => {
    const { data } = await apiClient.get('/serialization/dashboard');
    return data;
  },

  // Supplier codes management
  getSupplierCodes: async (activeOnly: boolean = true): Promise<SupplierCode[]> => {
    const { data } = await apiClient.get<SupplierCode[]>('/serialization/suppliers', { params: { active_only: activeOnly } });
    return data;
  },
  createSupplierCode: async (supplierCode: { code: string; name: string; vendor_id?: string; description?: string }) => {
    const { data } = await apiClient.post('/serialization/suppliers', supplierCode);
    return data;
  },

  // Model codes management
  getModelCodes: async (activeOnly: boolean = true, itemType?: string, linkedOnly: boolean = false): Promise<ModelCodeReference[]> => {
    const { data } = await apiClient.get<ModelCodeReference[]>('/serialization/model-codes', { params: { active_only: activeOnly, item_type: itemType, linked_only: linkedOnly } });
    return data;
  },
  createModelCode: async (modelCode: { fg_code: string; model_code: string; item_type?: string; product_id?: string; product_sku?: string; description?: string }) => {
    const { data } = await apiClient.post('/serialization/model-codes', modelCode);
    return data;
  },

  // Generate FG code
  generateFGCode: async (params: { category_code: string; subcategory_code: string; brand_code: string; model_name: string }) => {
    const { data } = await apiClient.post('/serialization/fg-code/generate', params);
    return data;
  },
};

// Company type is imported at the bottom with companyApi

// ============================================
// HR & PAYROLL API
// ============================================

// HR Types
export interface Department {
  id: string;
  code: string;
  name: string;
  description?: string;
  parent_id?: string;
  parent_name?: string;
  head_id?: string;
  head_name?: string;
  is_active: boolean;
  employee_count: number;
  created_at: string;
  updated_at: string;
}

export interface Employee {
  id: string;
  employee_code: string;
  user_id: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  phone?: string;
  avatar_url?: string;
  department_id?: string;
  department_name?: string;
  designation?: string;
  employment_type: string;
  status: string;
  joining_date: string;
  reporting_manager_id?: string;
  reporting_manager_name?: string;
  date_of_birth?: string;
  gender?: string;
  blood_group?: string;
  marital_status?: string;
  nationality?: string;
  personal_email?: string;
  personal_phone?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  emergency_contact_relation?: string;
  current_address?: Record<string, unknown>;
  permanent_address?: Record<string, unknown>;
  confirmation_date?: string;
  resignation_date?: string;
  last_working_date?: string;
  pan_number?: string;
  aadhaar_number?: string;
  uan_number?: string;
  esic_number?: string;
  bank_name?: string;
  bank_account_number?: string;
  bank_ifsc_code?: string;
  profile_photo_url?: string;
  documents?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SalaryStructure {
  id: string;
  employee_id: string;
  effective_from: string;
  basic_salary: number;
  hra: number;
  conveyance: number;
  medical_allowance: number;
  special_allowance: number;
  other_allowances: number;
  gross_salary: number;
  employer_pf: number;
  employer_esic: number;
  monthly_ctc: number;
  annual_ctc: number;
  pf_applicable: boolean;
  esic_applicable: boolean;
  pt_applicable: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AttendanceRecord {
  id: string;
  employee_id: string;
  attendance_date: string;
  status: string;
  check_in?: string;
  check_out?: string;
  work_hours?: number;
  is_late: boolean;
  late_minutes: number;
  is_early_out: boolean;
  early_out_minutes: number;
  location_in?: Record<string, unknown>;
  location_out?: Record<string, unknown>;
  remarks?: string;
  approved_by?: string;
  approved_by_name?: string;
  employee_code?: string;
  employee_name?: string;
  department_name?: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  id: string;
  employee_id: string;
  leave_type: string;
  financial_year: string;
  opening_balance: number;
  accrued: number;
  taken: number;
  adjusted: number;
  closing_balance: number;
  carry_forward_limit: number;
}

export interface LeaveRequest {
  id: string;
  employee_id: string;
  leave_type: string;
  from_date: string;
  to_date: string;
  days: number;
  is_half_day: boolean;
  half_day_type?: string;
  reason?: string;
  status: string;
  applied_on: string;
  approved_by?: string;
  approved_by_name?: string;
  approved_on?: string;
  rejection_reason?: string;
  employee_code?: string;
  employee_name?: string;
  department_name?: string;
  created_at: string;
  updated_at: string;
}

export interface PayrollRun {
  id: string;
  payroll_month: string;
  financial_year: string;
  status: string;
  total_employees: number;
  total_gross: number;
  total_deductions: number;
  total_net: number;
  processed_by?: string;
  processed_by_name?: string;
  processed_at?: string;
  approved_by?: string;
  approved_by_name?: string;
  approved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Payslip {
  id: string;
  payroll_id: string;
  employee_id: string;
  payslip_number: string;
  employee_code?: string;
  employee_name?: string;
  department_name?: string;
  designation?: string;
  working_days: number;
  days_present: number;
  days_absent: number;
  leaves_taken: number;
  basic_earned: number;
  hra_earned: number;
  conveyance_earned: number;
  medical_earned: number;
  special_earned: number;
  other_earned: number;
  overtime_amount: number;
  arrears: number;
  bonus: number;
  gross_earnings: number;
  employee_pf: number;
  employer_pf: number;
  employee_esic: number;
  employer_esic: number;
  professional_tax: number;
  tds: number;
  loan_deduction: number;
  advance_deduction: number;
  other_deductions: number;
  total_deductions: number;
  net_salary: number;
  payment_mode?: string;
  payment_date?: string;
  payment_reference?: string;
  payslip_pdf_url?: string;
  created_at: string;
  updated_at: string;
}

export interface HRDashboardStats {
  total_employees: number;
  active_employees: number;
  on_leave_today: number;
  new_joinings_this_month: number;
  exits_this_month: number;
  present_today: number;
  absent_today: number;
  not_marked: number;
  pending_leave_requests: number;
  pending_payroll_approval: number;
  department_wise: Array<{ department: string; count: number }>;
}

// Report Types
export interface PFReportItem {
  employee_id: string;
  employee_code: string;
  employee_name: string;
  uan_number?: string;
  gross_wages: number;
  epf_wages: number;
  eps_wages: number;
  edli_wages: number;
  epf_contribution_employee: number;
  epf_contribution_employer: number;
  eps_contribution: number;
  edli_contribution: number;
  admin_charges: number;
  ncp_days: number;
}

export interface ESICReportItem {
  employee_id: string;
  employee_code: string;
  employee_name: string;
  esic_number?: string;
  gross_wages: number;
  employee_contribution: number;
  employer_contribution: number;
  total_contribution: number;
  days_worked: number;
}

export interface SalaryRegisterEmployee {
  employee_id: string;
  employee_code: string;
  employee_name: string;
  department?: string;
  designation?: string;
  bank_name?: string;
  bank_account?: string;
  ifsc_code?: string;
  pan_number?: string;
  uan_number?: string;
  working_days: number;
  days_present: number;
  days_absent: number;
  leaves_taken: number;
  basic: number;
  hra: number;
  conveyance: number;
  medical: number;
  special: number;
  other_earnings: number;
  overtime: number;
  arrears: number;
  bonus: number;
  gross_earnings: number;
  employee_pf: number;
  employee_esic: number;
  professional_tax: number;
  tds: number;
  loan_deduction: number;
  advance_deduction: number;
  other_deductions: number;
  total_deductions: number;
  net_salary: number;
  employer_pf: number;
  employer_esic: number;
}

export interface SalaryRegisterResponse {
  payroll_month: string;
  total_employees: number;
  summary: {
    total_gross: number;
    total_deductions: number;
    total_net: number;
    total_pf: number;
    total_esic: number;
  };
  employees: SalaryRegisterEmployee[];
}

// Performance Management Types
export interface PerformanceDashboardStats {
  active_cycles: number;
  pending_self_reviews: number;
  pending_manager_reviews: number;
  pending_hr_reviews: number;
  total_goals: number;
  completed_goals: number;
  in_progress_goals: number;
  overdue_goals: number;
  rating_distribution: Array<{ band: string; count: number }>;
  recent_feedback_count: number;
}

export interface AppraisalCycle {
  id: string;
  name: string;
  description: string | null;
  financial_year: string;
  start_date: string;
  end_date: string;
  review_start_date: string | null;
  review_end_date: string | null;
  status: 'DRAFT' | 'ACTIVE' | 'CLOSED';
  created_at: string;
  updated_at: string;
}

export interface KPI {
  id: string;
  name: string;
  description: string | null;
  category: string;
  unit_of_measure: string;
  target_value: number | null;
  weightage: number;
  department_id: string | null;
  department_name: string | null;
  designation: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Goal {
  id: string;
  employee_id: string;
  cycle_id: string;
  title: string;
  description: string | null;
  category: string;
  kpi_id: string | null;
  kpi_name: string | null;
  target_value: number | null;
  achieved_value: number | null;
  unit_of_measure: string | null;
  weightage: number;
  start_date: string;
  due_date: string;
  completed_date: string | null;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  completion_percentage: number;
  employee_name: string | null;
  employee_code: string | null;
  cycle_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface Appraisal {
  id: string;
  employee_id: string;
  cycle_id: string;
  status: 'NOT_STARTED' | 'SELF_REVIEW' | 'MANAGER_REVIEW' | 'HR_REVIEW' | 'COMPLETED';
  self_rating: number | null;
  self_comments: string | null;
  self_review_date: string | null;
  manager_id: string | null;
  manager_rating: number | null;
  manager_comments: string | null;
  manager_review_date: string | null;
  final_rating: number | null;
  performance_band: string | null;
  goals_achieved: number;
  goals_total: number;
  overall_goal_score: number | null;
  strengths: string | null;
  areas_of_improvement: string | null;
  development_plan: string | null;
  recommended_for_promotion: boolean;
  recommended_increment_percentage: number | null;
  hr_reviewed_by: string | null;
  hr_review_date: string | null;
  hr_comments: string | null;
  employee_name: string | null;
  employee_code: string | null;
  manager_name: string | null;
  cycle_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface PerformanceFeedback {
  id: string;
  employee_id: string;
  given_by: string;
  feedback_type: 'APPRECIATION' | 'IMPROVEMENT' | 'SUGGESTION';
  title: string;
  content: string;
  is_private: boolean;
  goal_id: string | null;
  employee_name: string | null;
  employee_code: string | null;
  given_by_name: string | null;
  goal_title: string | null;
  created_at: string;
}

// HR API
export const hrApi = {
  // Dashboard
  getDashboard: async (): Promise<HRDashboardStats> => {
    const { data } = await apiClient.get<HRDashboardStats>('/hr/dashboard');
    return data;
  },

  // Departments
  departments: {
    list: async (params?: { is_active?: boolean; search?: string }) => {
      const { data } = await apiClient.get<{ items: Department[]; total: number }>('/hr/departments', { params });
      return data;
    },
    dropdown: async () => {
      const { data } = await apiClient.get<Array<{ id: string; code: string; name: string }>>('/hr/departments/dropdown');
      return data;
    },
    getById: async (id: string) => {
      const { data } = await apiClient.get<Department>(`/hr/departments/${id}`);
      return data;
    },
    create: async (dept: { code: string; name: string; description?: string; parent_id?: string; head_id?: string; is_active?: boolean }) => {
      const { data } = await apiClient.post<Department>('/hr/departments', dept);
      return data;
    },
    update: async (id: string, dept: Partial<{ name: string; description: string; parent_id: string; head_id: string; is_active: boolean }>) => {
      const { data } = await apiClient.put<Department>(`/hr/departments/${id}`, dept);
      return data;
    },
  },

  // Employees
  employees: {
    list: async (params?: { page?: number; size?: number; status?: string; department_id?: string; employment_type?: string; search?: string }) => {
      const { data } = await apiClient.get<{ items: Employee[]; total: number; page: number; size: number; pages: number }>('/hr/employees', { params });
      return data;
    },
    dropdown: async (departmentId?: string) => {
      const { data } = await apiClient.get<Array<{ id: string; employee_code: string; full_name: string; designation?: string; department_name?: string }>>('/hr/employees/dropdown', { params: { department_id: departmentId } });
      return data;
    },
    getById: async (id: string) => {
      const { data } = await apiClient.get<Employee>(`/hr/employees/${id}`);
      return data;
    },
    create: async (employee: {
      email: string;
      password: string;
      first_name: string;
      last_name?: string;
      phone?: string;
      date_of_birth?: string;
      gender?: string;
      blood_group?: string;
      marital_status?: string;
      nationality?: string;
      personal_email?: string;
      personal_phone?: string;
      emergency_contact_name?: string;
      emergency_contact_phone?: string;
      emergency_contact_relation?: string;
      current_address?: Record<string, unknown>;
      permanent_address?: Record<string, unknown>;
      department_id?: string;
      designation?: string;
      employment_type?: string;
      joining_date: string;
      confirmation_date?: string;
      reporting_manager_id?: string;
      pan_number?: string;
      aadhaar_number?: string;
      uan_number?: string;
      esic_number?: string;
      bank_name?: string;
      bank_account_number?: string;
      bank_ifsc_code?: string;
      role_ids?: string[];
    }) => {
      const { data } = await apiClient.post<Employee>('/hr/employees', employee);
      return data;
    },
    update: async (id: string, employee: Partial<Employee>) => {
      const { data } = await apiClient.put<Employee>(`/hr/employees/${id}`, employee);
      return data;
    },
    getSalary: async (id: string) => {
      const { data } = await apiClient.get<SalaryStructure>(`/hr/employees/${id}/salary`);
      return data;
    },
    updateSalary: async (id: string, salary: {
      employee_id: string;
      effective_from: string;
      basic_salary: number;
      hra?: number;
      conveyance?: number;
      medical_allowance?: number;
      special_allowance?: number;
      other_allowances?: number;
      pf_applicable?: boolean;
      esic_applicable?: boolean;
      pt_applicable?: boolean;
    }) => {
      const { data } = await apiClient.put<SalaryStructure>(`/hr/employees/${id}/salary`, salary);
      return data;
    },
  },

  // Attendance
  attendance: {
    checkIn: async (employeeId?: string, location?: Record<string, unknown>, remarks?: string) => {
      const { data } = await apiClient.post<AttendanceRecord>('/hr/attendance/check-in', { employee_id: employeeId, location, remarks });
      return data;
    },
    checkOut: async (employeeId?: string, location?: Record<string, unknown>, remarks?: string) => {
      const { data } = await apiClient.post<AttendanceRecord>('/hr/attendance/check-out', { employee_id: employeeId, location, remarks });
      return data;
    },
    list: async (params?: { page?: number; size?: number; employee_id?: string; department_id?: string; from_date?: string; to_date?: string; status?: string }) => {
      const { data } = await apiClient.get<{ items: AttendanceRecord[]; total: number; page: number; size: number; pages: number }>('/hr/attendance', { params });
      return data;
    },
  },

  // Leave
  leave: {
    getBalances: async (employeeId: string, financialYear?: string) => {
      const { data } = await apiClient.get<{ employee_id: string; financial_year: string; balances: LeaveBalance[] }>(`/hr/leave-balances/${employeeId}`, { params: { financial_year: financialYear } });
      return data;
    },
    listRequests: async (params?: { page?: number; size?: number; employee_id?: string; status?: string; from_date?: string; to_date?: string }) => {
      const { data } = await apiClient.get<{ items: LeaveRequest[]; total: number; page: number; size: number; pages: number }>('/hr/leave-requests', { params });
      return data;
    },
    apply: async (leave: {
      employee_id?: string;
      leave_type: string;
      from_date: string;
      to_date: string;
      is_half_day?: boolean;
      half_day_type?: string;
      reason?: string;
    }) => {
      const { data } = await apiClient.post<LeaveRequest>('/hr/leave-requests', leave);
      return data;
    },
    approve: async (id: string, action: 'APPROVE' | 'REJECT', rejectionReason?: string) => {
      const { data } = await apiClient.put<LeaveRequest>(`/hr/leave-requests/${id}/approve`, { action, rejection_reason: rejectionReason });
      return data;
    },
  },

  // Payroll
  payroll: {
    list: async (params?: { page?: number; size?: number; financial_year?: string; status?: string }) => {
      const { data } = await apiClient.get<{ items: PayrollRun[]; total: number; page: number; size: number; pages: number }>('/hr/payroll', { params });
      return data;
    },
    process: async (request: { payroll_month: string; financial_year: string; employee_ids?: string[] }) => {
      const { data } = await apiClient.post<PayrollRun>('/hr/payroll/process', request);
      return data;
    },
    approve: async (id: string) => {
      const { data } = await apiClient.put<PayrollRun>(`/hr/payroll/${id}/approve`);
      return data;
    },
    listPayslips: async (params?: { page?: number; size?: number; payroll_id?: string; employee_id?: string }) => {
      const { data } = await apiClient.get<{ items: Payslip[]; total: number; page: number; size: number; pages: number }>('/hr/payslips', { params });
      return data;
    },
  },

  // Reports
  reports: {
    getPFECR: async (params: { payroll_month: string; department_id?: string }) => {
      const { data } = await apiClient.get<PFReportItem[]>('/hr/reports/pf-ecr', { params });
      return data;
    },
    getESIC: async (params: { payroll_month: string; department_id?: string }) => {
      const { data } = await apiClient.get<ESICReportItem[]>('/hr/reports/esic', { params });
      return data;
    },
    getSalaryRegister: async (params: { payroll_month: string; department_id?: string }) => {
      const { data } = await apiClient.get<SalaryRegisterResponse>('/hr/reports/salary-register', { params });
      return data;
    },
  },

  // Performance Management
  performance: {
    // Dashboard
    getDashboard: async () => {
      const { data } = await apiClient.get<PerformanceDashboardStats>('/hr/performance/dashboard');
      return data;
    },

    // Appraisal Cycles
    cycles: {
      list: async (params?: { page?: number; size?: number; status?: string; financial_year?: string }) => {
        const { data } = await apiClient.get<{ items: AppraisalCycle[]; total: number; page: number; size: number; pages: number }>('/hr/performance/cycles', { params });
        return data;
      },
      getById: async (id: string) => {
        const { data } = await apiClient.get<AppraisalCycle>(`/hr/performance/cycles/${id}`);
        return data;
      },
      create: async (cycle: { name: string; description?: string; financial_year: string; start_date: string; end_date: string; review_start_date?: string; review_end_date?: string }) => {
        const { data } = await apiClient.post<AppraisalCycle>('/hr/performance/cycles', cycle);
        return data;
      },
      update: async (id: string, cycle: Partial<{ name: string; description: string; start_date: string; end_date: string; review_start_date: string; review_end_date: string; status: string }>) => {
        const { data } = await apiClient.put<AppraisalCycle>(`/hr/performance/cycles/${id}`, cycle);
        return data;
      },
    },

    // KPIs
    kpis: {
      list: async (params?: { page?: number; size?: number; category?: string; department_id?: string; is_active?: boolean }) => {
        const { data } = await apiClient.get<{ items: KPI[]; total: number; page: number; size: number; pages: number }>('/hr/performance/kpis', { params });
        return data;
      },
      create: async (kpi: { name: string; description?: string; category: string; unit_of_measure: string; target_value?: number; weightage?: number; department_id?: string; designation?: string }) => {
        const { data } = await apiClient.post<KPI>('/hr/performance/kpis', kpi);
        return data;
      },
      update: async (id: string, kpi: Partial<{ name: string; description: string; category: string; unit_of_measure: string; target_value: number; weightage: number; department_id: string; designation: string; is_active: boolean }>) => {
        const { data } = await apiClient.put<KPI>(`/hr/performance/kpis/${id}`, kpi);
        return data;
      },
    },

    // Goals
    goals: {
      list: async (params?: { page?: number; size?: number; employee_id?: string; cycle_id?: string; status?: string; category?: string }) => {
        const { data } = await apiClient.get<{ items: Goal[]; total: number; page: number; size: number; pages: number }>('/hr/performance/goals', { params });
        return data;
      },
      getById: async (id: string) => {
        const { data } = await apiClient.get<Goal>(`/hr/performance/goals/${id}`);
        return data;
      },
      create: async (goal: { employee_id: string; cycle_id: string; title: string; description?: string; category: string; kpi_id?: string; target_value?: number; unit_of_measure?: string; weightage?: number; start_date: string; due_date: string }) => {
        const { data } = await apiClient.post<Goal>('/hr/performance/goals', goal);
        return data;
      },
      update: async (id: string, goal: Partial<{ title: string; description: string; category: string; target_value: number; achieved_value: number; unit_of_measure: string; weightage: number; start_date: string; due_date: string; completed_date: string; status: string; completion_percentage: number }>) => {
        const { data } = await apiClient.put<Goal>(`/hr/performance/goals/${id}`, goal);
        return data;
      },
    },

    // Appraisals
    appraisals: {
      list: async (params?: { page?: number; size?: number; employee_id?: string; cycle_id?: string; status?: string; manager_id?: string }) => {
        const { data } = await apiClient.get<{ items: Appraisal[]; total: number; page: number; size: number; pages: number }>('/hr/performance/appraisals', { params });
        return data;
      },
      getById: async (id: string) => {
        const { data } = await apiClient.get<Appraisal>(`/hr/performance/appraisals/${id}`);
        return data;
      },
      create: async (appraisal: { employee_id: string; cycle_id: string; manager_id?: string }) => {
        const { data } = await apiClient.post<Appraisal>('/hr/performance/appraisals', appraisal);
        return data;
      },
      submitSelfReview: async (id: string, review: { self_rating: number; self_comments?: string }) => {
        const { data } = await apiClient.put<Appraisal>(`/hr/performance/appraisals/${id}/self-review`, review);
        return data;
      },
      submitManagerReview: async (id: string, review: { manager_rating: number; manager_comments?: string; strengths?: string; areas_of_improvement?: string; development_plan?: string; recommended_for_promotion?: boolean; recommended_increment_percentage?: number }) => {
        const { data } = await apiClient.put<Appraisal>(`/hr/performance/appraisals/${id}/manager-review`, review);
        return data;
      },
      submitHRReview: async (id: string, review: { final_rating: number; performance_band: string; hr_comments?: string }) => {
        const { data } = await apiClient.put<Appraisal>(`/hr/performance/appraisals/${id}/hr-review`, review);
        return data;
      },
    },

    // Feedback
    feedback: {
      list: async (params?: { page?: number; size?: number; employee_id?: string; feedback_type?: string }) => {
        const { data } = await apiClient.get<{ items: PerformanceFeedback[]; total: number; page: number; size: number; pages: number }>('/hr/performance/feedback', { params });
        return data;
      },
      create: async (feedback: { employee_id: string; feedback_type: string; title: string; content: string; is_private?: boolean; goal_id?: string }) => {
        const { data } = await apiClient.post<PerformanceFeedback>('/hr/performance/feedback', feedback);
        return data;
      },
    },
  },
};

// ==================== Fixed Assets Types ====================

export type DepreciationMethod = 'SLM' | 'WDV';
export type AssetStatus = 'ACTIVE' | 'UNDER_MAINTENANCE' | 'DISPOSED' | 'SOLD' | 'WRITTEN_OFF';
export type TransferStatus = 'PENDING' | 'APPROVED' | 'COMPLETED' | 'CANCELLED';
export type MaintenanceStatus = 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

export interface AssetCategory {
  id: string;
  code: string;
  name: string;
  description: string | null;
  depreciation_method: DepreciationMethod;
  depreciation_rate: number;
  useful_life_years: number;
  asset_account_id: string | null;
  depreciation_account_id: string | null;
  expense_account_id: string | null;
  is_active: boolean;
  asset_count: number;
  created_at: string;
  updated_at: string;
}

export interface Asset {
  id: string;
  asset_code: string;
  name: string;
  description: string | null;
  category_id: string;
  category_name: string | null;
  serial_number: string | null;
  model_number: string | null;
  manufacturer: string | null;
  warehouse_id: string | null;
  warehouse_name: string | null;
  location_details: string | null;
  custodian_employee_id: string | null;
  custodian_name: string | null;
  department_id: string | null;
  department_name: string | null;
  purchase_date: string;
  purchase_price: number;
  purchase_invoice_no: string | null;
  vendor_id: string | null;
  vendor_name: string | null;
  po_number: string | null;
  capitalization_date: string;
  installation_cost: number;
  other_costs: number;
  capitalized_value: number;
  depreciation_method: DepreciationMethod | null;
  depreciation_rate: number | null;
  useful_life_years: number | null;
  salvage_value: number;
  accumulated_depreciation: number;
  current_book_value: number;
  last_depreciation_date: string | null;
  warranty_start_date: string | null;
  warranty_end_date: string | null;
  warranty_details: string | null;
  insured: boolean;
  insurance_policy_no: string | null;
  insurance_value: number | null;
  insurance_expiry: string | null;
  disposal_date: string | null;
  disposal_price: number | null;
  disposal_reason: string | null;
  gain_loss_on_disposal: number | null;
  status: AssetStatus;
  documents: Record<string, unknown> | null;
  images: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DepreciationEntry {
  id: string;
  asset_id: string;
  asset_code: string | null;
  asset_name: string | null;
  period_date: string;
  financial_year: string;
  opening_book_value: number;
  depreciation_method: DepreciationMethod;
  depreciation_rate: number;
  depreciation_amount: number;
  closing_book_value: number;
  accumulated_depreciation: number;
  is_posted: boolean;
  journal_entry_id: string | null;
  processed_by_name: string | null;
  processed_at: string | null;
  created_at: string;
}

export interface AssetTransfer {
  id: string;
  transfer_number: string;
  asset_id: string;
  asset_code: string | null;
  asset_name: string | null;
  from_warehouse_name: string | null;
  from_department_name: string | null;
  from_custodian_name: string | null;
  from_location_details: string | null;
  to_warehouse_name: string | null;
  to_department_name: string | null;
  to_custodian_name: string | null;
  to_location_details: string | null;
  transfer_date: string;
  reason: string | null;
  status: TransferStatus;
  requested_by_name: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssetMaintenance {
  id: string;
  maintenance_number: string;
  asset_id: string;
  asset_code: string | null;
  asset_name: string | null;
  maintenance_type: string;
  description: string;
  scheduled_date: string;
  started_date: string | null;
  completed_date: string | null;
  estimated_cost: number;
  actual_cost: number;
  vendor_name: string | null;
  vendor_invoice_no: string | null;
  status: MaintenanceStatus;
  findings: string | null;
  parts_replaced: string | null;
  recommendations: string | null;
  assigned_to_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface FixedAssetsDashboard {
  total_assets: number;
  active_assets: number;
  disposed_assets: number;
  under_maintenance: number;
  total_capitalized_value: number;
  total_accumulated_depreciation: number;
  total_current_book_value: number;
  monthly_depreciation: number;
  ytd_depreciation: number;
  pending_maintenance: number;
  pending_transfers: number;
  category_wise: Array<{ category_name: string; count: number; book_value: number }>;
  warranty_expiring_soon: number;
  insurance_expiring_soon: number;
}

// ==================== Fixed Assets API ====================

// ==================== Notification Types ====================

export type NotificationType =
  | 'SYSTEM' | 'ALERT' | 'ANNOUNCEMENT'
  | 'ORDER_CREATED' | 'ORDER_CONFIRMED' | 'ORDER_SHIPPED' | 'ORDER_DELIVERED' | 'ORDER_CANCELLED'
  | 'LOW_STOCK' | 'OUT_OF_STOCK' | 'STOCK_RECEIVED'
  | 'APPROVAL_PENDING' | 'APPROVAL_APPROVED' | 'APPROVAL_REJECTED'
  | 'LEAVE_REQUEST' | 'LEAVE_APPROVED' | 'LEAVE_REJECTED' | 'PAYSLIP_GENERATED' | 'APPRAISAL_DUE'
  | 'PAYMENT_RECEIVED' | 'PAYMENT_DUE' | 'INVOICE_GENERATED'
  | 'SERVICE_ASSIGNED' | 'SERVICE_COMPLETED' | 'WARRANTY_EXPIRING'
  | 'ASSET_MAINTENANCE_DUE' | 'ASSET_TRANSFER_PENDING'
  | 'TASK_ASSIGNED' | 'REMINDER' | 'MENTION';

export type NotificationPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export interface UserNotification {
  id: string;
  user_id: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  action_url: string | null;
  action_label: string | null;
  entity_type: string | null;
  entity_id: string | null;
  extra_data: Record<string, unknown> | null;
  is_read: boolean;
  read_at: string | null;
  channels: string[] | null;
  created_at: string;
  expires_at: string | null;
}

export interface NotificationStats {
  total: number;
  unread: number;
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface NotificationPreference {
  id: string;
  user_id: string;
  email_enabled: boolean;
  sms_enabled: boolean;
  push_enabled: boolean;
  in_app_enabled: boolean;
  type_preferences: Record<string, Record<string, boolean>> | null;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  email_digest_enabled: boolean;
  email_digest_frequency: string;
  created_at: string;
  updated_at: string;
}

export interface Announcement {
  id: string;
  title: string;
  message: string;
  announcement_type: string;
  action_url: string | null;
  action_label: string | null;
  target_roles: string[] | null;
  target_departments: string[] | null;
  start_date: string;
  end_date: string | null;
  is_dismissible: boolean;
  show_on_dashboard: boolean;
  is_active: boolean;
  created_by_id: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
  is_dismissed: boolean;
}

// ==================== Notifications API ====================

export const notificationsApi = {
  // User notifications
  getMyNotifications: async (params?: {
    page?: number;
    size?: number;
    is_read?: boolean;
    notification_type?: NotificationType;
  }) => {
    const { data } = await apiClient.get<{
      items: UserNotification[];
      total: number;
      unread_count: number;
      page: number;
      size: number;
      pages: number;
    }>('/notifications/my', { params });
    return data;
  },

  getUnreadCount: async () => {
    const { data } = await apiClient.get<{ unread_count: number }>('/notifications/my/unread-count');
    return data;
  },

  markAsRead: async (notificationIds: string[]) => {
    const { data } = await apiClient.put<{ marked_read: number }>('/notifications/my/read', { notification_ids: notificationIds });
    return data;
  },

  markAllAsRead: async () => {
    const { data } = await apiClient.put<{ marked_read: number }>('/notifications/my/read-all');
    return data;
  },

  deleteNotification: async (id: string) => {
    const { data } = await apiClient.delete<{ deleted: boolean }>(`/notifications/my/${id}`);
    return data;
  },

  getStats: async () => {
    const { data } = await apiClient.get<NotificationStats>('/notifications/my/stats');
    return data;
  },

  // Preferences
  getPreferences: async () => {
    const { data } = await apiClient.get<NotificationPreference>('/notifications/preferences');
    return data;
  },

  updatePreferences: async (preferences: Partial<{
    email_enabled: boolean;
    sms_enabled: boolean;
    push_enabled: boolean;
    in_app_enabled: boolean;
    type_preferences: Record<string, Record<string, boolean>>;
    quiet_hours_enabled: boolean;
    quiet_hours_start: string;
    quiet_hours_end: string;
    email_digest_enabled: boolean;
    email_digest_frequency: string;
  }>) => {
    const { data } = await apiClient.put<NotificationPreference>('/notifications/preferences', preferences);
    return data;
  },

  // Announcements
  getAnnouncements: async (params?: { page?: number; size?: number; active_only?: boolean }) => {
    const { data } = await apiClient.get<{ items: Announcement[]; total: number; page: number; size: number; pages: number }>('/notifications/announcements', { params });
    return data;
  },

  getActiveAnnouncements: async () => {
    const { data } = await apiClient.get<{ announcements: Announcement[] }>('/notifications/announcements/active');
    return data;
  },

  dismissAnnouncement: async (id: string) => {
    const { data } = await apiClient.post<{ dismissed: boolean }>(`/notifications/announcements/${id}/dismiss`);
    return data;
  },

  // Admin - Announcements
  createAnnouncement: async (announcement: {
    title: string;
    message: string;
    announcement_type?: string;
    action_url?: string;
    action_label?: string;
    target_roles?: string[];
    target_departments?: string[];
    start_date: string;
    end_date?: string;
    is_dismissible?: boolean;
    show_on_dashboard?: boolean;
  }) => {
    const { data } = await apiClient.post<Announcement>('/notifications/announcements', announcement);
    return data;
  },

  updateAnnouncement: async (id: string, announcement: Partial<{
    title: string;
    message: string;
    announcement_type: string;
    action_url: string;
    action_label: string;
    target_roles: string[];
    target_departments: string[];
    start_date: string;
    end_date: string;
    is_dismissible: boolean;
    show_on_dashboard: boolean;
    is_active: boolean;
  }>) => {
    const { data } = await apiClient.put<Announcement>(`/notifications/announcements/${id}`, announcement);
    return data;
  },

  deleteAnnouncement: async (id: string) => {
    const { data } = await apiClient.delete<{ deleted: boolean }>(`/notifications/announcements/${id}`);
    return data;
  },

  // Notification types
  getTypes: async () => {
    const { data } = await apiClient.get<{
      types: Array<{ type: string; category: string; label: string }>;
      categories: string[];
    }>('/notifications/types');
    return data;
  },
};

export const fixedAssetsApi = {
  // Dashboard
  getDashboard: async () => {
    const { data } = await apiClient.get<FixedAssetsDashboard>('/fixed-assets/dashboard');
    return data;
  },

  // Asset Categories
  categories: {
    list: async (params?: { page?: number; size?: number; is_active?: boolean; search?: string }) => {
      const { data } = await apiClient.get<{ items: AssetCategory[]; total: number; page: number; size: number; pages: number }>('/fixed-assets/categories', { params });
      return data;
    },
    dropdown: async () => {
      const { data } = await apiClient.get<Array<{ id: string; code: string; name: string; depreciation_method: string; depreciation_rate: number }>>('/fixed-assets/categories/dropdown');
      return data;
    },
    getById: async (id: string) => {
      const { data } = await apiClient.get<AssetCategory>(`/fixed-assets/categories/${id}`);
      return data;
    },
    create: async (category: {
      code: string;
      name: string;
      description?: string;
      depreciation_method?: DepreciationMethod;
      depreciation_rate: number;
      useful_life_years: number;
      asset_account_id?: string;
      depreciation_account_id?: string;
      expense_account_id?: string;
    }) => {
      const { data } = await apiClient.post<AssetCategory>('/fixed-assets/categories', category);
      return data;
    },
    update: async (id: string, category: Partial<{
      name: string;
      description: string;
      depreciation_method: DepreciationMethod;
      depreciation_rate: number;
      useful_life_years: number;
      asset_account_id: string;
      depreciation_account_id: string;
      expense_account_id: string;
      is_active: boolean;
    }>) => {
      const { data } = await apiClient.put<AssetCategory>(`/fixed-assets/categories/${id}`, category);
      return data;
    },
  },

  // Assets
  assets: {
    list: async (params?: {
      page?: number;
      size?: number;
      status?: AssetStatus;
      category_id?: string;
      warehouse_id?: string;
      department_id?: string;
      search?: string;
    }) => {
      const { data } = await apiClient.get<{ items: Asset[]; total: number; page: number; size: number; pages: number }>('/fixed-assets/assets', { params });
      return data;
    },
    getById: async (id: string) => {
      const { data } = await apiClient.get<Asset>(`/fixed-assets/assets/${id}`);
      return data;
    },
    create: async (asset: {
      name: string;
      description?: string;
      category_id: string;
      serial_number?: string;
      model_number?: string;
      manufacturer?: string;
      warehouse_id?: string;
      location_details?: string;
      custodian_employee_id?: string;
      department_id?: string;
      purchase_date: string;
      purchase_price: number;
      purchase_invoice_no?: string;
      vendor_id?: string;
      po_number?: string;
      capitalization_date: string;
      installation_cost?: number;
      other_costs?: number;
      depreciation_method?: DepreciationMethod;
      depreciation_rate?: number;
      useful_life_years?: number;
      salvage_value?: number;
      warranty_start_date?: string;
      warranty_end_date?: string;
      warranty_details?: string;
      insured?: boolean;
      insurance_policy_no?: string;
      insurance_value?: number;
      insurance_expiry?: string;
      notes?: string;
    }) => {
      const { data } = await apiClient.post<Asset>('/fixed-assets/assets', asset);
      return data;
    },
    update: async (id: string, asset: Partial<{
      name: string;
      description: string;
      serial_number: string;
      model_number: string;
      manufacturer: string;
      warehouse_id: string;
      location_details: string;
      custodian_employee_id: string;
      department_id: string;
      depreciation_method: DepreciationMethod;
      depreciation_rate: number;
      useful_life_years: number;
      salvage_value: number;
      warranty_start_date: string;
      warranty_end_date: string;
      warranty_details: string;
      insured: boolean;
      insurance_policy_no: string;
      insurance_value: number;
      insurance_expiry: string;
      notes: string;
    }>) => {
      const { data } = await apiClient.put<Asset>(`/fixed-assets/assets/${id}`, asset);
      return data;
    },
    dispose: async (id: string, disposal: {
      disposal_date: string;
      disposal_price: number;
      disposal_reason: string;
    }) => {
      const { data } = await apiClient.post<Asset>(`/fixed-assets/assets/${id}/dispose`, disposal);
      return data;
    },
  },

  // Depreciation
  depreciation: {
    list: async (params?: {
      page?: number;
      size?: number;
      asset_id?: string;
      financial_year?: string;
      is_posted?: boolean;
    }) => {
      const { data } = await apiClient.get<{ items: DepreciationEntry[]; total: number; page: number; size: number; pages: number }>('/fixed-assets/depreciation', { params });
      return data;
    },
    run: async (request: {
      period_date: string;
      financial_year: string;
      asset_ids?: string[];
    }) => {
      const { data } = await apiClient.post<{ entries_created: number; total_depreciation: number; entries: DepreciationEntry[] }>('/fixed-assets/depreciation/run', request);
      return data;
    },
  },

  // Transfers
  transfers: {
    list: async (params?: {
      page?: number;
      size?: number;
      asset_id?: string;
      status?: TransferStatus;
    }) => {
      const { data } = await apiClient.get<{ items: AssetTransfer[]; total: number; page: number; size: number; pages: number }>('/fixed-assets/transfers', { params });
      return data;
    },
    create: async (transfer: {
      asset_id: string;
      to_warehouse_id?: string;
      to_department_id?: string;
      to_custodian_id?: string;
      to_location_details?: string;
      transfer_date: string;
      reason?: string;
    }) => {
      const { data } = await apiClient.post<AssetTransfer>('/fixed-assets/transfers', transfer);
      return data;
    },
    approve: async (id: string) => {
      const { data } = await apiClient.put<AssetTransfer>(`/fixed-assets/transfers/${id}/approve`);
      return data;
    },
    complete: async (id: string) => {
      const { data } = await apiClient.put<AssetTransfer>(`/fixed-assets/transfers/${id}/complete`);
      return data;
    },
    cancel: async (id: string) => {
      const { data } = await apiClient.put<AssetTransfer>(`/fixed-assets/transfers/${id}/cancel`);
      return data;
    },
  },

  // Maintenance
  maintenance: {
    list: async (params?: {
      page?: number;
      size?: number;
      asset_id?: string;
      status?: MaintenanceStatus;
      maintenance_type?: string;
    }) => {
      const { data } = await apiClient.get<{ items: AssetMaintenance[]; total: number; page: number; size: number; pages: number }>('/fixed-assets/maintenance', { params });
      return data;
    },
    create: async (maintenance: {
      asset_id: string;
      maintenance_type: string;
      description: string;
      scheduled_date: string;
      estimated_cost?: number;
      vendor_id?: string;
      assigned_to?: string;
    }) => {
      const { data } = await apiClient.post<AssetMaintenance>('/fixed-assets/maintenance', maintenance);
      return data;
    },
    update: async (id: string, maintenance: Partial<{
      description: string;
      scheduled_date: string;
      started_date: string;
      completed_date: string;
      estimated_cost: number;
      actual_cost: number;
      vendor_id: string;
      vendor_invoice_no: string;
      status: MaintenanceStatus;
      findings: string;
      parts_replaced: string;
      recommendations: string;
      assigned_to: string;
    }>) => {
      const { data } = await apiClient.put<AssetMaintenance>(`/fixed-assets/maintenance/${id}`, maintenance);
      return data;
    },
  },
};

// ==================== AI INSIGHTS TYPES ====================

export interface DailyPrediction {
  date: string;
  predicted_value: number;
  lower_bound: number;
  upper_bound: number;
}

export interface OrderPrediction {
  date: string;
  predicted_orders: number;
}

export interface RevenueForecast {
  current_month_actual: number;
  current_month_predicted: number;
  next_month_predicted: number;
  next_quarter_predicted: number;
  trend_direction: 'UP' | 'DOWN' | 'STABLE';
  trend_percentage: number;
  confidence_score: number;
  daily_predictions: DailyPrediction[];
}

export interface SalesTrends {
  daily_average: number;
  weekly_pattern: Record<string, number>;
  monthly_growth: number;
  peak_hours: number[];
  best_days: string[];
  seasonality_index: Record<number, number>;
}

export interface ProductPerformance {
  id: string;
  name: string;
  sku: string;
  revenue: number;
  quantity: number;
}

export interface CategoryPerformance {
  id: string;
  name: string;
  revenue: number;
}

export interface ChannelPerformance {
  channel: string;
  revenue: number;
  order_count: number;
}

export interface TopPerformers {
  top_products: ProductPerformance[];
  top_categories: CategoryPerformance[];
  top_channels: ChannelPerformance[];
  fastest_growing: { id: string; name: string; growth_rate: number }[];
  declining: { id: string; name: string; growth_rate: number }[];
}

export interface OrderPredictions {
  daily_predictions: OrderPrediction[];
  expected_total: number;
  confidence: number;
}

export interface ReorderRecommendation {
  product_id: string;
  product_name: string;
  sku: string;
  current_stock: number;
  reorder_level: number;
  recommended_qty: number;
  urgency: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  days_until_stockout: number;
  daily_velocity: number;
  vendor_id: string | null;
  vendor_name: string | null;
  estimated_cost: number;
}

export interface StockoutRisk {
  product_id: string;
  product_name: string;
  sku: string;
  current_stock: number;
  reserved_stock: number;
  daily_velocity: number;
  days_until_stockout: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  potential_revenue_loss: number;
  pending_orders: number;
}

export interface SlowMovingItem {
  product_id: string;
  product_name: string;
  sku: string;
  current_stock: number;
  days_since_last_sale: number;
  stock_value: number;
  recommendation: 'WRITE_OFF' | 'HEAVY_DISCOUNT' | 'DISCOUNT' | 'PROMOTION';
}

export interface ChurnRiskCustomer {
  customer_id: string;
  customer_name: string;
  email: string | null;
  phone: string | null;
  risk_score: number;
  days_since_last_order: number;
  total_orders: number;
  total_spent: number;
  avg_order_value: number;
  recommended_action: 'URGENT_CALL' | 'PERSONAL_EMAIL' | 'SPECIAL_OFFER' | 'LOYALTY_PROGRAM';
}

export interface CustomerSegment {
  segment_name: string;
  description: string;
  customer_count: number;
  percentage: number;
  avg_order_value: number;
  total_revenue: number;
  characteristics: string[];
}

export interface CustomerSegments {
  total_customers: number;
  champions: CustomerSegment;
  loyal_customers: CustomerSegment;
  potential_loyalists: CustomerSegment;
  new_customers: CustomerSegment;
  at_risk: CustomerSegment;
  hibernating: CustomerSegment;
  lost: CustomerSegment;
}

export interface HighValueCustomer {
  customer_id: string;
  customer_name: string;
  email: string | null;
  total_orders: number;
  total_spent: number;
  predicted_clv: number;
  segment: string;
}

export interface SegmentChart {
  name: string;
  value: number;
}

export interface StockoutTimeline {
  product: string;
  days: number;
}

export interface InsightsDashboard {
  revenue_trend: string;
  predicted_monthly_revenue: number;
  order_trend: string;
  predicted_monthly_orders: number;
  critical_stockouts: number;
  reorder_needed: number;
  high_churn_risk: number;
  slow_moving_value: number;
  top_insight_sales: string;
  top_insight_inventory: string;
  top_insight_customers: string;
  revenue_forecast_chart: DailyPrediction[];
  order_forecast_chart: OrderPrediction[];
  customer_segments_chart: SegmentChart[];
  stockout_timeline: StockoutTimeline[];
}

// ==================== AI INSIGHTS API ====================

export const insightsApi = {
  // Dashboard
  getDashboard: async () => {
    const { data } = await apiClient.get<InsightsDashboard>('/insights/dashboard');
    return data;
  },

  // Sales Insights
  getRevenueForecast: async (params?: { days_ahead?: number; lookback_days?: number }) => {
    const { data } = await apiClient.get<RevenueForecast>('/insights/sales/revenue-forecast', { params });
    return data;
  },

  getSalesTrends: async (params?: { lookback_days?: number }) => {
    const { data } = await apiClient.get<SalesTrends>('/insights/sales/trends', { params });
    return data;
  },

  getTopPerformers: async (params?: { period_days?: number; limit?: number }) => {
    const { data } = await apiClient.get<TopPerformers>('/insights/sales/top-performers', { params });
    return data;
  },

  getOrderPredictions: async (params?: { days_ahead?: number }) => {
    const { data } = await apiClient.get<OrderPredictions>('/insights/sales/order-predictions', { params });
    return data;
  },

  // Inventory Insights
  getReorderRecommendations: async (params?: { limit?: number }) => {
    const { data } = await apiClient.get<{ items: ReorderRecommendation[]; total: number }>('/insights/inventory/reorder', { params });
    return data;
  },

  getStockoutRisks: async (params?: { limit?: number }) => {
    const { data } = await apiClient.get<{ items: StockoutRisk[]; total: number }>('/insights/inventory/stockout-risks', { params });
    return data;
  },

  getSlowMovingInventory: async (params?: { days_threshold?: number; limit?: number }) => {
    const { data } = await apiClient.get<{ items: SlowMovingItem[]; total: number }>('/insights/inventory/slow-moving', { params });
    return data;
  },

  // Customer Insights
  getChurnRiskCustomers: async (params?: { threshold?: number; limit?: number }) => {
    const { data } = await apiClient.get<{ items: ChurnRiskCustomer[]; total: number }>('/insights/customers/churn-risk', { params });
    return data;
  },

  getCustomerSegments: async () => {
    const { data } = await apiClient.get<CustomerSegments>('/insights/customers/segments');
    return data;
  },

  getHighValueCustomers: async (params?: { limit?: number }) => {
    const { data } = await apiClient.get<{ items: HighValueCustomer[]; total: number }>('/insights/customers/high-value', { params });
    return data;
  },
};

// ==================== AI SERVICES API (Advanced) ====================

export const aiApi = {
  // Dashboard
  getDashboard: async () => {
    const { data } = await apiClient.get('/ai/dashboard');
    return data;
  },

  getCapabilities: async () => {
    const { data } = await apiClient.get('/ai/capabilities');
    return data;
  },

  // Demand Forecasting
  getDemandDashboard: async () => {
    const { data } = await apiClient.get('/ai/forecast/demand/dashboard');
    return data;
  },

  getProductForecast: async (productId: string, params?: { days_ahead?: number; lookback_days?: number }) => {
    const { data } = await apiClient.get(`/ai/forecast/demand/product/${productId}`, { params });
    return data;
  },

  getCategoryForecast: async (categoryId: string, params?: { days_ahead?: number; lookback_days?: number }) => {
    const { data } = await apiClient.get(`/ai/forecast/demand/category/${categoryId}`, { params });
    return data;
  },

  getAllProductForecasts: async (params?: { days_ahead?: number; min_sales?: number }) => {
    const { data } = await apiClient.get('/ai/forecast/demand/all', { params });
    return data;
  },

  // Payment Prediction
  predictInvoicePayment: async (invoiceId: string) => {
    const { data } = await apiClient.get(`/ai/predict/payment/invoice/${invoiceId}`);
    return data;
  },

  getCollectionPriority: async (params?: { limit?: number }) => {
    const { data } = await apiClient.get('/ai/predict/payment/collection-priority', { params });
    return data;
  },

  getCashFlowPrediction: async (params?: { days_ahead?: number }) => {
    const { data } = await apiClient.get('/ai/predict/payment/cash-flow', { params });
    return data;
  },

  getCustomerCreditScore: async (customerId: string) => {
    const { data } = await apiClient.get(`/ai/predict/payment/customer-credit/${customerId}`);
    return data;
  },

  // Predictive Maintenance
  getMaintenanceDashboard: async () => {
    const { data } = await apiClient.get('/ai/predict/maintenance/dashboard');
    return data;
  },

  getInstallationHealth: async (installationId: string) => {
    const { data } = await apiClient.get(`/ai/predict/maintenance/installation/${installationId}`);
    return data;
  },

  getProactiveServiceList: async (params?: { health_threshold?: number; limit?: number }) => {
    const { data } = await apiClient.get('/ai/predict/maintenance/proactive-list', { params });
    return data;
  },

  getFailureAnalysis: async (params?: { days_back?: number }) => {
    const { data } = await apiClient.get('/ai/predict/maintenance/failure-analysis', { params });
    return data;
  },

  // AI Chatbot
  chat: async (query: string) => {
    const { data } = await apiClient.post('/ai/chat', { query });
    return data;
  },

  getChatQuickStats: async () => {
    const { data } = await apiClient.get('/ai/chat/quick-stats');
    return data;
  },
};

// ==================== LEADS API ====================

export const leadsApi = {
  list: async (params?: { page?: number; size?: number; search?: string; status?: string; source?: string; assigned_to?: string; temperature?: string }) => {
    const { data } = await apiClient.get('/leads', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/leads/${id}`);
    return data;
  },
  create: async (lead: Record<string, unknown>) => {
    const { data } = await apiClient.post('/leads', lead);
    return data;
  },
  update: async (id: string, lead: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/leads/${id}`, lead);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/leads/${id}`);
  },
  convert: async (id: string, conversionData: Record<string, unknown>) => {
    const { data } = await apiClient.post(`/leads/${id}/convert`, conversionData);
    return data;
  },
  autoAssign: async (id: string, params?: { strategy?: string; team_id?: string }) => {
    const { data } = await apiClient.post(`/leads/${id}/auto-assign`, null, { params });
    return data;
  },
  bulkAutoAssign: async (leadIds: string[], strategy?: string, teamId?: string) => {
    const { data } = await apiClient.post('/leads/auto-assign/bulk', {
      lead_ids: leadIds,
      strategy,
      team_id: teamId
    });
    return data;
  },
  getUnassigned: async (params?: { limit?: number; source?: string }) => {
    const { data } = await apiClient.get('/leads/unassigned', { params });
    return data;
  },
  getAssignmentStats: async (params?: { start_date?: string; end_date?: string }) => {
    const { data } = await apiClient.get('/leads/assignment-stats', { params });
    return data;
  },
  getAgentWorkload: async () => {
    const { data } = await apiClient.get('/leads/agents/workload');
    return data;
  },
  getStats: async () => {
    try {
      const { data } = await apiClient.get('/leads/stats');
      return data;
    } catch {
      return { total: 0, by_status: {}, by_source: {}, total_pipeline_value: 0, conversion_rate: 0 };
    }
  },
  getPipeline: async () => {
    try {
      const { data } = await apiClient.get('/leads/pipeline');
      return data;
    } catch {
      return {};
    }
  },
};

// ==================== CAMPAIGNS API ====================

export const campaignsApi = {
  list: async (params?: { page?: number; size?: number; search?: string; status?: string; type?: string }) => {
    const { data } = await apiClient.get('/campaigns', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/campaigns/${id}`);
    return data;
  },
  create: async (campaign: Record<string, unknown>) => {
    const { data } = await apiClient.post('/campaigns', campaign);
    return data;
  },
  update: async (id: string, campaign: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/campaigns/${id}`, campaign);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/campaigns/${id}`);
  },
  launch: async (id: string) => {
    const { data } = await apiClient.post(`/campaigns/${id}/launch`);
    return data;
  },
  pause: async (id: string) => {
    const { data } = await apiClient.post(`/campaigns/${id}/pause`);
    return data;
  },
  getStats: async (id: string) => {
    const { data } = await apiClient.get(`/campaigns/${id}/stats`);
    return data;
  },
};

// ==================== COMMISSIONS API ====================

export const commissionsApi = {
  list: async (params?: { page?: number; size?: number; agent_id?: string; status?: string; period?: string }) => {
    const { data } = await apiClient.get('/commissions', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/commissions/${id}`);
    return data;
  },
  create: async (commission: Record<string, unknown>) => {
    const { data } = await apiClient.post('/commissions', commission);
    return data;
  },
  approve: async (id: string) => {
    const { data } = await apiClient.post(`/commissions/${id}/approve`);
    return data;
  },
  reject: async (id: string, reason: string) => {
    const { data } = await apiClient.post(`/commissions/${id}/reject`, { reason });
    return data;
  },
  getSlabs: async () => {
    const { data } = await apiClient.get('/commissions/slabs');
    return data;
  },
  createSlab: async (slab: Record<string, unknown>) => {
    const { data } = await apiClient.post('/commissions/slabs', slab);
    return data;
  },
  getSummary: async (params?: { period?: string; agent_id?: string }) => {
    const { data } = await apiClient.get('/commissions/summary', { params });
    return data;
  },
  listPlans: async (params?: { page?: number; size?: number }) => {
    const { data } = await apiClient.get('/commissions/plans', { params });
    return data;
  },
  listTransactions: async (params?: { page?: number; size?: number; status?: string }) => {
    const { data } = await apiClient.get('/commissions/transactions', { params });
    return data;
  },
  listPayouts: async (params?: { page?: number; size?: number; status?: string }) => {
    const { data } = await apiClient.get('/commissions/payouts', { params });
    return data;
  },
  createPlan: async (plan: Record<string, unknown>) => {
    const { data } = await apiClient.post('/commissions/plans', plan);
    return data;
  },
  processPayout: async (payoutId: string, reference: string) => {
    const { data } = await apiClient.post(`/commissions/payouts/${payoutId}/process`, { payment_reference: reference });
    return data;
  },
};

// ==================== PROMOTIONS API ====================

export const promotionsApi = {
  list: async (params?: { page?: number; size?: number; search?: string; status?: string; type?: string }) => {
    const { data } = await apiClient.get('/promotions', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/promotions/${id}`);
    return data;
  },
  create: async (promotion: Record<string, unknown>) => {
    const { data } = await apiClient.post('/promotions', promotion);
    return data;
  },
  update: async (id: string, promotion: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/promotions/${id}`, promotion);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/promotions/${id}`);
  },
  activate: async (id: string) => {
    const { data } = await apiClient.post(`/promotions/${id}/activate`);
    return data;
  },
  deactivate: async (id: string) => {
    const { data } = await apiClient.post(`/promotions/${id}/deactivate`);
    return data;
  },
  validateCode: async (code: string, orderValue?: number) => {
    const { data } = await apiClient.post('/promotions/validate', { code, order_value: orderValue });
    return data;
  },
};

// ==================== CALL CENTER API ====================

export const callCenterApi = {
  list: async (params?: { page?: number; size?: number; search?: string; status?: string; agent_id?: string }) => {
    const { data } = await apiClient.get('/call-center/calls', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/call-center/calls/${id}`);
    return data;
  },
  create: async (call: Record<string, unknown>) => {
    const { data } = await apiClient.post('/call-center/calls', call);
    return data;
  },
  update: async (id: string, call: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/call-center/calls/${id}`, call);
    return data;
  },
  addNote: async (id: string, note: string) => {
    const { data } = await apiClient.post(`/call-center/calls/${id}/notes`, { note });
    return data;
  },
  getAgentStats: async (agentId: string, params?: { period?: string }) => {
    const { data } = await apiClient.get(`/call-center/agents/${agentId}/stats`, { params });
    return data;
  },
  getDashboard: async () => {
    const { data } = await apiClient.get('/call-center/dashboard/agent');
    return data;
  },
  getCenterDashboard: async () => {
    try {
      const { data } = await apiClient.get('/call-center/dashboard/center');
      return data;
    } catch {
      return { total_calls: 0, answered: 0, missed: 0, avg_wait_time: 0 };
    }
  },
};

// ==================== ESCALATIONS API ====================

export const escalationsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; priority?: string; assigned_to?: string }) => {
    const { data } = await apiClient.get('/escalations', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/escalations/${id}`);
    return data;
  },
  create: async (escalation: Record<string, unknown>) => {
    const { data } = await apiClient.post('/escalations', escalation);
    return data;
  },
  update: async (id: string, escalation: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/escalations/${id}`, escalation);
    return data;
  },
  assign: async (id: string, userId: string) => {
    const { data } = await apiClient.post(`/escalations/${id}/assign`, { user_id: userId });
    return data;
  },
  resolve: async (id: string, resolution: Record<string, unknown>) => {
    const { data } = await apiClient.post(`/escalations/${id}/resolve`, resolution);
    return data;
  },
  escalate: async (id: string, level: number) => {
    const { data } = await apiClient.post(`/escalations/${id}/escalate`, { level });
    return data;
  },
  getStats: async () => {
    const { data } = await apiClient.get('/escalations/stats');
    return data;
  },
};

// ==================== TECHNICIANS API ====================

export const techniciansApi = {
  list: async (params?: { page?: number; size?: number; search?: string; status?: string; skill?: string }) => {
    const { data } = await apiClient.get('/technicians', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/technicians/${id}`);
    return data;
  },
  create: async (technician: Record<string, unknown>) => {
    const { data } = await apiClient.post('/technicians', technician);
    return data;
  },
  update: async (id: string, technician: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/technicians/${id}`, technician);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/technicians/${id}`);
  },
  getSchedule: async (id: string, params?: { start_date?: string; end_date?: string }) => {
    const { data } = await apiClient.get(`/technicians/${id}/schedule`, { params });
    return data;
  },
  assignJob: async (id: string, jobId: string) => {
    const { data } = await apiClient.post(`/technicians/${id}/assign`, { job_id: jobId });
    return data;
  },
  getPerformance: async (id: string, params?: { period?: string }) => {
    const { data } = await apiClient.get(`/technicians/${id}/performance`, { params });
    return data;
  },
};

// ==================== INSTALLATIONS API ====================

export const installationsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; technician_id?: string; customer_id?: string }) => {
    const { data } = await apiClient.get('/installations', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/installations/${id}`);
    return data;
  },
  create: async (installation: Record<string, unknown>) => {
    const { data } = await apiClient.post('/installations', installation);
    return data;
  },
  update: async (id: string, installation: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/installations/${id}`, installation);
    return data;
  },
  schedule: async (id: string, scheduleData: Record<string, unknown>) => {
    const { data } = await apiClient.post(`/installations/${id}/schedule`, scheduleData);
    return data;
  },
  complete: async (id: string, completionData: Record<string, unknown>) => {
    const { data } = await apiClient.post(`/installations/${id}/complete`, completionData);
    return data;
  },
  activateWarranty: async (id: string, warrantyData: Record<string, unknown>) => {
    const { data } = await apiClient.post(`/installations/${id}/warranty/activate`, warrantyData);
    return data;
  },
  getWarranty: async (id: string) => {
    const { data } = await apiClient.get(`/installations/${id}/warranty`);
    return data;
  },
};

// ==================== FRANCHISEES API ====================

export const franchiseesApi = {
  list: async (params?: { page?: number; size?: number; search?: string; status?: string; region?: string }) => {
    const { data } = await apiClient.get('/franchisees', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/franchisees/${id}`);
    return data;
  },
  create: async (franchisee: Record<string, unknown>) => {
    const { data } = await apiClient.post('/franchisees', franchisee);
    return data;
  },
  update: async (id: string, franchisee: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/franchisees/${id}`, franchisee);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/franchisees/${id}`);
  },
  getPerformance: async (id: string, params?: { period?: string }) => {
    const { data } = await apiClient.get(`/franchisees/${id}/performance`, { params });
    return data;
  },
  getServiceability: async (id: string) => {
    const { data } = await apiClient.get(`/franchisees/${id}/serviceability`);
    return data;
  },
  updateServiceability: async (id: string, pincodes: string[]) => {
    const { data } = await apiClient.put(`/franchisees/${id}/serviceability`, { pincodes });
    return data;
  },

  // Support Tickets
  createSupportTicket: async (ticket: {
    franchisee_id: string;
    subject: string;
    description: string;
    category: 'TECHNICAL' | 'OPERATIONAL' | 'BILLING' | 'TRAINING' | 'COMPLAINT' | 'SUGGESTION';
    priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    contact_name: string;
    contact_email?: string;
    contact_phone?: string;
    attachments?: string[];
  }) => {
    const { data } = await apiClient.post('/franchisees/support', ticket);
    return data;
  },
  listSupportTickets: async (params?: {
    franchisee_id?: string;
    status?: string;
    priority?: string;
    category?: string;
    skip?: number;
    limit?: number;
  }) => {
    const { data } = await apiClient.get('/franchisees/support', { params });
    return data;
  },
  getSupportTicket: async (ticketId: string) => {
    const { data } = await apiClient.get(`/franchisees/support/${ticketId}`);
    return data;
  },
  assignSupportTicket: async (ticketId: string, assignedToId: string) => {
    const { data } = await apiClient.post(`/franchisees/support/${ticketId}/assign`, { assigned_to_id: assignedToId });
    return data;
  },
  resolveSupportTicket: async (ticketId: string, resolution: string) => {
    const { data } = await apiClient.post(`/franchisees/support/${ticketId}/resolve`, { resolution });
    return data;
  },
  escalateSupportTicket: async (ticketId: string, escalatedToId: string, reason: string) => {
    const { data } = await apiClient.post(`/franchisees/support/${ticketId}/escalate`, { escalated_to_id: escalatedToId, reason });
    return data;
  },
  closeSupportTicket: async (ticketId: string) => {
    const { data } = await apiClient.post(`/franchisees/support/${ticketId}/close`);
    return data;
  },

  // Audits
  createAudit: async (audit: {
    franchisee_id: string;
    audit_type: 'OPERATIONAL' | 'FINANCIAL' | 'COMPLIANCE' | 'QUALITY' | 'SAFETY';
    scheduled_date: string;
    auditor_name: string;
    auditor_id?: string;
    notes?: string;
  }) => {
    const { data } = await apiClient.post('/franchisees/audits', audit);
    return data;
  },
  listAudits: async (params?: {
    franchisee_id?: string;
    audit_type?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }) => {
    const { data } = await apiClient.get('/franchisees/audits', { params });
    return data;
  },
  getAudit: async (auditId: string) => {
    const { data } = await apiClient.get(`/franchisees/audits/${auditId}`);
    return data;
  },
  completeAudit: async (auditId: string, auditData: {
    actual_date: string;
    checklist?: Record<string, boolean>;
    findings?: string[];
    observations?: string;
    non_conformities?: string[];
    overall_score?: number;
    compliance_score?: number;
    quality_score?: number;
    result?: 'PASS' | 'CONDITIONAL_PASS' | 'FAIL';
    corrective_actions?: Array<{ description: string; due_date: string; assigned_to?: string }>;
    follow_up_required?: boolean;
    follow_up_date?: string;
    report_url?: string;
    evidence_urls?: string[];
  }) => {
    const { data } = await apiClient.post(`/franchisees/audits/${auditId}/complete`, auditData);
    return data;
  },
  closeAudit: async (auditId: string) => {
    const { data } = await apiClient.post(`/franchisees/audits/${auditId}/close`);
    return data;
  },
};

// ==================== PICKLISTS API ====================

export const picklistsApi = {
  list: async (params?: { page?: number; size?: number; status?: string; warehouse_id?: string }) => {
    const { data } = await apiClient.get('/picklists', { params });
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/picklists/${id}`);
    return data;
  },
  create: async (picklist: Record<string, unknown>) => {
    const { data } = await apiClient.post('/picklists', picklist);
    return data;
  },
  assign: async (id: string, pickerId: string) => {
    const { data } = await apiClient.post(`/picklists/${id}/assign`, { picker_id: pickerId });
    return data;
  },
  startPicking: async (id: string) => {
    const { data } = await apiClient.post(`/picklists/${id}/start`);
    return data;
  },
  pickItem: async (id: string, itemId: string, quantity: number) => {
    const { data } = await apiClient.post(`/picklists/${id}/items/${itemId}/pick`, { quantity });
    return data;
  },
  complete: async (id: string) => {
    const { data } = await apiClient.post(`/picklists/${id}/complete`);
    return data;
  },
  generateFromOrders: async (orderIds: string[]) => {
    const { data } = await apiClient.post('/picklists/generate', { order_ids: orderIds });
    return data;
  },
};

// ==================== BANKING API ====================

export const bankingApi = {
  // Bank Accounts
  listAccounts: async (params?: { page?: number; size?: number; is_active?: boolean }) => {
    const { data } = await apiClient.get('/banking/accounts', { params });
    return data;
  },
  getAccount: async (id: string) => {
    const { data } = await apiClient.get(`/banking/accounts/${id}`);
    return data;
  },
  createAccount: async (account: Record<string, unknown>) => {
    const { data } = await apiClient.post('/banking/accounts', account);
    return data;
  },
  updateAccount: async (id: string, account: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/banking/accounts/${id}`, account);
    return data;
  },
  // Statement Import
  importStatement: async (accountId: string, formData: FormData) => {
    const { data } = await apiClient.post(`/banking/accounts/${accountId}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  // Transactions
  listTransactions: async (accountId: string, params?: { page?: number; size?: number; status?: string; start_date?: string; end_date?: string }) => {
    const { data } = await apiClient.get(`/banking/accounts/${accountId}/transactions`, { params });
    return data;
  },
  getTransaction: async (id: string) => {
    const { data } = await apiClient.get(`/banking/transactions/${id}`);
    return data;
  },
  matchTransaction: async (id: string, matchData: Record<string, unknown>) => {
    const { data } = await apiClient.post(`/banking/transactions/${id}/match`, matchData);
    return data;
  },
  unmatchTransaction: async (id: string) => {
    const { data } = await apiClient.post(`/banking/transactions/${id}/unmatch`);
    return data;
  },
  getSuggestedMatches: async (id: string) => {
    const { data } = await apiClient.get(`/banking/transactions/${id}/suggestions`);
    return data;
  },
  // Reconciliation
  getReconciliationSummary: async (accountId: string) => {
    const { data } = await apiClient.get(`/banking/accounts/${accountId}/reconciliation`);
    return data;
  },
  reconcile: async (accountId: string, reconcileDate: string) => {
    const { data } = await apiClient.post(`/banking/accounts/${accountId}/reconcile`, { reconcile_date: reconcileDate });
    return data;
  },
  // ML-Powered Auto-Reconciliation
  getReconciliationSuggestions: async (accountId: string, params?: {
    start_date?: string;
    end_date?: string;
    min_confidence?: number;
    limit?: number;
  }) => {
    const { data } = await apiClient.get(`/banking/accounts/${accountId}/reconciliation-suggestions`, { params });
    return data;
  },
  autoReconcile: async (accountId: string, options?: {
    start_date?: string;
    end_date?: string;
    confidence_threshold?: number;
    dry_run?: boolean;
  }) => {
    const { data } = await apiClient.post(`/banking/accounts/${accountId}/auto-reconcile`, options);
    return data;
  },
  getReconciliationStats: async (accountId: string, params?: {
    start_date?: string;
    end_date?: string;
  }) => {
    const { data } = await apiClient.get(`/banking/accounts/${accountId}/reconciliation-stats`, { params });
    return data;
  },
  trainReconciliationModel: async (accountId: string) => {
    const { data } = await apiClient.post(`/banking/accounts/${accountId}/train-reconciliation-model`);
    return data;
  },
};

// ==================== CREDENTIALS API ====================

export const credentialsApi = {
  getGSTCredentials: async () => {
    const { data } = await apiClient.get('/credentials/gst');
    return data;
  },
  saveGSTCredentials: async (credentials: { einvoice_username?: string; einvoice_password?: string; ewb_username?: string; ewb_password?: string }) => {
    const { data } = await apiClient.post('/credentials/gst', credentials);
    return data;
  },
  testGSTConnection: async (type: 'einvoice' | 'ewaybill') => {
    const { data } = await apiClient.post(`/credentials/gst/test/${type}`);
    return data;
  },
  rotateEncryptionKey: async () => {
    const { data } = await apiClient.post('/credentials/rotate-key');
    return data;
  },
};

// ==================== MARKETPLACES API ====================

export const marketplacesApi = {
  list: async () => {
    const { data } = await apiClient.get('/marketplaces/integrations');
    return data;
  },
  listIntegrations: async () => {
    const { data } = await apiClient.get('/marketplaces/integrations');
    return data;
  },
  getById: async (id: string) => {
    const { data } = await apiClient.get(`/marketplaces/integrations/${id}`);
    return data;
  },
  create: async (integration: Record<string, unknown>) => {
    const { data } = await apiClient.post('/marketplaces/integrations', integration);
    return data;
  },
  createIntegration: async (integration: object) => {
    const { data } = await apiClient.post('/marketplaces/integrations', integration);
    return data;
  },
  update: async (id: string, integration: Record<string, unknown>) => {
    const { data } = await apiClient.put(`/marketplaces/integrations/${id}`, integration);
    return data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/marketplaces/integrations/${id}`);
  },
  deleteIntegration: async (marketplaceType: string) => {
    await apiClient.delete(`/marketplaces/integrations/${marketplaceType}`);
  },
  toggleIntegration: async (marketplaceType: string, isActive: boolean) => {
    const { data } = await apiClient.patch(`/marketplaces/integrations/${marketplaceType}`, { is_active: isActive });
    return data;
  },
  testConnection: async (id: string) => {
    const { data } = await apiClient.post(`/marketplaces/integrations/${id}/test`);
    return data;
  },
  syncOrders: async (id: string, params?: { from_date?: string }) => {
    const { data } = await apiClient.post(`/marketplaces/integrations/${id}/sync/orders`, null, { params });
    return data;
  },
  syncInventory: async (id: string) => {
    const { data } = await apiClient.post(`/marketplaces/integrations/${id}/sync/inventory`);
    return data;
  },
  getOrders: async (id: string, params?: { page?: number; size?: number; status?: string }) => {
    const { data } = await apiClient.get(`/marketplaces/integrations/${id}/orders`, { params });
    return data;
  },
  getSyncHistory: async (id: string) => {
    const { data } = await apiClient.get(`/marketplaces/integrations/${id}/sync-history`);
    return data;
  },
};

// ==================== AUTO JOURNAL API ====================

export const autoJournalApi = {
  generateFromInvoice: async (invoiceId: string, autoPost?: boolean) => {
    const { data } = await apiClient.post('/auto-journal/generate/from-invoice', {
      invoice_id: invoiceId,
      auto_post: autoPost
    });
    return data;
  },
  generateFromReceipt: async (receiptId: string, bankAccountCode?: string, autoPost?: boolean) => {
    const { data } = await apiClient.post('/auto-journal/generate/from-receipt', {
      receipt_id: receiptId,
      bank_account_code: bankAccountCode,
      auto_post: autoPost
    });
    return data;
  },
  generateFromBankTransaction: async (transactionId: string, contraAccountCode: string, autoPost?: boolean) => {
    const { data } = await apiClient.post('/auto-journal/generate/from-bank-transaction', {
      bank_transaction_id: transactionId,
      contra_account_code: contraAccountCode,
      auto_post: autoPost
    });
    return data;
  },
  generateBulk: async (invoiceIds?: string[], receiptIds?: string[], autoPost?: boolean) => {
    const { data } = await apiClient.post('/auto-journal/generate/bulk', {
      invoice_ids: invoiceIds,
      receipt_ids: receiptIds,
      auto_post: autoPost
    });
    return data;
  },
  bulkGenerate: async (invoiceIds?: string[], receiptIds?: string[], autoPost?: boolean) => {
    const { data } = await apiClient.post('/auto-journal/generate/bulk', {
      invoice_ids: invoiceIds,
      receipt_ids: receiptIds,
      auto_post: autoPost
    });
    return data;
  },
  postJournal: async (journalId: string) => {
    const { data } = await apiClient.post(`/auto-journal/journals/${journalId}/post`);
    return data;
  },
  listPending: async (params?: { skip?: number; limit?: number }) => {
    const { data } = await apiClient.get('/auto-journal/journals/pending', { params });
    return data;
  },
  listPendingJournals: async (params?: { skip?: number; limit?: number }) => {
    const { data } = await apiClient.get('/auto-journal/journals/pending', { params });
    return data;
  },
  postAllPending: async () => {
    const { data } = await apiClient.post('/auto-journal/journals/post-all');
    return data;
  },
};

// ==================== TDS API ====================

export const tdsApi = {
  calculate: async (amount: number, section: string, panAvailable?: boolean, lowerDeductionRate?: number) => {
    const { data } = await apiClient.post('/tds/calculate', {
      amount,
      section,
      pan_available: panAvailable,
      lower_deduction_rate: lowerDeductionRate
    });
    return data;
  },
  recordDeduction: async (deduction: Record<string, unknown>) => {
    const { data } = await apiClient.post('/tds/deductions', deduction);
    return data;
  },
  listDeductions: async (params?: {
    financial_year?: string;
    quarter?: string;
    status?: string;
    section?: string;
    deductee_pan?: string;
    skip?: number;
    limit?: number
  }) => {
    const { data } = await apiClient.get('/tds/deductions', { params });
    return data;
  },
  getDeduction: async (id: string) => {
    const { data } = await apiClient.get(`/tds/deductions/${id}`);
    return data;
  },
  getPendingDeposits: async (financialYear?: string) => {
    const { data } = await apiClient.get('/tds/pending-deposits', { params: { financial_year: financialYear } });
    return data;
  },
  markDeposited: async (deductionIds: string[], depositDate: string, challanNumber: string, challanDate: string, bsrCode: string, cin?: string) => {
    const { data } = await apiClient.post('/tds/mark-deposited', {
      deduction_ids: deductionIds,
      deposit_date: depositDate,
      challan_number: challanNumber,
      challan_date: challanDate,
      bsr_code: bsrCode,
      cin
    });
    return data;
  },
  generateForm16A: async (deducteePan: string, financialYear: string, quarter: string) => {
    const { data } = await apiClient.post('/tds/form-16a/generate', {
      deductee_pan: deducteePan,
      financial_year: financialYear,
      quarter
    });
    return data;
  },
  downloadForm16A: async (deducteePan: string, financialYear: string, quarter: string) => {
    const { data } = await apiClient.post('/tds/form-16a/download', {
      deductee_pan: deducteePan,
      financial_year: financialYear,
      quarter
    });
    return data;
  },
  getSummary: async (financialYear: string) => {
    const { data } = await apiClient.get('/tds/summary', { params: { financial_year: financialYear } });
    return data;
  },
  getSections: async () => {
    const { data } = await apiClient.get('/tds/sections');
    return data;
  },
};

// ==================== PAYMENTS API (RAZORPAY) ====================

export const paymentsApi = {
  createOrder: async (amount: number, currency?: string, receipt?: string, notes?: Record<string, string>) => {
    const { data } = await apiClient.post('/payments/create-order', { amount, currency, receipt, notes });
    return data;
  },
  verifyPayment: async (razorpayOrderId: string, razorpayPaymentId: string, razorpaySignature: string) => {
    const { data } = await apiClient.post('/payments/verify', {
      razorpay_order_id: razorpayOrderId,
      razorpay_payment_id: razorpayPaymentId,
      razorpay_signature: razorpaySignature
    });
    return data;
  },
  getPayment: async (paymentId: string) => {
    const { data } = await apiClient.get(`/payments/${paymentId}`);
    return data;
  },
  listPayments: async (params?: { page?: number; size?: number; status?: string; customer_id?: string }) => {
    const { data } = await apiClient.get('/payments', { params });
    return data;
  },
  refund: async (paymentId: string, amount?: number, reason?: string) => {
    const { data } = await apiClient.post(`/payments/${paymentId}/refund`, { amount, reason });
    return data;
  },
};

// ==================== CUSTOMER PORTAL API ====================

export const portalApi = {
  getDashboard: async (customerId: string) => {
    const { data } = await apiClient.get('/portal/dashboard', { params: { customer_id: customerId } });
    return data;
  },
  getProfile: async (customerId: string) => {
    const { data } = await apiClient.get('/portal/profile', { params: { customer_id: customerId } });
    return data;
  },
  updateProfile: async (customerId: string, profile: Record<string, unknown>) => {
    const { data } = await apiClient.put('/portal/profile', profile, { params: { customer_id: customerId } });
    return data;
  },
  getOrders: async (customerId: string, params?: { status?: string; skip?: number; limit?: number }) => {
    const { data } = await apiClient.get('/portal/orders', { params: { customer_id: customerId, ...params } });
    return data;
  },
  getOrderDetails: async (customerId: string, orderId: string) => {
    const { data } = await apiClient.get(`/portal/orders/${orderId}`, { params: { customer_id: customerId } });
    return data;
  },
  trackOrder: async (customerId: string, orderId: string) => {
    const { data } = await apiClient.get(`/portal/orders/${orderId}/track`, { params: { customer_id: customerId } });
    return data;
  },
  getInvoices: async (customerId: string, params?: { skip?: number; limit?: number }) => {
    const { data } = await apiClient.get('/portal/invoices', { params: { customer_id: customerId, ...params } });
    return data;
  },
  getInvoiceDetails: async (customerId: string, invoiceId: string) => {
    const { data } = await apiClient.get(`/portal/invoices/${invoiceId}`, { params: { customer_id: customerId } });
    return data;
  },
  downloadInvoice: async (customerId: string, invoiceId: string) => {
    const { data } = await apiClient.get(`/portal/invoices/${invoiceId}/download`, { params: { customer_id: customerId } });
    return data;
  },
  getServiceRequests: async (customerId: string, params?: { status?: string; skip?: number; limit?: number }) => {
    const { data } = await apiClient.get('/portal/service-requests', { params: { customer_id: customerId, ...params } });
    return data;
  },
  createServiceRequest: async (customerId: string, request: Record<string, unknown>) => {
    const { data } = await apiClient.post('/portal/service-requests', request, { params: { customer_id: customerId } });
    return data;
  },
  getServiceRequestDetails: async (customerId: string, requestId: string) => {
    const { data } = await apiClient.get(`/portal/service-requests/${requestId}`, { params: { customer_id: customerId } });
    return data;
  },
  addServiceRequestComment: async (customerId: string, requestId: string, comment: string) => {
    const { data } = await apiClient.post(`/portal/service-requests/${requestId}/comments`, { comment }, { params: { customer_id: customerId } });
    return data;
  },
  submitFeedback: async (customerId: string, requestId: string, rating: number, comments?: string) => {
    const { data } = await apiClient.post(`/portal/service-requests/${requestId}/feedback`, { rating, comments }, { params: { customer_id: customerId } });
    return data;
  },
  getLoyaltySummary: async (customerId: string) => {
    const { data } = await apiClient.get('/portal/loyalty', { params: { customer_id: customerId } });
    return data;
  },
};

// S&OP (Sales & Operations Planning) API
export const snopApi = {
  // Dashboard
  getDashboard: async () => {
    const { data } = await apiClient.get('/snop/dashboard');
    return data;
  },
  getDemandSupplyGap: async () => {
    const { data } = await apiClient.get('/snop/dashboard/demand-supply-gap');
    return data;
  },
  // Forecasts
  getForecasts: async (params?: { granularity?: string; level?: string; warehouse_id?: string; skip?: number; limit?: number }) => {
    const { data } = await apiClient.get('/snop/forecasts', { params });
    return data;
  },
  generateForecast: async (payload: { granularity: string; level: string; horizon_periods: number }) => {
    const { data } = await apiClient.post('/snop/forecast/generate', {
      granularity: payload.granularity || 'WEEKLY',
      forecast_level: payload.level || 'SKU',
      forecast_horizon_days: (payload.horizon_periods || 12) * 7,
    });
    return data;
  },
  // Supply Plans
  getSupplyPlans: async (params?: { skip?: number; limit?: number }) => {
    const { data } = await apiClient.get('/snop/supply-plans', { params });
    return data;
  },
  createSupplyPlan: async (payload: Record<string, unknown>) => {
    const { data } = await apiClient.post('/snop/supply-plans', payload);
    return data;
  },
  // Scenarios
  getScenarios: async (params?: { skip?: number; limit?: number }) => {
    const { data } = await apiClient.get('/snop/scenarios', { params });
    return data;
  },
  createScenario: async (payload: Record<string, unknown>) => {
    const { data } = await apiClient.post('/snop/scenarios', payload);
    return data;
  },
  runScenario: async (scenarioId: string) => {
    const { data } = await apiClient.post(`/snop/scenarios/${scenarioId}/run`);
    return data;
  },
  // Inventory Optimization
  getOptimizations: async (params?: { skip?: number; limit?: number; warehouse_id?: string; region_id?: string; cluster_id?: string }) => {
    const { data } = await apiClient.get('/snop/inventory/optimizations', { params });
    return data;
  },
  runOptimization: async () => {
    const { data } = await apiClient.post('/snop/inventory/optimize', {});
    return data;
  },
  // Inventory Network Health (Geo Drill-Down)
  getNetworkHealth: async (params?: { region_id?: string; cluster_id?: string; warehouse_id?: string }) => {
    const { data } = await apiClient.get('/snop/inventory/network-health', { params });
    return data;
  },
  getWarehouseDetail: async (warehouseId: string, params?: { product_id?: string }) => {
    const { data } = await apiClient.get(`/snop/inventory/warehouse-detail/${warehouseId}`, { params });
    return data;
  },
  getForecastAccuracyGeo: async (params: { start_date: string; end_date: string; region_id?: string; cluster_id?: string; warehouse_id?: string }) => {
    const { data } = await apiClient.get('/snop/inventory/forecast-accuracy-geo', { params });
    return data;
  },
  getAvailabilityVsForecast: async (params: { warehouse_id: string; product_id?: string; horizon_days?: number }) => {
    const { data } = await apiClient.get('/snop/inventory/availability-vs-forecast', { params });
    return data;
  },
};

// Company API
import type { Company as CompanyType, CompanyBankAccount, CompanyBankAccountCreate, CompanyBankAccountUpdate } from '@/types/company';
export type { Company } from '@/types/company';
type Company = CompanyType;

export const companyApi = {
  // Get primary company with branches and bank accounts
  getPrimary: async (): Promise<Company> => {
    const { data } = await apiClient.get<Company>('/company/primary');
    return data;
  },

  // Update primary company
  updatePrimary: async (company: Partial<Company>): Promise<Company> => {
    const { data } = await apiClient.put<Company>('/company/primary', company);
    return data;
  },

  // List all companies
  list: async (params?: { is_active?: boolean }) => {
    const { data } = await apiClient.get<{ items: Company[]; total: number }>('/company', { params });
    return data;
  },

  // Get company by ID
  getById: async (id: string): Promise<Company> => {
    const { data } = await apiClient.get<Company>(`/company/${id}`);
    return data;
  },

  // Update company by ID
  update: async (id: string, company: Partial<Company>) => {
    const { data } = await apiClient.put<Company>(`/company/${id}`, company);
    return data;
  },

  // Bank Accounts
  listBankAccounts: async (companyId: string): Promise<CompanyBankAccount[]> => {
    if (!companyId) {
      throw new Error('Company ID is required to list bank accounts');
    }
    const { data } = await apiClient.get<CompanyBankAccount[]>(`/company/${companyId}/bank-accounts`);
    return data;
  },

  createBankAccount: async (companyId: string, account: CompanyBankAccountCreate): Promise<CompanyBankAccount> => {
    if (!companyId) {
      throw new Error('Company ID is required to create bank account');
    }
    const { data } = await apiClient.post<CompanyBankAccount>(`/company/${companyId}/bank-accounts`, account);
    return data;
  },

  updateBankAccount: async (companyId: string, accountId: string, account: CompanyBankAccountUpdate): Promise<CompanyBankAccount> => {
    if (!companyId || !accountId) {
      throw new Error('Company ID and Account ID are required to update bank account');
    }
    const { data } = await apiClient.put<CompanyBankAccount>(`/company/${companyId}/bank-accounts/${accountId}`, account);
    return data;
  },

  deleteBankAccount: async (companyId: string, accountId: string): Promise<void> => {
    if (!companyId || !accountId) {
      throw new Error('Company ID and Account ID are required to delete bank account');
    }
    await apiClient.delete(`/company/${companyId}/bank-accounts/${accountId}`);
  },

  setPrimaryBankAccount: async (companyId: string, accountId: string): Promise<CompanyBankAccount> => {
    if (!companyId || !accountId) {
      throw new Error('Company ID and Account ID are required to set primary bank account');
    }
    const { data } = await apiClient.put<CompanyBankAccount>(`/company/${companyId}/bank-accounts/${accountId}`, { is_primary: true });
    return data;
  },
};

// ==================== GST REPORTS API ====================

export const gstReportsApi = {
  // GSTR-1 (Outward Supplies)
  getGSTR1: async (month: number, year: number) => {
    const { data } = await apiClient.get('/billing/reports/gstr1', { params: { month, year } });
    return data;
  },

  // GSTR-2A (Inward Supplies)
  getGSTR2A: async (month: number, year: number) => {
    const { data } = await apiClient.get('/billing/reports/gstr2a', { params: { month, year } });
    return data;
  },

  // GSTR-3B (Monthly Summary)
  getGSTR3B: async (month: number, year: number) => {
    const { data } = await apiClient.get('/billing/reports/gstr3b', { params: { month, year } });
    return data;
  },

  // HSN Summary
  getHSNSummary: async (month: number, year: number) => {
    const { data } = await apiClient.get('/billing/reports/hsn-summary', { params: { month, year } });
    return data;
  },

  // Finance Dashboard Stats
  getFinanceDashboard: async () => {
    const { data } = await apiClient.get('/billing/reports/finance-dashboard');
    return data;
  },
};

// ==================== GST E-FILING API ====================

export interface GSTFilingStatus {
  return_type: string;
  period: string;
  status: string;
  arn?: string;
  filed_at?: string;
  acknowledgement_number?: string;
}

export interface ITCEntry {
  id: string;
  vendor_gstin: string;
  vendor_name?: string;
  invoice_number: string;
  invoice_date: string;
  cgst_itc: number;
  sgst_itc: number;
  igst_itc: number;
  cess_itc: number;
  status: string;
  gstr2a_matched: boolean;
  gstr2b_matched: boolean;
}

export const gstFilingApi = {
  // GST Portal Authentication
  authenticate: async () => {
    const { data } = await apiClient.post('/gst/authenticate');
    return data;
  },

  // File GSTR-1 (Outward Supplies)
  fileGSTR1: async (month: number, year: number, options?: { preview?: boolean }) => {
    const { data } = await apiClient.post('/gst/file/gstr1', { month, year, ...options });
    return data;
  },

  // File GSTR-3B (Monthly Summary)
  fileGSTR3B: async (month: number, year: number, options?: { preview?: boolean }) => {
    const { data } = await apiClient.post('/gst/file/gstr3b', { month, year, ...options });
    return data;
  },

  // Get Filing Status
  getFilingStatus: async (returnType: string, period: string) => {
    const { data } = await apiClient.get<GSTFilingStatus>('/gst/filing-status', {
      params: { return_type: returnType, period }
    });
    return data;
  },

  // Download GSTR-2A (Inward Supplies from Portal)
  downloadGSTR2A: async (month: number, year: number) => {
    const { data } = await apiClient.get('/gst/download/gstr2a', { params: { month, year } });
    return data;
  },

  // GST Filing Dashboard
  getDashboard: async (params?: { year?: number }) => {
    const { data } = await apiClient.get('/gst/dashboard', { params });
    return data;
  },

  // Filing History
  getFilingHistory: async (params?: { page?: number; size?: number; limit?: number; return_type?: string }) => {
    // Normalize: use 'size' as the standard param, allow 'limit' as alias
    const normalizedParams = params ? {
      page: params.page,
      size: params.size || params.limit,
      return_type: params.return_type,
    } : undefined;
    const { data } = await apiClient.get('/gst/filing-history', { params: normalizedParams });
    return data;
  },
};

// ==================== ITC (INPUT TAX CREDIT) API ====================

export const itcApi = {
  // Get Available ITC
  getAvailableITC: async (period: string) => {
    const { data } = await apiClient.get('/gst/itc/available', { params: { period } });
    return data;
  },

  // Reconcile ITC with GSTR-2A
  reconcileWithGSTR2A: async (month: number, year: number) => {
    const { data } = await apiClient.post('/gst/itc/reconcile', { month, year, source: 'GSTR2A' });
    return data;
  },

  // Reconcile ITC with GSTR-2B
  reconcileWithGSTR2B: async (month: number, year: number) => {
    const { data } = await apiClient.post('/gst/itc/reconcile', { month, year, source: 'GSTR2B' });
    return data;
  },

  // Get ITC Ledger
  getLedger: async (params?: {
    page?: number;
    size?: number;
    limit?: number;
    period?: string;
    status?: string;
    vendor_gstin?: string;
  }) => {
    // Normalize: use 'size' as the standard param, allow 'limit' as alias
    const normalizedParams = params ? {
      page: params.page,
      size: params.size || params.limit,
      period: params.period,
      status: params.status,
      vendor_gstin: params.vendor_gstin,
    } : undefined;
    const { data } = await apiClient.get('/gst/itc/ledger', { params: normalizedParams });
    return data;
  },

  // Get ITC Summary
  getSummary: async (period: string) => {
    const { data } = await apiClient.get('/gst/itc/summary', { params: { period } });
    return data;
  },

  // Utilize ITC
  utilizeITC: async (utilizationData: {
    period: string;
    cgst_utilized: number;
    sgst_utilized: number;
    igst_utilized: number;
  }) => {
    const { data } = await apiClient.post('/gst/itc/utilize', utilizationData);
    return data;
  },

  // Reverse ITC
  reverseITC: async (entryId: string, reason: string, amount?: number) => {
    const { data } = await apiClient.post(`/gst/itc/${entryId}/reverse`, { reason, amount });
    return data;
  },

  // Get Mismatch Report (ITC vs GSTR-2A/2B)
  getMismatchReport: async (period: string) => {
    const { data } = await apiClient.get('/gst/itc/mismatch-report', { params: { period } });
    return data;
  },
};

// ==================== UPLOADS API ====================

export interface UploadResponse {
  url: string;
  thumbnail_url?: string;
  filename: string;
  size: number;
  content_type: string;
}

export const uploadsApi = {
  uploadImage: async (file: File, category: string = 'products'): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    const { data } = await apiClient.post<UploadResponse>('/uploads/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  uploadImages: async (files: File[], category: string = 'products'): Promise<{ files: UploadResponse[]; total: number }> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    formData.append('category', category);
    const { data } = await apiClient.post('/uploads/images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  uploadDocument: async (file: File, category: string = 'documents'): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    const { data } = await apiClient.post<UploadResponse>('/uploads/document', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  deleteFile: async (url: string): Promise<{ success: boolean; message: string }> => {
    const { data } = await apiClient.delete('/uploads', { data: { url } });
    return data;
  },
};

// ==================== COMMUNITY PARTNERS API ====================

export interface CommunityPartner {
  id: string;
  partner_code: string;
  referral_code: string;
  status: string;
  tier_id?: string;

  // Basic Info
  full_name: string;
  phone: string;
  email?: string;

  // Address
  address_line1?: string;
  address_line2?: string;
  city?: string;
  district?: string;
  state?: string;
  pincode?: string;

  // Profile
  profile_photo_url?: string;
  date_of_birth?: string;
  gender?: string;
  partner_type?: string;
  occupation?: string;

  // KYC Status
  kyc_status: string;
  kyc_verified_at?: string;
  kyc_rejection_reason?: string;
  aadhaar_verified: boolean;
  pan_verified: boolean;
  bank_verified: boolean;

  // Performance Metrics (match backend field names)
  total_sales_count: number;
  total_sales_value: number;
  total_commission_earned: number;
  total_commission_paid: number;
  current_month_sales: number;
  current_month_value: number;
  wallet_balance: number;

  // Training
  training_completed: boolean;

  // Timestamps
  registered_at?: string;
  created_at: string;
  updated_at: string;
  activated_at?: string;
  last_login_at?: string;

  // Related
  tier?: PartnerTier;
}

export interface PartnerTier {
  id: string;
  name: string;
  code: string;
  level: number;
  description?: string;

  // Requirements (match backend field names)
  min_monthly_sales: number;
  min_monthly_value: number;
  max_monthly_sales?: number;

  // Commission & Bonuses
  commission_percentage: number;
  bonus_percentage: number;
  milestone_bonus: number;
  referral_bonus: number;

  // Display
  badge_color?: string;
  badge_icon_url?: string;
  benefits?: Record<string, unknown>;

  // Flags
  is_active: boolean;
  is_default: boolean;

  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface PartnerCommission {
  id: string;
  partner_id: string;
  order_id: string;
  order_amount: number;
  commission_rate: number;
  commission_amount: number;
  status: string;
  approved_at?: string;
  paid_at?: string;
  created_at: string;
}

export interface PartnerPayout {
  id: string;
  partner_id: string;
  amount: number;
  status: string;
  bank_reference?: string;
  failure_reason?: string;
  requested_at: string;
  processed_at?: string;
}

export interface PartnerOrder {
  id: string;
  order_id: string;
  order_number: string;
  order_amount: number;
  commission_amount: number;
  customer_name?: string;
  order_status: string;
  created_at: string;
}

export interface PartnerAnalytics {
  total_partners: number;
  active_partners: number;
  pending_kyc: number;
  total_orders: number;
  total_sales: number;
  total_commissions_paid: number;
  pending_payouts: number;
  partners_by_tier: Record<string, number>;
  partners_by_state: Record<string, number>;
}

export const partnersApi = {
  // Admin endpoints
  list: async (params?: { page?: number; size?: number; status?: string; kyc_status?: string; state?: string; search?: string }) => {
    const { data } = await apiClient.get<{
      items: CommunityPartner[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    }>('/partners', { params: { ...params, page_size: params?.size } });
    return data;
  },

  getById: async (id: string) => {
    const { data } = await apiClient.get<CommunityPartner>(`/partners/${id}`);
    return data;
  },

  update: async (partnerId: string, updateData: Partial<CommunityPartner>) => {
    const { data } = await apiClient.put<CommunityPartner>(`/partners/${partnerId}`, updateData);
    return data;
  },

  delete: async (partnerId: string) => {
    await apiClient.delete(`/partners/${partnerId}`);
  },

  verifyKyc: async (partnerId: string, verification: { status: 'VERIFIED' | 'REJECTED'; notes?: string }) => {
    const { data } = await apiClient.post<CommunityPartner>(`/partners/${partnerId}/verify-kyc`, verification);
    return data;
  },

  suspend: async (partnerId: string, reason: string) => {
    const { data } = await apiClient.post<CommunityPartner>(`/partners/${partnerId}/suspend`, null, { params: { reason } });
    return data;
  },

  activate: async (partnerId: string) => {
    const { data } = await apiClient.post<CommunityPartner>(`/partners/${partnerId}/activate`);
    return data;
  },

  getAnalytics: async () => {
    const { data } = await apiClient.get<PartnerAnalytics>('/partners/analytics/summary');
    return data;
  },

  // Tiers
  getTiers: async () => {
    const { data } = await apiClient.get<PartnerTier[]>('/partners/tiers');
    return data;
  },

  // Commissions
  getCommissions: async (partnerId: string, params?: { page?: number; size?: number; status?: string }) => {
    const { data } = await apiClient.get<{
      items: PartnerCommission[];
      page: number;
      page_size: number;
    }>(`/partners/${partnerId}/commissions`, { params: { ...params, page_size: params?.size } });
    return data;
  },

  approveCommission: async (commissionId: string) => {
    const { data } = await apiClient.post<PartnerCommission>(`/partners/commissions/${commissionId}/approve`);
    return data;
  },

  // Payouts
  processPayout: async (payoutId: string, params: { reference?: string; success: boolean; failure_reason?: string }) => {
    const { data } = await apiClient.post<PartnerPayout>(`/partners/payouts/${payoutId}/process`, null, { params });
    return data;
  },

  // Partner orders (for admin view)
  getPartnerOrders: async (partnerId: string, params?: { page?: number; size?: number }) => {
    // This uses the public endpoint which works for admin too
    const { data } = await apiClient.get<{
      items: PartnerOrder[];
      page: number;
      page_size: number;
    }>('/partners/me/orders', { params: { partner_id: partnerId, ...params, page_size: params?.size } });
    return data;
  },

  // Get partner payouts (admin view - stub until backend endpoint is implemented)
  getPayouts: async (partnerId: string, params?: { page?: number; size?: number }) => {
    // TODO: Implement backend endpoint GET /partners/{partnerId}/payouts
    // For now return empty data to prevent build errors
    return {
      items: [] as Array<{
        id: string;
        partner_id: string;
        amount: number;
        status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
        requested_at: string;
        processed_at?: string;
        bank_reference?: string;
      }>,
      page: params?.page || 1,
      page_size: params?.size || 20,
    };
  },
};

export default apiClient;
export { onboardingApi } from './onboarding';
