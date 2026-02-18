// Auth Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  tenant_id: string;
  tenant_subdomain: string;
}

export interface User {
  id: string;
  email: string;
  phone?: string;
  first_name: string;
  last_name?: string;
  full_name?: string;
  name?: string; // Computed name from backend (first_name + last_name)
  department?: string;
  designation?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  roles?: Role[];
}

// Helper function to get user display name
export function getUserDisplayName(user: User | null | undefined): string {
  if (!user) return 'Unknown';
  return user.name || user.full_name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email || 'Unknown';
}

export interface Role {
  id: string;
  name: string;
  code: string;
  level: RoleLevel;
  description?: string;
  permissions?: Permission[];
  permission_count?: number;
}

export type RoleLevel = 'SUPER_ADMIN' | 'DIRECTOR' | 'HEAD' | 'MANAGER' | 'EXECUTIVE';

export interface PermissionModule {
  id: string;
  name: string;
  code: string;
}

export interface Permission {
  id: string;
  code: string;
  name: string;
  module: string | PermissionModule | null;  // Backend returns object, some code expects string
  action?: string;
  description?: string;
}

// Helper to get module code from permission (handles both string and object)
export function getPermissionModuleCode(permission: Permission): string {
  if (!permission.module) return 'general';
  if (typeof permission.module === 'string') return permission.module;
  return permission.module.code || 'general';
}

