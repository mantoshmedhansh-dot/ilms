import axios from 'axios';
import {
  StorefrontProduct,
  StorefrontCategory,
  StorefrontBrand,
  PaginatedResponse,
  ProductFilters,
  StockVerificationRequest,
  StockVerificationResponse,
  D2COrderRequest,
  D2COrderResponse,
  CompanyInfo,
} from '@/types/storefront';
import { useAuthStore, CustomerProfile, CustomerAddress } from './auth-store';

// Create a separate axios instance for storefront
// withCredentials: true ensures httpOnly cookies are sent with requests
const storefrontClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
  withCredentials: true, // Send httpOnly cookies with requests
  headers: {
    'Content-Type': 'application/json',
  },
});

// API base paths
const API_PATH = '/api/v1';
const STOREFRONT_PATH = '/api/v1/storefront';

// Products API - Uses public storefront endpoints
export const productsApi = {
  list: async (filters?: ProductFilters): Promise<PaginatedResponse<StorefrontProduct>> => {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.category_id) params.append('category_id', filters.category_id);
      if (filters.brand_id) params.append('brand_id', filters.brand_id);
      if (filters.min_price) params.append('min_price', filters.min_price.toString());
      if (filters.max_price) params.append('max_price', filters.max_price.toString());
      if (filters.is_featured) params.append('is_featured', 'true');
      if (filters.is_bestseller) params.append('is_bestseller', 'true');
      if (filters.is_new_arrival) params.append('is_new_arrival', 'true');
      if (filters.search) params.append('search', filters.search);
      if (filters.sort_by) params.append('sort_by', filters.sort_by);
      if (filters.sort_order) params.append('sort_order', filters.sort_order);
      if (filters.page) params.append('page', filters.page.toString());
      if (filters.size) params.append('size', filters.size.toString());
    }

    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products?${params.toString()}`);
    return data;
  },

  getBySlug: async (slug: string): Promise<StorefrontProduct> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products/${slug}`);
    return data;
  },

  getById: async (id: string): Promise<StorefrontProduct> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products/${id}`);
    return data;
  },

  getFeatured: async (limit = 8): Promise<StorefrontProduct[]> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products?is_featured=true&size=${limit}`);
    return data.items || [];
  },

  getBestsellers: async (limit = 8): Promise<StorefrontProduct[]> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products?is_bestseller=true&size=${limit}`);
    return data.items || [];
  },

  getNewArrivals: async (limit = 8): Promise<StorefrontProduct[]> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products?is_new_arrival=true&size=${limit}&sort_by=created_at&sort_order=desc`);
    return data.items || [];
  },

  getRelated: async (productId: string, categoryId?: string, limit = 4): Promise<StorefrontProduct[]> => {
    const params = new URLSearchParams();
    params.append('size', limit.toString());
    if (categoryId) params.append('category_id', categoryId);

    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products?${params.toString()}`);
    // Filter out the current product
    return (data.items || []).filter((p: StorefrontProduct) => p.id !== productId);
  },

  // Compare products - fetches full product details with specifications
  compare: async (productIds: string[]): Promise<{
    products: StorefrontProduct[];
    specifications: Record<string, string[]>;
    comparison_attributes: string[];
  }> => {
    if (productIds.length === 0) {
      return { products: [], specifications: {}, comparison_attributes: [] };
    }

    const params = new URLSearchParams();
    params.append('product_ids', productIds.join(','));

    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products/compare?${params.toString()}`);
      return data;
    } catch (error) {
      // Fallback: fetch products individually if compare endpoint not available
      const products = await Promise.all(
        productIds.map(async (id) => {
          try {
            const product = await productsApi.getById(id);
            return product;
          } catch {
            return null;
          }
        })
      );

      const validProducts = products.filter((p): p is StorefrontProduct => p !== null);

      // Extract all unique specification keys
      const allSpecs = new Set<string>();
      validProducts.forEach((p) => {
        p.specifications?.forEach((spec) => {
          allSpecs.add(spec.key);
        });
      });

      return {
        products: validProducts,
        specifications: {},
        comparison_attributes: Array.from(allSpecs),
      };
    }
  },
};

// Categories API - Uses public storefront endpoints
export const categoriesApi = {
  list: async (): Promise<StorefrontCategory[]> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/categories`);
    return data || [];
  },

  getTree: async (): Promise<StorefrontCategory[]> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/categories`);
    return data || [];
  },

  getBySlug: async (slug: string): Promise<StorefrontCategory> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/categories`);

    // Recursive function to search through category tree (including nested children)
    const findCategoryBySlug = (categories: StorefrontCategory[], targetSlug: string): StorefrontCategory | null => {
      for (const cat of categories) {
        if (cat.slug === targetSlug) {
          return cat;
        }
        // Search in children recursively
        if (cat.children && cat.children.length > 0) {
          const found = findCategoryBySlug(cat.children, targetSlug);
          if (found) return found;
        }
      }
      return null;
    };

    const category = findCategoryBySlug(data || [], slug);
    if (!category) throw new Error('Category not found');
    return category;
  },

  getById: async (id: string): Promise<StorefrontCategory> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/categories`);

    // Recursive function to search through category tree (including nested children)
    const findCategoryById = (categories: StorefrontCategory[], targetId: string): StorefrontCategory | null => {
      for (const cat of categories) {
        if (cat.id === targetId) {
          return cat;
        }
        // Search in children recursively
        if (cat.children && cat.children.length > 0) {
          const found = findCategoryById(cat.children, targetId);
          if (found) return found;
        }
      }
      return null;
    };

    const category = findCategoryById(data || [], id);
    if (!category) throw new Error('Category not found');
    return category;
  },

  getFeatured: async (): Promise<StorefrontCategory[]> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/categories`);
    return data || [];
  },
};

// Brands API - Uses public storefront endpoints
export const brandsApi = {
  list: async (): Promise<StorefrontBrand[]> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/brands`);
    return data || [];
  },

  getBySlug: async (slug: string): Promise<StorefrontBrand> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/brands`);
    const brand = (data || []).find((b: StorefrontBrand) => b.slug === slug);
    if (!brand) throw new Error('Brand not found');
    return brand;
  },

  getById: async (id: string): Promise<StorefrontBrand> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/brands`);
    const brand = (data || []).find((b: StorefrontBrand) => b.id === id);
    if (!brand) throw new Error('Brand not found');
    return brand;
  },
};

// Search API types
export interface SearchProductSuggestion {
  id: string;
  name: string;
  slug: string;
  image_url?: string;
  price: number;
  mrp: number;
}

export interface SearchCategorySuggestion {
  id: string;
  name: string;
  slug: string;
  image_url?: string;
  product_count: number;
}

export interface SearchBrandSuggestion {
  id: string;
  name: string;
  slug: string;
  logo_url?: string;
}

export interface SearchSuggestionsResponse {
  products: SearchProductSuggestion[];
  categories: SearchCategorySuggestion[];
  brands: SearchBrandSuggestion[];
  query: string;
}

