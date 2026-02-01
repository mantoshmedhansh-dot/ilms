// Storefront-specific types (D2C)

export interface StorefrontProduct {
  id: string;
  name: string;
  slug: string;
  sku: string;
  short_description?: string;
  description?: string;
  features?: string;
  category_id?: string;
  brand_id?: string;
  category?: StorefrontCategory;
  brand?: StorefrontBrand;
  mrp: number;
  selling_price: number;
  discount_percentage?: number;
  gst_rate?: number;
  hsn_code?: string;
  warranty_months?: number;
  warranty_type?: string;
  is_active: boolean;
  is_featured?: boolean;
  is_bestseller?: boolean;
  is_new_arrival?: boolean;
  // Stock information
  in_stock?: boolean;
  stock_quantity?: number;
  images?: ProductImage[];
  variants?: ProductVariant[];
  specifications?: ProductSpecification[];
  documents?: ProductDocument[];
  created_at?: string;
  updated_at?: string;
}

export interface ProductImage {
  id: string;
  image_url: string;
  thumbnail_url?: string;
  alt_text?: string;
  is_primary: boolean;
  sort_order: number;
}

export interface ProductVariant {
  id: string;
  name: string;
  sku: string;
  attributes?: Record<string, string>;
  mrp?: number;
  selling_price?: number;
  stock_quantity?: number;
  image_url?: string;
  is_active: boolean;
}

export interface ProductSpecification {
  id: string;
  group_name?: string;
  key: string;
  value: string;
  sort_order?: number;
}

export interface ProductDocument {
  id: string;
  title: string;
  document_type: string;
  file_url: string;
  file_size_bytes?: number;
}

export interface StorefrontCategory {
  id: string;
  name: string;
  slug: string;
  description?: string;
  parent_id?: string;
  image_url?: string;
  icon?: string;
  is_active: boolean;
  is_featured?: boolean;
  product_count?: number;
  children?: StorefrontCategory[];
}

export interface StorefrontBrand {
  id: string;
  name: string;
  slug: string;
  description?: string;
  logo_url?: string;
  is_active: boolean;
}

// Cart Types
export interface CartItem {
  id: string;
  product: StorefrontProduct;
  variant?: ProductVariant;
  quantity: number;
  price: number;
}

export interface Cart {
  items: CartItem[];
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
  itemCount: number;
}

// Checkout Types
export interface ShippingAddress {
  full_name: string;
  phone: string;
  email?: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
}

export interface CheckoutData {
  shipping_address: ShippingAddress;
  billing_same_as_shipping: boolean;
  billing_address?: ShippingAddress;
  payment_method: 'RAZORPAY' | 'COD';
  notes?: string;
}

export interface D2COrderItem {
  product_id: string;
  sku: string;
  name: string;
  quantity: number;
  unit_price: number;
  tax_rate?: number;
  discount?: number;
}

export interface D2COrderRequest {
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  shipping_address: ShippingAddress;
  items: D2COrderItem[];
  payment_method: 'RAZORPAY' | 'COD';
  subtotal: number;
  tax_amount: number;
  shipping_amount: number;
  discount_amount?: number;
  coupon_code?: string;
  total_amount: number;
  notes?: string;
  partner_code?: string; // Community partner referral code for attribution
}

export interface D2COrderResponse {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  created_at: string;
}

// Stock Verification
export interface StockVerificationRequest {
  product_id: string;
  quantity: number;
  pincode?: string;
}

export interface StockVerificationResponse {
  product_id: string;
  in_stock: boolean;
  available_quantity: number;
  requested_quantity: number;
  delivery_estimate?: string;
  message?: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Filter Types
export interface ProductFilters {
  category_id?: string;
  brand_id?: string;
  min_price?: number;
  max_price?: number;
  is_featured?: boolean;
  is_bestseller?: boolean;
  is_new_arrival?: boolean;
  search?: string;
  sort_by?: 'name' | 'price' | 'created_at';
  sort_order?: 'asc' | 'desc';
  page?: number;
  size?: number;
}

// Hero Banner
export interface HeroBanner {
  id: string;
  title: string;
  subtitle?: string;
  image_url: string;
  mobile_image_url?: string;
  cta_text?: string;
  cta_link?: string;
  is_active: boolean;
}

// Testimonial
export interface Testimonial {
  id: string;
  name: string;
  location?: string;
  rating: number;
  content: string;
  avatar_url?: string;
  product_name?: string;
}

// Company Info (from ERP)
export interface CompanyInfo {
  name: string;
  trade_name?: string;
  logo_url?: string;
  logo_small_url?: string;
  favicon_url?: string;
  email: string;
  phone: string;
  website?: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
}