export interface UserPermissions {
  is_super_admin: boolean;
  roles?: Role[];
  permissions_by_module?: Record<string, string[]>;
  total_permissions?: number;
  permissions: Record<string, boolean>;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// Product Types
export interface ProductImage {
  id: string;
  product_id: string;
  image_url: string;
  thumbnail_url?: string;
  alt_text?: string;
  is_primary: boolean;
  sort_order: number;
  created_at?: string;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  name: string;
  sku: string;
  attributes?: Record<string, string>;
  mrp?: number;
  selling_price?: number;
  cost_price?: number;
  stock_quantity?: number;
  image_url?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ProductSpecification {
  id: string;
  product_id?: string;
  group_name?: string;
  key: string;
  value: string;
  name?: string; // Alias for key
  group?: string; // Alias for group_name
  sort_order?: number;
}

export interface ProductDocument {
  id: string;
  product_id?: string;
  title: string;
  name?: string; // Alias for title
  document_type: 'MANUAL' | 'WARRANTY_CARD' | 'BROCHURE' | 'CERTIFICATE' | 'OTHER';
  file_url: string;
  file_size_bytes?: number;
  file_size?: number; // Alias
  mime_type?: string;
  sort_order?: number;
  created_at?: string;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  slug?: string;
  description?: string;
  short_description?: string;
  model_number?: string;
  fg_code?: string;
  // Serialization fields (auto-generated on creation)
  model_code?: string; // 3-letter code for barcode generation (e.g., IEL, ELZ)
  item_type?: 'FG' | 'SP' | 'CO' | 'CN' | 'AC'; // FG=Finished Goods, SP=Spare Part, etc.
  part_code?: string; // Vendor's part code
  category_id?: string;
  brand_id?: string;
  mrp: number;
  selling_price: number;
  cost_price?: number;
  gst_rate?: number;
  hsn_code?: string;
  // Dimensions
  weight?: number;
  length?: number;
  width?: number;
  height?: number;
  volumetric_weight?: number;
  // Status flags
  is_active: boolean;
  is_featured?: boolean;
  is_new_arrival?: boolean;
  is_bestseller?: boolean;
  requires_installation?: boolean;
  // Warranty
  warranty_months?: number;
  warranty_type?: string;
  // SEO
  meta_title?: string;
  meta_description?: string;
  meta_keywords?: string;
  // Stock
  min_stock_level?: number;
  max_stock_level?: number;
  reorder_point?: number;
  // Tags
  tags?: string[];
  // Features (key selling points - newline separated string)
  features?: string;
  // Timestamps
  created_at: string;
  updated_at: string;
  // Relations
  category?: Category;
  brand?: Brand;
  images?: ProductImage[];
  variants?: ProductVariant[];
  specifications?: ProductSpecification[];
  documents?: ProductDocument[];
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
  parent_id?: string;
  image_url?: string;
  icon?: string;
  sort_order?: number;
  is_active: boolean;
  is_featured?: boolean;
}

export interface Brand {
  id: string;
  name: string;
  code: string;
  description?: string;
  logo_url?: string;
  is_active: boolean;
}

// Order Types
export type OrderStatus =
  | 'NEW'
  | 'PENDING_PAYMENT'
  | 'CONFIRMED'
  | 'ALLOCATED'
  | 'PICKLIST_CREATED'
  | 'PICKING'
  | 'PICKED'
  | 'PACKING'
  | 'PACKED'
  | 'MANIFESTED'
  | 'READY_TO_SHIP'
  | 'SHIPPED'
  | 'IN_TRANSIT'
  | 'OUT_FOR_DELIVERY'
  | 'DELIVERED'
  | 'PARTIALLY_DELIVERED'
  | 'RTO_INITIATED'
  | 'RTO_IN_TRANSIT'
  | 'RTO_DELIVERED'
  | 'RETURNED'
  | 'CANCELLED'
  | 'REFUNDED'
  | 'ON_HOLD';

export interface Order {
  id: string;
  order_number: string;
  customer_id: string;
  status: OrderStatus;
  total_amount: number;
  discount_amount: number;
  tax_amount: number;
  grand_total: number;
  payment_status: 'PENDING' | 'PAID' | 'PARTIALLY_PAID' | 'REFUNDED';
  source?: string;
  channel?: string;
  item_count?: number;
  created_at: string;
  updated_at: string;
  customer?: Customer;
  items?: OrderItem[];
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  discount: number;
  tax: number;
  total: number;
}

// Customer Types
export interface Customer {
  id: string;
  name: string;
  full_name?: string;
  email?: string;
  phone: string;
  customer_type: 'INDIVIDUAL' | 'BUSINESS' | 'DEALER';
  is_active: boolean;
  created_at: string;
  addresses?: Address[];
}

export interface Address {
  id: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
  is_default: boolean;
}

// Inventory Types
export interface Warehouse {
  id: string;
  name: string;
  code: string;
  type: 'MAIN' | 'REGIONAL' | 'SERVICE_CENTER' | 'DEALER' | 'VIRTUAL';
  address: string;
  city: string;
  state: string;
  pincode: string;
  is_active: boolean;
  capacity?: number;
  region_id?: string;
}

export interface StockItem {
  id: string;
  product_id: string;
  warehouse_id: string;
  serial_number?: string;
  batch_number?: string;
  status: 'AVAILABLE' | 'RESERVED' | 'ALLOCATED' | 'PICKED' | 'PACKED' | 'IN_TRANSIT' | 'SHIPPED' | 'DAMAGED' | 'DEFECTIVE' | 'SOLD' | 'RETURNED' | 'QUARANTINE' | 'SCRAPPED';
  quantity: number;
  reserved_quantity?: number;
  available_quantity?: number;
  reorder_level?: number;
  last_updated?: string;
  product?: Product;
  warehouse?: Warehouse;
}

export type StockMovementType =
  | 'RECEIPT'
  | 'ISSUE'
  | 'TRANSFER_IN'
  | 'TRANSFER_OUT'
  | 'RETURN_IN'
  | 'RETURN_OUT'
  | 'ADJUSTMENT_PLUS'
  | 'ADJUSTMENT_MINUS'
  | 'DAMAGE'
  | 'SCRAP'
  | 'CYCLE_COUNT';

export interface StockMovement {
  id: string;
  movement_number: string;
  movement_type: StockMovementType;
  movement_date: string;
  warehouse_id: string;
  product_id: string;
  variant_id?: string;
  stock_item_id?: string;
  quantity: number;
  balance_before?: number;
  balance_after?: number;
  reference_type?: string;
  reference_id?: string;
  reference_number?: string;
  unit_cost?: number;
  total_cost?: number;
  notes?: string;
  created_at: string;
  // Joined fields
  product_name?: string;
  product_sku?: string;
  warehouse_name?: string;
  serial_number?: string;
}

// Vendor Types
export type VendorType =
  | 'MANUFACTURER'
  | 'IMPORTER'
  | 'DISTRIBUTOR'
  | 'TRADER'
  | 'SERVICE_PROVIDER'
  | 'RAW_MATERIAL'
  | 'SPARE_PARTS'
  | 'CONSUMABLES'
  | 'TRANSPORTER'
  | 'CONTRACTOR';

export type VendorStatus = 'ACTIVE' | 'INACTIVE' | 'PENDING_APPROVAL' | 'SUSPENDED' | 'BLACKLISTED';

export type VendorGrade = 'A+' | 'A' | 'B' | 'C' | 'D';

export interface Vendor {
  id: string;
  name: string;
  // Backend uses vendor_code, frontend can use code as alias
  vendor_code: string;
  code?: string; // Alias for vendor_code
  // Backend uses legal_name (required), trade_name (optional)
  legal_name?: string;
  trade_name?: string;
  // Vendor type
  vendor_type?: VendorType;
  email?: string;
  phone?: string;
  // Backend uses gstin/pan, frontend uses gst_number/pan_number as aliases
  gstin?: string;
  gst_number?: string; // Alias for gstin
  pan?: string;
  pan_number?: string; // Alias for pan
  status: VendorStatus;
  // Backend uses grade, frontend can use tier as alias
  grade?: VendorGrade;
  tier?: VendorGrade; // Alias for grade
  // Auto-generated supplier code for barcode generation (SPARE_PARTS/MANUFACTURER vendors)
  supplier_code?: string;
  created_at: string;
  contact_person?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  pincode?: string;
  country?: string;
  // Bank Details
  bank_name?: string;
  bank_branch?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
  bank_account_type?: 'SAVINGS' | 'CURRENT' | 'OD';
  beneficiary_name?: string;
}

// Purchase Order Types
export type POStatus =
  | 'DRAFT'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'SENT_TO_VENDOR'
  | 'ACKNOWLEDGED'
  | 'PARTIALLY_RECEIVED'
  | 'FULLY_RECEIVED'
  | 'CLOSED'
  | 'CANCELLED';

export interface PurchaseOrder {
  id: string;
  po_number: string;
  vendor_id: string;
  vendor_name?: string;
  warehouse_id: string;
  delivery_warehouse_id?: string;
  status: POStatus;
  po_date?: string;
  credit_days?: number;
  subtotal?: number;
  total_amount: number;
  gst_amount: number;
  grand_total: number;
  expected_delivery_date?: string;
  // Financial terms
  payment_terms?: string;
  advance_required?: number;
  advance_paid?: number;
  freight_charges?: number;
  packing_charges?: number;
  other_charges?: number;
  // Notes
  terms_and_conditions?: string;
  special_instructions?: string;
  internal_notes?: string;
  notes?: string;
  created_at: string;
  vendor?: Vendor;
  warehouse?: Warehouse;
  items?: POItem[];
}

export interface POItem {
  id?: string;
  po_id?: string;
  product_id: string;
  product_name?: string;
  sku?: string;
  quantity?: number;
  quantity_ordered?: number;
  quantity_received?: number;
  unit_price: number;
  gst_rate: number;
  total?: number;
}

// Service Request Types
export type ServiceRequestStatus =
  | 'DRAFT'
  | 'PENDING'
  | 'ASSIGNED'
  | 'SCHEDULED'
  | 'EN_ROUTE'
  | 'IN_PROGRESS'
  | 'PARTS_REQUIRED'
  | 'ON_HOLD'
  | 'COMPLETED'
  | 'CLOSED'
  | 'CANCELLED'
  | 'REOPENED';

export type ServiceRequestType =
  | 'INSTALLATION'
  | 'WARRANTY_REPAIR'
  | 'PAID_REPAIR'
  | 'AMC_SERVICE'
  | 'DEMO'
  | 'PREVENTIVE_MAINTENANCE'
  | 'COMPLAINT'
  | 'FILTER_CHANGE'
  | 'INSPECTION'
  | 'UNINSTALLATION';

export interface ServiceRequest {
  id: string;
  request_number: string;
  customer_id: string;
  product_id?: string;
  type: ServiceRequestType;
  status: ServiceRequestStatus;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT' | 'CRITICAL';
  description?: string;
  scheduled_date?: string;
  technician_id?: string;
  created_at: string;
  customer?: Customer;
  product?: Product;
  technician?: {
    id?: string;
    name: string;
    phone?: string;
  };
}

// Dealer Types
export type DealerType = 'DISTRIBUTOR' | 'DEALER' | 'SUB_DEALER' | 'FRANCHISE' | 'RETAILER' | 'CORPORATE';

export interface Dealer {
  id: string;
  name: string;
  code?: string;
  dealer_code?: string;  // Backend returns dealer_code
  type?: DealerType;
  dealer_type?: string;  // Backend returns dealer_type
  email?: string;
  phone?: string;
  gst_number?: string;
  gstin?: string;  // Backend returns gstin
  pan?: string;
  legal_name?: string;
  display_name?: string;
  contact_person?: string;
  pricing_tier?: 'PLATINUM' | 'GOLD' | 'SILVER' | 'BRONZE' | 'STANDARD';
  tier?: string;  // Backend returns tier
  credit_limit?: number;
  credit_days?: number;
  credit_status?: string;
  available_credit?: number;
  outstanding_amount?: number;
  overdue_amount?: number;
  status?: 'ACTIVE' | 'INACTIVE' | 'PENDING' | 'SUSPENDED';
  // Address fields
  registered_address_line1?: string;
  registered_address_line2?: string;
  registered_city?: string;
  registered_district?: string;
  registered_state?: string;
  registered_state_code?: string;
  registered_pincode?: string;
  region?: 'NORTH' | 'SOUTH' | 'EAST' | 'WEST' | 'CENTRAL' | string;
  // Bank details
  bank_name?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
  bank_branch?: string;
  bank_account_name?: string;
  // Business details
  business_type?: string;
  establishment_year?: number;
  annual_turnover?: number;
  shop_area_sqft?: number;
  no_of_employees?: number;
  existing_brands?: string[];
  // Shipping address
  shipping_address_line1?: string;
  shipping_address_line2?: string;
  shipping_city?: string;
  shipping_state?: string;
  shipping_pincode?: string;
  // Territory
  territory?: string;
  // KYC
  kyc_verified?: boolean;
  kyc_verified_at?: string;
  // Agreement
  agreement_start_date?: string;
  agreement_end_date?: string;
  // Settings
  can_place_orders?: boolean;
  receive_promotions?: boolean;
  portal_access?: boolean;
  // Additional fields
  assigned_pincodes?: string[];
  total_orders?: number;
  total_revenue?: number;
  average_order_value?: number;
  credit_utilization_percentage?: number;
  created_at?: string;
  updated_at?: string;
}

// ==================== DMS Types ====================

export interface DMSDashboardSummary {
  total_distributors: number;
  active_distributors: number;
  pending_approval: number;
  total_orders_mtd: number;
  revenue_mtd: number;
  collection_mtd: number;
  total_outstanding: number;
  total_overdue: number;
  avg_order_value: number;
  credit_utilization_avg: number;
}

export interface DMSDashboardResponse {
  summary: DMSDashboardSummary;
  by_region: Array<{ region: string; count: number; revenue: number; outstanding: number }>;
  by_tier: Array<{ tier: string; count: number; revenue: number }>;
  monthly_trend: Array<{ month: string; orders: number; revenue: number; collection: number }>;
  top_performers: Array<{ dealer_id: string; dealer_code: string; name: string; revenue: number; orders: number; achievement_pct: number }>;
  credit_alerts: Array<{ dealer_id: string; dealer_code: string; name: string; outstanding: number; overdue: number; credit_limit: number; utilization_pct: number }>;
  recent_orders: Array<{ order_id: string; order_number: string; dealer_name: string; amount: number; status: string; date: string }>;
}

export interface DMSOrderItem {
  product_id: string;
  variant_id?: string;
  quantity: number;
}

export interface DMSOrder {
  id: string;
  order_number: string;
  dealer_id: string;
  dealer_name: string;
  dealer_code: string;
  items: Array<{
    product_id: string;
    product_name: string;
    sku: string;
    quantity: number;
    unit_price: number;
    total: number;
  }>;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total_amount: number;
  status: string;
  payment_status: string;
  schemes_applied: string[];
  credit_impact: number;
  notes?: string;
  created_at: string;
}

export interface DMSOrderListResponse {
  items: DMSOrder[];
  total: number;
  page: number;
  size: number;
}

// ==================== DMS Phase 2 Types ====================

export interface DealerClaim {
  id: string;
  claim_number: string;
  dealer_id: string;
  dealer_name?: string;
  dealer_code?: string;
  claim_type: 'PRODUCT_DEFECT' | 'TRANSIT_DAMAGE' | 'QUANTITY_SHORT' | 'PRICING_ERROR' | 'SCHEME_DISPUTE' | 'WARRANTY';
  status: 'SUBMITTED' | 'UNDER_REVIEW' | 'APPROVED' | 'PARTIALLY_APPROVED' | 'REJECTED' | 'SETTLED';
  order_id?: string;
  items?: Array<{ product_id: string; product_name: string; quantity: number; issue_description: string }>;
  evidence_urls?: string[];
  amount_claimed: number;
  amount_approved: number;
  resolution?: 'REPLACEMENT' | 'CREDIT_NOTE' | 'REFUND' | 'REPAIR';
  resolution_notes?: string;
  submitted_at?: string;
  reviewed_at?: string;
  settled_at?: string;
  assigned_to?: string;
  remarks?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DealerClaimListResponse {
  items: DealerClaim[];
  total: number;
  page: number;
  size: number;
}

export interface RetailerOutlet {
  id: string;
  outlet_code: string;
  dealer_id: string;
  dealer_name?: string;
  dealer_code?: string;
  name: string;
  owner_name: string;
  outlet_type: 'KIRANA' | 'MODERN_TRADE' | 'SUPERMARKET' | 'PHARMACY' | 'HARDWARE' | 'ELECTRONICS' | 'GENERAL_STORE' | 'OTHER';
  phone: string;
  email?: string;
  address_line1: string;
  city: string;
  state: string;
  pincode: string;
  latitude?: number;
  longitude?: number;
  beat_day?: 'MONDAY' | 'TUESDAY' | 'WEDNESDAY' | 'THURSDAY' | 'FRIDAY' | 'SATURDAY' | 'SUNDAY';
  status: 'ACTIVE' | 'INACTIVE' | 'CLOSED';
  last_order_date?: string;
  total_orders: number;
  total_revenue: number;
  created_at?: string;
  updated_at?: string;
}

export interface RetailerOutletListResponse {
  items: RetailerOutlet[];
  total: number;
  page: number;
  size: number;
}

export interface DMSCollections {
  aging_buckets: Array<{ label: string; amount: number; count: number }>;
  overdue_dealers: Array<{
    dealer_id: string;
    dealer_code: string;
    dealer_name: string;
    outstanding: number;
    overdue: number;
    days_overdue: number;
    credit_limit: number;
    utilization_pct: number;
    last_payment_date?: string;
  }>;
  total_outstanding: number;
  total_overdue: number;
  collection_this_month: number;
  overdue_count: number;
}

export interface DMSSecondarySale {
  id: string;
  order_number: string;
  dealer_id: string;
  dealer_name: string;
  retailer_id: string;
  retailer_name: string;
  items: Array<{ product_id: string; product_name: string; sku: string; quantity: number; unit_price: number; total: number }>;
  total_amount: number;
  status: string;
  created_at?: string;
}

export interface DMSSecondarySaleListResponse {
  items: DMSSecondarySale[];
  total: number;
  page: number;
  size: number;
  summary?: { total_sales: number; volume_this_month: number; count_this_month: number };
}

export interface DealerScheme {
  id: string;
  scheme_code: string;
  scheme_name: string;
  description?: string;
  scheme_type: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  applicable_dealer_types?: string[];
  applicable_tiers?: string[];
  applicable_regions?: string[];
  applicable_products?: string[];
  applicable_categories?: string[];
  rules: Record<string, unknown>;
  total_budget?: number;
  utilized_budget: number;
  budget_remaining?: number;
  is_valid: boolean;
  terms_and_conditions?: string;
  can_combine: boolean;
  created_by?: string;
  approved_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DealerSchemeListResponse {
  items: DealerScheme[];
  total: number;
  page: number;
  size: number;
}

// Common Types
export interface SelectOption {
  label: string;
  value: string;
}

export interface TableColumn<T> {
  key: keyof T | string;
  label: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
}