// Inventory API
export const inventoryApi = {
  verifyStock: async (request: StockVerificationRequest): Promise<StockVerificationResponse> => {
    try {
      const { data } = await storefrontClient.post(`${API_PATH}/inventory/verify-stock`, request);
      return data;
    } catch {
      // Return default response if endpoint doesn't exist
      return {
        product_id: request.product_id,
        in_stock: true,
        available_quantity: 100,
        requested_quantity: request.quantity,
        message: 'Stock available',
      };
    }
  },

  verifyStockBulk: async (requests: StockVerificationRequest[]): Promise<StockVerificationResponse[]> => {
    try {
      const { data } = await storefrontClient.post(`${API_PATH}/inventory/verify-stock-bulk`, { items: requests });
      return data;
    } catch {
      // Return default responses if endpoint doesn't exist
      return requests.map(req => ({
        product_id: req.product_id,
        in_stock: true,
        available_quantity: 100,
        requested_quantity: req.quantity,
        message: 'Stock available',
      }));
    }
  },

  checkDelivery: async (pincode: string): Promise<{
    serviceable: boolean;
    estimate_days?: number;
    message?: string;
    cod_available?: boolean;
    shipping_cost?: number;
    zone?: string;
    city?: string;
    state?: string;
  }> => {
    // Use edge-based serviceability for instant response (<10ms)
    // Falls back to API only when edge data unavailable
    const { checkServiceability, checkServiceabilityWithFallback } = await import('./serviceability-store');

    // First try instant lookup from edge/localStorage
    const edgeResult = checkServiceability(pincode);

    if (edgeResult.serviceable) {
      return {
        serviceable: true,
        estimate_days: edgeResult.estimated_days || undefined,
        message: `Delivery available in ${edgeResult.estimated_days || 3-5} days`,
        cod_available: edgeResult.cod_available,
        shipping_cost: edgeResult.shipping_cost,
        zone: edgeResult.zone || undefined,
        city: edgeResult.city || undefined,
        state: edgeResult.state || undefined,
      };
    }

    // For non-cached pincodes, try API fallback
    try {
      const apiResult = await checkServiceabilityWithFallback(pincode);
      if (apiResult.serviceable) {
        return {
          serviceable: true,
          estimate_days: apiResult.estimated_days || undefined,
          message: `Delivery available in ${apiResult.estimated_days || 3-5} days`,
          cod_available: apiResult.cod_available,
          shipping_cost: apiResult.shipping_cost,
          zone: apiResult.zone || undefined,
          city: apiResult.city || undefined,
          state: apiResult.state || undefined,
        };
      }
    } catch {
      // Fallback failed, continue with not serviceable
    }

    return {
      serviceable: false,
      message: 'Delivery not available for this pincode',
    };
  },
};

// Orders API
export const ordersApi = {
  createD2C: async (order: D2COrderRequest): Promise<D2COrderResponse> => {
    const { data } = await storefrontClient.post(`${API_PATH}/orders/d2c`, order);
    return data;
  },

  getByNumber: async (orderNumber: string, phone: string): Promise<D2COrderResponse> => {
    const { data } = await storefrontClient.get(`${API_PATH}/orders/track?order_number=${orderNumber}&phone=${phone}`);
    return data;
  },
};

// Payments API - Razorpay integration
export interface CreatePaymentOrderRequest {
  order_id: string;
  amount: number;
  customer_name: string;
  customer_email?: string;
  customer_phone: string;
  notes?: Record<string, string>;
}

export interface PaymentOrderResponse {
  razorpay_order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  order_id: string;
  customer_name: string;
  customer_email?: string;
  customer_phone: string;
}

export interface VerifyPaymentRequest {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
  order_id: string;
}

export const paymentsApi = {
  createOrder: async (request: CreatePaymentOrderRequest): Promise<PaymentOrderResponse> => {
    const { data } = await storefrontClient.post(`${API_PATH}/payments/create-order`, request);
    return data;
  },

  verifyPayment: async (request: VerifyPaymentRequest): Promise<{ verified: boolean; message: string }> => {
    const { data } = await storefrontClient.post(`${API_PATH}/payments/verify`, request);
    return data;
  },
};

// Search API - Uses public storefront endpoints
export const searchApi = {
  products: async (query: string, limit = 10): Promise<StorefrontProduct[]> => {
    const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products?search=${encodeURIComponent(query)}&size=${limit}`);
    return data.items || [];
  },

  suggestions: async (query: string): Promise<string[]> => {
    try {
      // Use products endpoint with search for suggestions
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/products?search=${encodeURIComponent(query)}&size=5`);
      return (data.items || []).map((p: StorefrontProduct) => p.name);
    } catch {
      return [];
    }
  },

  getSuggestions: async (query: string, limit = 6): Promise<SearchSuggestionsResponse> => {
    if (!query || query.length < 2) {
      return { products: [], categories: [], brands: [], query };
    }
    const { data } = await storefrontClient.get(
      `${STOREFRONT_PATH}/search/suggestions?q=${encodeURIComponent(query)}&limit=${limit}`
    );
    return data;
  },
};

// Company API (public info from ERP)
export const companyApi = {
  getInfo: async (): Promise<CompanyInfo> => {
    try {
      const { data } = await storefrontClient.get(`${API_PATH}/storefront/company`);
      return data;
    } catch {
      // Return default company info if API fails
      return {
        name: 'AQUAPURITE',
        trade_name: 'AQUAPURITE',
        email: 'support@aquapurite.com',
        phone: '1800-123-4567',
        website: 'https://aquapurite.com',
        address: '123 Industrial Area, Sector 62',
        city: 'Noida',
        state: 'Uttar Pradesh',
        pincode: '201301',
      };
    }
  },
};

// Auth API - D2C customer authentication
export const authApi = {
  sendOTP: async (phone: string, captchaToken?: string): Promise<{
    success: boolean;
    message: string;
    expires_in_seconds: number;
    resend_in_seconds: number;
  }> => {
    const { data } = await storefrontClient.post(`${API_PATH}/d2c/auth/send-otp`, {
      phone,
      captcha_token: captchaToken,
    });
    return data;
  },

  verifyOTP: async (phone: string, otp: string): Promise<{
    success: boolean;
    message: string;
    access_token?: string;
    refresh_token?: string;
    customer?: CustomerProfile;
    is_new_customer: boolean;
  }> => {
    const { data } = await storefrontClient.post(`${API_PATH}/d2c/auth/verify-otp`, { phone, otp });
    return data;
  },

  refreshToken: async (refreshToken: string): Promise<{
    access_token: string;
    token_type: string;
  }> => {
    const { data } = await storefrontClient.post(
      `${API_PATH}/d2c/auth/refresh-token`,
      {},
      { headers: { Authorization: `Bearer ${refreshToken}` } }
    );
    return data;
  },

  getProfile: async (): Promise<CustomerProfile> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.get(`${API_PATH}/d2c/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  updateProfile: async (profile: { first_name?: string; last_name?: string; email?: string }): Promise<CustomerProfile> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.put(`${API_PATH}/d2c/auth/me`, profile, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  // Phone change - Step 1: Request OTP for new phone
  requestPhoneChange: async (newPhone: string): Promise<{
    success: boolean;
    message: string;
    expires_in_seconds: number;
    resend_in_seconds: number;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.post(
      `${API_PATH}/d2c/auth/change-phone/request`,
      { new_phone: newPhone },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  // Phone change - Step 2: Verify OTP and update phone
  verifyPhoneChange: async (newPhone: string, otp: string): Promise<CustomerProfile> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.post(
      `${API_PATH}/d2c/auth/change-phone/verify`,
      { new_phone: newPhone, otp },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  getAddresses: async (): Promise<CustomerAddress[]> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.get(`${API_PATH}/d2c/auth/addresses`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  addAddress: async (address: Omit<CustomerAddress, 'id'>): Promise<CustomerAddress> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.post(`${API_PATH}/d2c/auth/addresses`, address, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  deleteAddress: async (addressId: string): Promise<void> => {
    const token = useAuthStore.getState().accessToken;
    await storefrontClient.delete(`${API_PATH}/d2c/auth/addresses/${addressId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  updateAddress: async (addressId: string, address: Omit<CustomerAddress, 'id'>): Promise<CustomerAddress> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.put(`${API_PATH}/d2c/auth/addresses/${addressId}`, address, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  setDefaultAddress: async (addressId: string): Promise<CustomerAddress> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.put(`${API_PATH}/d2c/auth/addresses/${addressId}/default`, {}, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  // Wishlist
  getWishlist: async (): Promise<{
    items: Array<{
      id: string;
      product_id: string;
      product_name: string;
      product_slug: string;
      product_image?: string;
      product_price: number;
      product_mrp: number;
      variant_id?: string;
      variant_name?: string;
      price_when_added?: number;
      is_in_stock: boolean;
      price_dropped: boolean;
      created_at: string;
    }>;
    total: number;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.get(`${API_PATH}/d2c/auth/wishlist`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  addToWishlist: async (productId: string, variantId?: string): Promise<{
    id: string;
    product_id: string;
    product_name: string;
    product_slug: string;
    product_image?: string;
    product_price: number;
    product_mrp: number;
    created_at: string;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.post(`${API_PATH}/d2c/auth/wishlist`, {
      product_id: productId,
      variant_id: variantId,
    }, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  removeFromWishlist: async (productId: string): Promise<void> => {
    const token = useAuthStore.getState().accessToken;
    await storefrontClient.delete(`${API_PATH}/d2c/auth/wishlist/${productId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  checkWishlist: async (productId: string): Promise<{ in_wishlist: boolean }> => {
    const token = useAuthStore.getState().accessToken;
    if (!token) return { in_wishlist: false };
    const { data } = await storefrontClient.get(`${API_PATH}/d2c/auth/wishlist/check/${productId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  getOrders: async (page = 1, size = 10): Promise<{
    orders: Array<{
      id: string;
      order_number: string;
      status: string;
      total_amount: number;
      created_at: string;
      items_count: number;
    }>;
    total: number;
    page: number;
    size: number;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.get(`${API_PATH}/d2c/auth/orders?page=${page}&size=${size}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  getOrderByNumber: async (orderNumber: string): Promise<{
    id: string;
    order_number: string;
    status: string;
    payment_status: string;
    payment_method: string;
    subtotal: number;
    tax_amount: number;
    shipping_amount: number;
    discount_amount: number;
    grand_total: number;
    created_at: string;
    shipped_at?: string;
    delivered_at?: string;
    shipping_address: {
      full_name: string;
      phone: string;
      email?: string;
      address_line1: string;
      address_line2?: string;
      city: string;
      state: string;
      pincode: string;
    };
    items: Array<{
      id: string;
      product_name: string;
      sku: string;
      quantity: number;
      unit_price: number;
      total_price: number;
    }>;
    tracking_number?: string;
    courier_name?: string;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.get(`${API_PATH}/d2c/auth/orders/${orderNumber}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  },

  logout: async (): Promise<void> => {
    const token = useAuthStore.getState().accessToken;
    try {
      await storefrontClient.post(`${API_PATH}/d2c/auth/logout`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Ignore errors on logout
    }
  },
};

// Reviews API
export const reviewsApi = {
  getProductReviews: async (
    productId: string,
    page = 1,
    size = 10,
    sortBy: 'recent' | 'helpful' | 'rating_high' | 'rating_low' = 'recent',
    ratingFilter?: number
  ): Promise<{
    reviews: Array<{
      id: string;
      rating: number;
      title?: string;
      review_text?: string;
      is_verified_purchase: boolean;
      helpful_count: number;
      created_at: string;
      customer_name: string;
      admin_response?: string;
      admin_response_at?: string;
    }>;
    summary: {
      average_rating: number;
      total_reviews: number;
      rating_distribution: Record<string, number>;
      verified_purchase_count: number;
    };
    total: number;
    page: number;
    size: number;
  }> => {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
      sort_by: sortBy,
    });
    if (ratingFilter) params.append('rating_filter', ratingFilter.toString());

    const { data } = await storefrontClient.get(
      `${API_PATH}/reviews/product/${productId}?${params.toString()}`
    );
    return data;
  },

  getReviewSummary: async (productId: string): Promise<{
    average_rating: number;
    total_reviews: number;
    rating_distribution: Record<string, number>;
    verified_purchase_count: number;
  }> => {
    const { data } = await storefrontClient.get(
      `${API_PATH}/reviews/product/${productId}/summary`
    );
    return data;
  },

  canReview: async (productId: string): Promise<{
    can_review: boolean;
    reason?: string;
    is_verified_purchase: boolean;
  }> => {
    const token = useAuthStore.getState().accessToken;
    if (!token) {
      return { can_review: false, reason: 'Login required', is_verified_purchase: false };
    }
    const { data } = await storefrontClient.get(
      `${API_PATH}/reviews/can-review/${productId}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  createReview: async (
    productId: string,
    rating: number,
    title?: string,
    reviewText?: string
  ): Promise<{
    id: string;
    rating: number;
    title?: string;
    review_text?: string;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.post(
      `${API_PATH}/reviews`,
      { product_id: productId, rating, title, review_text: reviewText },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  voteHelpful: async (reviewId: string, isHelpful: boolean): Promise<void> => {
    const token = useAuthStore.getState().accessToken;
    await storefrontClient.post(
      `${API_PATH}/reviews/${reviewId}/helpful`,
      { is_helpful: isHelpful },
      { headers: { Authorization: `Bearer ${token}` } }
    );
  },
};

// Product Q&A API
// Backend endpoints:
// - GET /api/v1/questions/product/{product_id} - Get questions for product
// - POST /api/v1/questions - Create a new question (authenticated)
// - POST /api/v1/questions/{question_id}/answers - Answer a question (authenticated)
// - POST /api/v1/questions/{question_id}/helpful - Vote question helpful (authenticated)
// - POST /api/v1/questions/answers/{answer_id}/helpful - Vote answer helpful (authenticated)

export interface ProductQuestion {
  id: string;
  question_text: string;
  asked_by: string;
  answers: ProductAnswer[];
  answer_count: number;
  helpful_count: number;
  created_at: string;
}

export interface ProductAnswer {
  id: string;
  answer_text: string;
  answered_by: string;
  is_seller_answer: boolean;
  is_verified_buyer: boolean;
  helpful_count: number;
  created_at: string;
}

export const questionsApi = {
  // Get questions for a product
  getByProduct: async (productId: string, params?: { page?: number; size?: number }): Promise<{
    items: ProductQuestion[];
    total: number;
    page: number;
    size: number;
  }> => {
    try {
      const { data } = await storefrontClient.get(`${API_PATH}/questions/product/${productId}`, { params });
      return data;
    } catch (error) {
      // Return empty list if endpoint fails or product has no questions
      return {
        items: [],
        total: 0,
        page: params?.page || 1,
        size: params?.size || 10,
      };
    }
  },

  // Create a new question
  create: async (data: { product_id: string; question_text: string }): Promise<ProductQuestion> => {
    const token = useAuthStore.getState().accessToken;
    if (!token) {
      throw new Error('Authentication required to ask a question');
    }

    const response = await storefrontClient.post(
      `${API_PATH}/questions`,
      data,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data;
  },

  // Create an answer to a question
  createAnswer: async (questionId: string, answerText: string): Promise<ProductAnswer> => {
    const token = useAuthStore.getState().accessToken;
    if (!token) {
      throw new Error('Authentication required to answer a question');
    }

    const response = await storefrontClient.post(
      `${API_PATH}/questions/${questionId}/answers`,
      { answer_text: answerText },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data;
  },

  // Vote on a question or answer
  voteHelpful: async (type: 'question' | 'answer', id: string): Promise<{ helpful_count: number }> => {
    const token = useAuthStore.getState().accessToken;
    if (!token) {
      throw new Error('Authentication required to vote');
    }

    // Use the correct endpoint based on type
    const endpoint = type === 'question'
      ? `${API_PATH}/questions/${id}/helpful`
      : `${API_PATH}/questions/answers/${id}/helpful`;

    const response = await storefrontClient.post(
      endpoint,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data;
  },
};

// Coupons API
export interface CouponValidationRequest {
  code: string;
  cart_total: number;
  cart_items: number;
  product_ids?: string[];
  category_ids?: string[];
}

export interface CouponValidationResponse {
  valid: boolean;
  code: string;
  discount_type?: 'PERCENTAGE' | 'FIXED_AMOUNT' | 'FREE_SHIPPING';
  discount_value?: number;
  discount_amount?: number;
  message: string;
  name?: string;
  description?: string;
  minimum_order_amount?: number;
}

export interface ActiveCoupon {
  code: string;
  name: string;
  description?: string;
  discount_type: 'PERCENTAGE' | 'FIXED_AMOUNT' | 'FREE_SHIPPING';
  discount_value: number;
  minimum_order_amount?: number;
  max_discount_amount?: number;
  valid_until?: string;
  first_order_only: boolean;
}

export const couponsApi = {
  validate: async (request: CouponValidationRequest): Promise<CouponValidationResponse> => {
    const token = useAuthStore.getState().accessToken;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const { data } = await storefrontClient.post(
      `${API_PATH}/coupons/validate`,
      request,
      { headers }
    );
    return data;
  },

  getActive: async (): Promise<ActiveCoupon[]> => {
    const token = useAuthStore.getState().accessToken;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const { data } = await storefrontClient.get(`${API_PATH}/coupons/active`, { headers });
    return data;
  },
};

// Returns API
export interface ReturnItemRequest {
  order_item_id: string;
  quantity_returned: number;
  condition: 'UNOPENED' | 'OPENED_UNUSED' | 'USED' | 'DAMAGED' | 'DEFECTIVE';
  condition_notes?: string;
  customer_images?: string[];
}

export interface ReturnRequest {
  order_number: string;
  phone: string;
  return_reason: 'DAMAGED' | 'DEFECTIVE' | 'WRONG_ITEM' | 'NOT_AS_DESCRIBED' | 'CHANGED_MIND' | 'SIZE_FIT_ISSUE' | 'QUALITY_ISSUE' | 'OTHER';
  return_reason_details?: string;
  items: ReturnItemRequest[];
  pickup_address?: {
    full_name: string;
    phone: string;
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    pincode: string;
    country?: string;
  };
}

export interface ReturnItem {
  id: string;
  order_item_id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity_ordered: number;
  quantity_returned: number;
  condition: string;
  condition_notes?: string;
  inspection_result?: string;
  inspection_notes?: string;
  accepted_quantity?: number;
  unit_price: number;
  total_amount: number;
  refund_amount: number;
  serial_number?: string;
  customer_images?: string[];
}

export interface ReturnStatusHistory {
  id: string;
  from_status?: string;
  to_status: string;
  notes?: string;
  created_at: string;
}

export interface ReturnStatus {
  rma_number: string;
  status: string;
  status_message: string;
  requested_at: string;
  estimated_refund_date?: string;
  refund_amount?: number;
  refund_status?: string;
  tracking_number?: string;
  courier?: string;
  items: ReturnItem[];
  timeline: ReturnStatusHistory[];
}

export interface ReturnListItem {
  id: string;
  rma_number: string;
  order_id: string;
  order_number?: string;
  return_type: string;
  return_reason: string;
  status: string;
  status_message: string;
  requested_at: string;
  total_return_amount: number;
  net_refund_amount: number;
  items_count: number;
}

export const returnsApi = {
  requestReturn: async (request: ReturnRequest): Promise<ReturnStatus> => {
    const token = useAuthStore.getState().accessToken;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const { data } = await storefrontClient.post(
      `${API_PATH}/returns/request`,
      request,
      { headers }
    );
    return data;
  },

  trackReturn: async (rmaNumber: string, phone: string): Promise<ReturnStatus> => {
    const { data } = await storefrontClient.get(
      `${API_PATH}/returns/track/${rmaNumber}?phone=${encodeURIComponent(phone)}`
    );
    return data;
  },

  getMyReturns: async (page = 1, size = 10): Promise<{
    items: ReturnListItem[];
    total: number;
    page: number;
    size: number;
    pages: number;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.get(
      `${API_PATH}/returns/my-returns?page=${page}&size=${size}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  cancelReturn: async (rmaNumber: string): Promise<{ message: string; rma_number: string }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.post(
      `${API_PATH}/returns/${rmaNumber}/cancel`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },
};

// Export all APIs
// Order Tracking API
export interface TimelineEvent {
  event_type: 'ORDER' | 'PAYMENT' | 'SHIPMENT' | 'DELIVERY' | 'RETURN';
  status: string;
  title: string;
  description?: string;
  timestamp: string;
  location?: string;
  metadata?: Record<string, any>;
}

export interface ShipmentInfo {
  shipment_id: string;
  tracking_number?: string;
  courier_name?: string;
  status: string;
  status_message: string;
  shipped_at?: string;
  estimated_delivery?: string;
  delivered_at?: string;
  current_location?: string;
  tracking_url?: string;
  tracking_events: Array<{
    status: string;
    message: string;
    location?: string;
    remarks?: string;
    timestamp?: string;
  }>;
}

export interface OrderTrackingResponse {
  order_number: string;
  order_id: string;
  status: string;
  status_message: string;
  payment_status: string;
  payment_method: string;
  placed_at: string;
  confirmed_at?: string;
  shipped_at?: string;
  delivered_at?: string;
  cancelled_at?: string;
  subtotal: number;
  tax_amount: number;
  shipping_amount: number;
  discount_amount: number;
  total_amount: number;
  amount_paid: number;
  shipping_address: Record<string, any>;
  items: Array<{
    id: string;
    product_id: string;
    product_name: string;
    sku: string;
    quantity: number;
    unit_price: number;
    total_price: number;
  }>;
  timeline: TimelineEvent[];
  shipments: ShipmentInfo[];
  active_return?: {
    rma_number: string;
    status: string;
    requested_at: string;
    refund_amount: number;
  };
  can_cancel: boolean;
  can_return: boolean;
}

export const orderTrackingApi = {
  trackPublic: async (orderNumber: string, phone: string): Promise<OrderTrackingResponse> => {
    const { data } = await storefrontClient.get(
      `${API_PATH}/order-tracking/track/${orderNumber}?phone=${encodeURIComponent(phone)}`
    );
    return data;
  },

  trackMyOrder: async (orderNumber: string): Promise<OrderTrackingResponse> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.get(
      `${API_PATH}/order-tracking/my-order/${orderNumber}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  downloadInvoice: async (orderNumber: string): Promise<Blob> => {
    const token = useAuthStore.getState().accessToken;
    const response = await storefrontClient.get(
      `${API_PATH}/orders/${orderNumber}/invoice`,
      {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      }
    );
    return response.data;
  },

  reorder: async (orderNumber: string): Promise<{ items_added: number; message: string }> => {
    const token = useAuthStore.getState().accessToken;
    const { data } = await storefrontClient.post(
      `${API_PATH}/orders/${orderNumber}/reorder`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },
};

// Abandoned Cart API
export interface CartItemSync {
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  price: number;
  variant_id?: string;
  variant_name?: string;
  image_url?: string;
}

export interface CartSyncRequest {
  session_id: string;
  items: CartItemSync[];
  subtotal: number;
  tax_amount: number;
  shipping_amount: number;
  discount_amount: number;
  total_amount: number;
  coupon_code?: string;
  email?: string;
  phone?: string;
  customer_name?: string;
  checkout_step?: string;
  shipping_address?: Record<string, any>;
  selected_payment_method?: string;
  source?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  referrer_url?: string;
  user_agent?: string;
  device_type?: string;
  device_fingerprint?: string;
}

export interface CartSyncResponse {
  cart_id: string;
  session_id: string;
  status: string;
  items_count: number;
  total_amount: number;
  recovery_token?: string;
  message: string;
}

export interface RecoveredCartItem {
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  price: number;
  variant_id?: string;
  variant_name?: string;
  image_url?: string;
}

export interface RecoveredCartResponse {
  cart_id: string;
  items: RecoveredCartItem[];
  subtotal: number;
  tax_amount: number;
  shipping_amount: number;
  discount_amount: number;
  total_amount: number;
  coupon_code?: string;
  shipping_address?: Record<string, any>;
  message: string;
}

export const abandonedCartApi = {
  sync: async (request: CartSyncRequest): Promise<CartSyncResponse> => {
    const token = useAuthStore.getState().accessToken;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const { data } = await storefrontClient.post(
      `${API_PATH}/abandoned-cart/sync`,
      request,
      { headers }
    );
    return data;
  },

  recover: async (token: string): Promise<RecoveredCartResponse> => {
    const { data } = await storefrontClient.get(
      `${API_PATH}/abandoned-cart/recover/${token}`
    );
    return data;
  },

  markConverted: async (sessionId: string, orderId: string): Promise<void> => {
    const token = useAuthStore.getState().accessToken;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    await storefrontClient.post(
      `${API_PATH}/abandoned-cart/mark-converted/${sessionId}?order_id=${orderId}`,
      {},
      { headers }
    );
  },
};

// Address Lookup API (Google Places + DigiPin)
export interface AddressSuggestion {
  place_id: string;
  description: string;
  main_text: string;
  secondary_text: string;
}

export interface AddressDetails {
  place_id?: string;
  formatted_address: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
  latitude?: number;
  longitude?: number;
  digipin?: string;
}

export interface DigiPinInfo {
  digipin: string;
  latitude: number;
  longitude: number;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
}

export interface PincodeInfo {
  pincode: string;
  city?: string;
  state?: string;
  areas?: string[];
}

export const addressApi = {
  // Get address suggestions as user types
  autocomplete: async (query: string, sessionToken?: string): Promise<AddressSuggestion[]> => {
    if (query.length < 3) return [];
    const params = new URLSearchParams({ query });
    if (sessionToken) params.append('session_token', sessionToken);

    try {
      const { data } = await storefrontClient.get(`${API_PATH}/address/autocomplete?${params.toString()}`);
      return data.suggestions || [];
    } catch {
      return [];
    }
  },

  // Get full address details from place ID
  getPlaceDetails: async (placeId: string, sessionToken?: string): Promise<AddressDetails | null> => {
    const params = new URLSearchParams();
    if (sessionToken) params.append('session_token', sessionToken);

    try {
      const { data } = await storefrontClient.get(
        `${API_PATH}/address/place/${placeId}${params.toString() ? '?' + params.toString() : ''}`
      );
      return data;
    } catch {
      return null;
    }
  },

  // Get address from DigiPin code
  lookupDigiPin: async (digipin: string): Promise<DigiPinInfo | null> => {
    try {
      const { data } = await storefrontClient.get(`${API_PATH}/address/digipin/${digipin}`);
      return data;
    } catch {
      return null;
    }
  },

  // Get address from coordinates (for "Use my location")
  reverseGeocode: async (latitude: number, longitude: number): Promise<AddressDetails | null> => {
    try {
      const { data } = await storefrontClient.get(
        `${API_PATH}/address/reverse-geocode?latitude=${latitude}&longitude=${longitude}`
      );
      return data;
    } catch {
      return null;
    }
  },

  // Get city/state from pincode
  lookupPincode: async (pincode: string): Promise<PincodeInfo | null> => {
    if (!/^\d{6}$/.test(pincode)) return null;
    try {
      const { data } = await storefrontClient.get(`${API_PATH}/address/pincode/${pincode}`);
      return data;
    } catch {
      return null;
    }
  },

  // Generate DigiPin from coordinates
  encodeDigiPin: async (latitude: number, longitude: number): Promise<DigiPinInfo | null> => {
    try {
      const { data } = await storefrontClient.post(`${API_PATH}/address/encode-digipin`, {
        latitude,
        longitude,
      });
      return data;
    } catch {
      return null;
    }
  },
};

// CMS Content API - Public storefront content
export interface StorefrontBanner {
  id: string;
  title: string;
  subtitle?: string;
  image_url: string;
  mobile_image_url?: string;
  cta_text?: string;
  cta_link?: string;
  text_position: 'left' | 'center' | 'right';
  text_color: 'white' | 'dark';
}

export interface StorefrontUsp {
  id: string;
  title: string;
  description?: string;
  icon: string;
  icon_color?: string;
  link_url?: string;
  link_text?: string;
}

export interface StorefrontTestimonial {
  id: string;
  customer_name: string;
  customer_location?: string;
  customer_avatar_url?: string;
  customer_designation?: string;
  rating: number;
  content: string;
  title?: string;
  product_name?: string;
}

export interface StorefrontAnnouncement {
  id: string;
  text: string;
  link_url?: string;
  link_text?: string;
  announcement_type: 'INFO' | 'WARNING' | 'PROMO' | 'SUCCESS';
  background_color?: string;
  text_color?: string;
  is_dismissible: boolean;
}

export interface StorefrontPage {
  id: string;
  title: string;
  slug: string;
  content?: string;
  meta_title?: string;
  meta_description?: string;
  og_image_url?: string;
}

export interface FooterPage {
  id: string;
  title: string;
  slug: string;
}

export interface StorefrontMenuItem {
  id: string;
  menu_location: 'header' | 'footer_quick' | 'footer_service';
  title: string;
  url: string;
  icon?: string;
  target: '_self' | '_blank';
  children?: StorefrontMenuItem[];
}

export interface StorefrontFeatureBar {
  id: string;
  icon: string;
  title: string;
  subtitle?: string;
}

export interface StorefrontSettings {
  [key: string]: string | undefined;
}

// Mega Menu Types (CMS-managed navigation)
export interface StorefrontMegaMenuSubcategory {
  id: string;
  name: string;
  slug: string;
  image_url?: string;
  product_count: number;
}

export interface StorefrontMegaMenuItem {
  id: string;
  title: string;
  icon?: string;
  image_url?: string;
  menu_type: 'CATEGORY' | 'CUSTOM_LINK';
  url?: string;
  target: '_self' | '_blank';
  is_highlighted: boolean;
  highlight_text?: string;
  category_slug?: string;
  subcategories: StorefrontMegaMenuSubcategory[];
}

// FAQ Types (CMS-managed FAQ content)
export interface StorefrontFaqItem {
  id: string;
  question: string;
  answer: string;
  keywords: string[];
}

export interface StorefrontFaqCategory {
  id: string;
  name: string;
  slug: string;
  icon: string;
  icon_color?: string;
  items: StorefrontFaqItem[];
}

export interface StorefrontFaqResponse {
  categories: StorefrontFaqCategory[];
  total_items: number;
}

export const contentApi = {
  getBanners: async (): Promise<StorefrontBanner[]> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/banners`);
      return data || [];
    } catch {
      return [];
    }
  },

  getUsps: async (): Promise<StorefrontUsp[]> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/usps`);
      return data || [];
    } catch {
      return [];
    }
  },

  getTestimonials: async (): Promise<StorefrontTestimonial[]> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/testimonials`);
      return data || [];
    } catch {
      return [];
    }
  },

  getActiveAnnouncement: async (): Promise<StorefrontAnnouncement | null> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/announcements/active`);
      return data || null;
    } catch {
      return null;
    }
  },

  getPage: async (slug: string): Promise<StorefrontPage | null> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/pages/${slug}`);
      return data || null;
    } catch {
      return null;
    }
  },

  getFooterPages: async (): Promise<FooterPage[]> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/footer-pages`);
      return data || [];
    } catch {
      return [];
    }
  },

  getSettings: async (group?: string): Promise<StorefrontSettings> => {
    try {
      const params = group ? `?group=${group}` : '';
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/settings${params}`);
      return data || {};
    } catch {
      return {};
    }
  },

  getMenuItems: async (location?: string): Promise<StorefrontMenuItem[]> => {
    try {
      const params = location ? `?location=${location}` : '';
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/menu-items${params}`);
      return data || [];
    } catch {
      return [];
    }
  },

  getFeatureBars: async (): Promise<StorefrontFeatureBar[]> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/feature-bars`);
      return data || [];
    } catch {
      return [];
    }
  },

  getMegaMenu: async (): Promise<StorefrontMegaMenuItem[]> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/mega-menu`);
      return data || [];
    } catch {
      return [];
    }
  },

  getFaq: async (categorySlug?: string): Promise<StorefrontFaqResponse> => {
    try {
      const params = categorySlug ? `?category_slug=${categorySlug}` : '';
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/faq${params}`);
      return data || { categories: [], total_items: 0 };
    } catch {
      return { categories: [], total_items: 0 };
    }
  },
};

// Homepage Composite API - Single request for all homepage data
// Uses types from @/types/storefront for products, categories, brands
// Uses local CMS types for banners, usps, testimonials
export interface HomepageData {
  categories: import('@/types/storefront').StorefrontCategory[];
  featured_products: import('@/types/storefront').StorefrontProduct[];
  bestseller_products: import('@/types/storefront').StorefrontProduct[];
  new_arrivals: import('@/types/storefront').StorefrontProduct[];
  banners: StorefrontBanner[];
  brands: import('@/types/storefront').StorefrontBrand[];
  usps: StorefrontUsp[];
  testimonials: StorefrontTestimonial[];
}

export const homepageApi = {
  getData: async (): Promise<HomepageData> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/homepage`);
      return data;
    } catch {
      // Return empty data on error
      return {
        categories: [],
        featured_products: [],
        bestseller_products: [],
        new_arrivals: [],
        banners: [],
        brands: [],
        usps: [],
        testimonials: [],
      };
    }
  },
};

// Customer Portal API - Service Requests, Devices, etc.
export interface ServiceRequest {
  id: string;
  ticket_number: string;
  request_type: string;
  subject: string;
  description: string;
  status: string;
  priority: string;
  product_id?: string;
  product_name?: string;
  scheduled_date?: string;
  scheduled_time?: string;
  technician_name?: string;
  technician_phone?: string;
  address?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
  rating?: number;
  feedback?: string;
}

export interface ServiceRequestCreate {
  request_type: 'REPAIR' | 'INSTALLATION' | 'WARRANTY' | 'GENERAL' | 'COMPLAINT' | 'MAINTENANCE';
  subject: string;
  description: string;
  product_id?: string;
  order_id?: string;
  priority?: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  preferred_date?: string;
  preferred_time?: string;
  address?: string;
}

export const portalApi = {
  // Service Requests
  getServiceRequests: async (params?: { status?: string; skip?: number; limit?: number }): Promise<{
    items: ServiceRequest[];
    total: number;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    const searchParams = new URLSearchParams();
    searchParams.append('customer_id', customer.id);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.skip) searchParams.append('skip', params.skip.toString());
    if (params?.limit) searchParams.append('limit', params.limit.toString());

    const { data } = await storefrontClient.get(
      `${API_PATH}/portal/service-requests?${searchParams.toString()}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  createServiceRequest: async (request: ServiceRequestCreate): Promise<ServiceRequest> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    const { data } = await storefrontClient.post(
      `${API_PATH}/portal/service-requests?customer_id=${customer.id}`,
      request,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  getServiceRequestDetails: async (requestId: string): Promise<ServiceRequest> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    const { data } = await storefrontClient.get(
      `${API_PATH}/portal/service-requests/${requestId}?customer_id=${customer.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  addServiceComment: async (requestId: string, comment: string): Promise<{ success: boolean }> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    const { data } = await storefrontClient.post(
      `${API_PATH}/portal/service-requests/${requestId}/comments?customer_id=${customer.id}`,
      { comment },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  submitServiceFeedback: async (requestId: string, rating: number, comments?: string): Promise<{ success: boolean }> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    const { data } = await storefrontClient.post(
      `${API_PATH}/portal/service-requests/${requestId}/feedback?customer_id=${customer.id}`,
      { rating, comments },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  // Customer Products/Devices
  getMyProducts: async (): Promise<{
    products: Array<{
      name: string;
      sku: string;
      image_url?: string;
      last_ordered: string;
    }>;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    const { data } = await storefrontClient.get(
      `${API_PATH}/portal/my-products?customer_id=${customer.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },
};

// AMC (Annual Maintenance Contract) API
export interface AMCPlan {
  id: string;
  name: string;
  code: string;
  amc_type: string;
  duration_months: number;
  base_price: number;
  tax_rate: number;
  services_included: number;
  parts_covered: boolean;
  labor_covered: boolean;
  emergency_support: boolean;
  priority_support: boolean;
  discount_on_parts: number;
  description?: string;
  is_active: boolean;
}

export interface AMCContract {
  id: string;
  contract_number: string;
  plan_name: string;
  plan_id: string;
  product_name: string;
  serial_number: string;
  status: string;
  start_date: string;
  end_date: string;
  total_services: number;
  services_used: number;
  next_service_due?: string;
  total_amount: number;
}

export const amcApi = {
  // Get active AMC plans for storefront
  getPlans: async (): Promise<AMCPlan[]> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/amc/plans`);
      return data.items || data || [];
    } catch {
      // Fallback: try the admin API if storefront endpoint doesn't exist
      const token = useAuthStore.getState().accessToken;
      if (!token) return [];
      const { data } = await storefrontClient.get(
        `${API_PATH}/amc/plans?is_active=true`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return data.items || [];
    }
  },

  // Get customer's active AMC contracts
  getMyContracts: async (): Promise<AMCContract[]> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    try {
      const { data } = await storefrontClient.get(
        `${API_PATH}/amc/contracts?customer_id=${customer.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return data.items || [];
    } catch {
      return [];
    }
  },

  // Purchase AMC plan
  purchasePlan: async (planId: string, serialNumber: string): Promise<{
    contract_id: string;
    contract_number: string;
    message: string;
  }> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    const { data } = await storefrontClient.post(
      `${API_PATH}/amc/contracts`,
      {
        customer_id: customer.id,
        plan_id: planId,
        serial_number: serialNumber,
        start_date: new Date().toISOString().split('T')[0],
      },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },

  // Renew AMC contract
  renewContract: async (contractId: string, planId?: string): Promise<{
    contract_id: string;
    message: string;
  }> => {
    const token = useAuthStore.getState().accessToken;
    if (!token) throw new Error('Not authenticated');

    const { data } = await storefrontClient.post(
      `${API_PATH}/amc/contracts/${contractId}/renew`,
      { new_plan_id: planId },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return data;
  },
};

// Referral Program API
export interface ReferralStats {
  referral_code: string;
  total_referrals: number;
  successful_referrals: number;
  pending_referrals: number;
  total_earnings: number;
  pending_earnings: number;
  referrals: Array<{
    id: string;
    referee_name: string;
    referee_phone?: string;
    status: 'pending' | 'completed' | 'expired' | 'converted';
    order_amount?: number;
    reward_amount?: number;
    created_at: string;
    converted_at?: string;
  }>;
}

export const referralApi = {
  // Get customer's referral code and stats
  getMyReferralStats: async (): Promise<ReferralStats> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    try {
      const { data } = await storefrontClient.get(
        `${API_PATH}/promotions/referral/customers/${customer.id}/code`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return data;
    } catch {
      // Generate a default code based on customer info if API fails
      const code = customer.first_name
        ? `${customer.first_name.toUpperCase().slice(0, 4)}${customer.phone?.slice(-4) || '2024'}`
        : `AQUA${customer.phone?.slice(-4) || '2024'}`;
      return {
        referral_code: code,
        total_referrals: 0,
        successful_referrals: 0,
        pending_referrals: 0,
        total_earnings: 0,
        pending_earnings: 0,
        referrals: [],
      };
    }
  },

  // Create a referral (when someone uses a referral code)
  createReferral: async (referralCode: string, refereeName: string, refereePhone: string): Promise<{
    referral_id: string;
    message: string;
  }> => {
    const { data } = await storefrontClient.post(
      `${API_PATH}/promotions/referral/referrals`,
      {
        referral_code: referralCode,
        referee_name: refereeName,
        referee_phone: refereePhone,
      }
    );
    return data;
  },
};

// Warranty & Device Registration API
export interface CustomerDevice {
  id: string;
  serial_number: string;
  product_id: string;
  product_name: string;
  product_image?: string;
  purchase_date: string;
  installation_date?: string;
  warranty_start_date: string;
  warranty_end_date: string;
  warranty_status: 'active' | 'expired' | 'expiring_soon';
  extended_warranty_end_date?: string;
  amc_status: 'active' | 'expired' | 'none';
  amc_end_date?: string;
  last_service_date?: string;
  next_service_due?: string;
  installation_address?: string;
}

export interface WarrantyStatus {
  serial_number: string;
  product_name: string;
  warranty_start_date: string;
  warranty_end_date: string;
  is_valid: boolean;
  days_remaining: number;
  extended_warranty?: {
    end_date: string;
    is_valid: boolean;
  };
}

export const deviceApi = {
  // Get customer's registered devices
  getMyDevices: async (): Promise<CustomerDevice[]> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    try {
      // Try to get installations for the customer
      const { data } = await storefrontClient.get(
        `${API_PATH}/installations?customer_id=${customer.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Transform installation data to device format
      const devices: CustomerDevice[] = (data.items || []).map((inst: any) => ({
        id: inst.id,
        serial_number: inst.serial_number,
        product_id: inst.product_id,
        product_name: inst.product_name || inst.product?.name || 'Water Purifier',
        product_image: inst.product?.image_url,
        purchase_date: inst.purchase_date || inst.created_at,
        installation_date: inst.installation_date || inst.completed_at,
        warranty_start_date: inst.warranty_start_date || inst.installation_date || inst.created_at,
        warranty_end_date: inst.warranty_end_date,
        warranty_status: getWarrantyStatus(inst.warranty_end_date),
        amc_status: inst.amc_contract?.status === 'ACTIVE' ? 'active' : inst.amc_contract ? 'expired' : 'none',
        amc_end_date: inst.amc_contract?.end_date,
        last_service_date: inst.last_service_date,
        next_service_due: inst.next_service_due,
        installation_address: inst.address,
      }));

      return devices;
    } catch {
      return [];
    }
  },

  // Register a new device
  registerDevice: async (data: {
    serial_number: string;
    purchase_date?: string;
    invoice_number?: string;
    address?: string;
  }): Promise<{ device_id: string; message: string }> => {
    const token = useAuthStore.getState().accessToken;
    const customer = useAuthStore.getState().customer;
    if (!token || !customer) throw new Error('Not authenticated');

    const response = await storefrontClient.post(
      `${API_PATH}/installations`,
      {
        customer_id: customer.id,
        serial_number: data.serial_number,
        purchase_date: data.purchase_date,
        invoice_number: data.invoice_number,
        address: data.address,
        status: 'REGISTERED',
      },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return { device_id: response.data.id, message: 'Device registered successfully' };
  },

  // Check warranty status by serial number (public)
  checkWarranty: async (serialNumber: string): Promise<WarrantyStatus | null> => {
    try {
      const { data } = await storefrontClient.get(
        `${API_PATH}/installations/warranty/${serialNumber}/status`
      );
      return data;
    } catch {
      return null;
    }
  },

  // Lookup warranty by serial/phone/email (public)
  lookupWarranty: async (params: { serial_number?: string; phone?: string; email?: string }): Promise<WarrantyStatus[]> => {
    try {
      const searchParams = new URLSearchParams();
      if (params.serial_number) searchParams.append('serial_number', params.serial_number);
      if (params.phone) searchParams.append('phone', params.phone);
      if (params.email) searchParams.append('email', params.email);

      const { data } = await storefrontClient.get(
        `${API_PATH}/installations/warranty/lookup?${searchParams.toString()}`
      );
      return data.items || data || [];
    } catch {
      return [];
    }
  },
};

// Helper function for warranty status
function getWarrantyStatus(warrantyEndDate: string): 'active' | 'expired' | 'expiring_soon' {
  if (!warrantyEndDate) return 'expired';
  const endDate = new Date(warrantyEndDate);
  const now = new Date();
  const daysRemaining = Math.floor((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (daysRemaining < 0) return 'expired';
  if (daysRemaining <= 30) return 'expiring_soon';
  return 'active';
}

// Demo Booking API
export interface DemoBookingRequest {
  product_name: string;
  customer_name: string;
  phone: string;
  email?: string;
  address: string;
  pincode: string;
  preferred_date: string;
  preferred_time: string;
  notes?: string;
}

export const demoBookingApi = {
  bookDemo: async (request: DemoBookingRequest): Promise<{ booking_id: string; message: string }> => {
    try {
      const { data } = await storefrontClient.post(
        `${STOREFRONT_PATH}/demo-bookings`,
        request
      );
      return data;
    } catch {
      // Fallback: Return success with message to call customer
      return {
        booking_id: `DEMO-${Date.now()}`,
        message: 'Demo request submitted. Our team will call you shortly to confirm.',
      };
    }
  },
};

// Exchange Calculator API
export interface ExchangeValuation {
  brand: string;
  model?: string;
  age_years: number;
  condition: 'excellent' | 'good' | 'fair' | 'poor';
  estimated_value: number;
  max_value: number;
  min_value: number;
}

export const exchangeApi = {
  calculateValue: async (params: {
    brand: string;
    model?: string;
    age_years: number;
    condition: 'excellent' | 'good' | 'fair' | 'poor';
    purifier_type?: string;
  }): Promise<ExchangeValuation> => {
    try {
      const { data } = await storefrontClient.post(
        `${STOREFRONT_PATH}/exchange/calculate`,
        params
      );
      return data;
    } catch {
      // Client-side calculation fallback
      const brandValues: Record<string, number> = {
        'aquaguard': 2000, 'kent': 1800, 'pureit': 1500, 'livpure': 1400,
        'eureka_forbes': 1800, 'blue_star': 1600, 'ao_smith': 1700, 'aquapurite': 2000,
        'other': 1000,
      };
      const conditionMultipliers: Record<string, number> = {
        'excellent': 1.0, 'good': 0.8, 'fair': 0.6, 'poor': 0.4,
      };
      const ageMultipliers: Record<number, number> = {
        0: 1.0, 1: 0.85, 2: 0.70, 3: 0.50, 4: 0.50, 5: 0.30, 6: 0.30,
      };

      const baseValue = brandValues[params.brand.toLowerCase().replace(' ', '_')] || brandValues['other'];
      const conditionMult = conditionMultipliers[params.condition] || 0.5;
      const ageMult = ageMultipliers[Math.floor(Math.min(params.age_years, 6))] || 0.3;

      let estimatedValue = Math.round(baseValue * conditionMult * ageMult);
      estimatedValue = Math.max(500, Math.min(estimatedValue, 2000)); // min 500, max 2000

      return {
        brand: params.brand,
        model: params.model,
        age_years: params.age_years,
        condition: params.condition,
        estimated_value: estimatedValue,
        max_value: 2000,
        min_value: 500,
      };
    }
  },
};

// Video Guides API
export interface VideoGuide {
  id: string;
  title: string;
  description: string;
  category: string;
  duration: string;
  thumbnail: string;
  video_url: string;
  youtube_id?: string;
  views: number;
  likes: number;
  is_featured: boolean;
}

export const guidesApi = {
  getGuides: async (params?: { category?: string; search?: string; featured?: boolean }): Promise<VideoGuide[]> => {
    try {
      const searchParams = new URLSearchParams();
      if (params?.category) searchParams.append('category', params.category);
      if (params?.search) searchParams.append('search', params.search);
      if (params?.featured) searchParams.append('featured', 'true');

      const { data } = await storefrontClient.get(
        `${STOREFRONT_PATH}/guides?${searchParams.toString()}`
      );
      return data.items || data || [];
    } catch {
      return [];
    }
  },

  getGuideById: async (guideId: string): Promise<VideoGuide | null> => {
    try {
      const { data } = await storefrontClient.get(`${STOREFRONT_PATH}/guides/${guideId}`);
      return data;
    } catch {
      return null;
    }
  },
};

export const storefrontApi = {
  products: productsApi,
  categories: categoriesApi,
  brands: brandsApi,
  inventory: inventoryApi,
  orders: ordersApi,
  payments: paymentsApi,
  search: searchApi,
  company: companyApi,
  auth: authApi,
  reviews: reviewsApi,
  questions: questionsApi,
  coupons: couponsApi,
  returns: returnsApi,
  orderTracking: orderTrackingApi,
  abandonedCart: abandonedCartApi,
  address: addressApi,
  content: contentApi,
  homepage: homepageApi,
  portal: portalApi,
  amc: amcApi,
  referral: referralApi,
  device: deviceApi,
  demoBooking: demoBookingApi,
  exchange: exchangeApi,
  guides: guidesApi,
};

export default storefrontApi;
