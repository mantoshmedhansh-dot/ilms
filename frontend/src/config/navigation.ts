import {
  LayoutDashboard,
  Users,
  Shield,
  Package,
  ShoppingCart,
  Warehouse,
  Truck,
  DollarSign,
  FileText,
  Wrench,
  Store,
  UserCircle,
  Megaphone,
  Barcode,
  CheckSquare,
  History,
  Settings,
  Building2,
  FolderTree,
  Tag,
  LucideIcon,
  Layers,
  Grid3X3,
  ArrowRightLeft,
  ClipboardList,
  BarChart3,
  TrendingUp,
  Scale,
  Calculator,
  Receipt,
  FileCheck,
  Clock,
  AlertTriangle,
  Gauge,
  Network,
  Briefcase,
  Calendar,
  CreditCard,
  Bell,
  Brain,
  Lightbulb,
  Target,
  LineChart,
  Boxes,
  GitBranch,
  Cog,
  PackageSearch,
  Handshake,
  Phone,
  UserPlus,
  FileInput,
  FileOutput,
  Clipboard,
  MapPin,
  Route,
  BadgePercent,
  Banknote,
  Building,
  Landmark,
  ScrollText,
  IndianRupee,
  CalendarCheck,
  HeartHandshake,
  ShieldCheck,
  HardHat,
  Headphones,
  UsersRound,
  GraduationCap,
  Award,
  Globe,
  Image,
  MessageSquare,
  Search,
  Menu,
  Star,
  LayoutGrid,
  Share2,
  Wallet,
  Trophy,
  HelpCircle,
  Video,
} from 'lucide-react';

export interface NavItem {
  title: string;
  href?: string;
  icon?: LucideIcon;
  permissions?: string[];
  children?: NavItem[];
  badge?: string;
  moduleCode?: string;  // Module required for access
  section?: number;     // Section number for module mapping
}

/**
 * ILMS.AI ERP - NAVIGATION STRUCTURE
 *
 * Based on Industry Best Practices (SAP, Oracle NetSuite, Zoho, Microsoft Dynamics)
 *
 * Structure:
 * 1. Dashboard - Overview & KPIs
 * 2. Intelligence - AI & analytics (prominent placement for AI-first approach)
 * 3. Sales - Order management & sales channels
 * 4. CRM - Customer relationship management
 * 5. Procurement - Vendor-facing operations (P2P)
 * 6. Inventory - Stock management
 * 7. Warehouse (WMS) - Physical warehouse operations
 * 8. Logistics - Shipping & fulfillment
 * 9. Planning (S&OP) - Demand forecasting & supply planning
 * 10. Finance - Accounting, billing, tax compliance
 * 11. Service - After-sales support
 * 12. Human Resources - Employee management
 * 13. Master Data - Products & configuration
 * 14. D2C Content - CMS for storefront
 * 15. Administration - System settings
 */

export const navigation: NavItem[] = [
  // ==================== 1. DASHBOARD ====================
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    permissions: [],
    moduleCode: 'system_admin',
    section: 1,
  },

  // ==================== 2. INTELLIGENCE (AI) ====================
  {
    title: 'Intelligence',
    icon: Brain,
    permissions: [],
    badge: 'AI',
    moduleCode: 'scm_ai',
    children: [
      { title: 'AI Hub', href: '/dashboard/ai', icon: Lightbulb, permissions: [] },
      { title: 'Insights Dashboard', href: '/dashboard/insights', icon: TrendingUp, permissions: [] },
      { title: 'Reorder Suggestions', href: '/dashboard/insights/reorder', icon: PackageSearch, permissions: [] },
      { title: 'Churn Risk Analysis', href: '/dashboard/insights/churn-risk', icon: AlertTriangle, permissions: [] },
      { title: 'Slow Moving Stock', href: '/dashboard/insights/slow-moving', icon: Clock, permissions: [] },
      { title: 'Campaigns', href: '/dashboard/marketing/campaigns', icon: Megaphone, permissions: ['MARKETING_VIEW'] },
    ],
  },

  // ==================== 3. SALES ====================
  {
    title: 'Sales',
    icon: ShoppingCart,
    permissions: ['ORDERS_VIEW', 'MARKETING_VIEW'],
    moduleCode: 'oms_fulfillment',
    children: [
      // Orders
      { title: 'All Orders', href: '/dashboard/orders', icon: ShoppingCart, permissions: ['ORDERS_VIEW'] },
      { title: 'New Order', href: '/dashboard/orders/new', icon: FileInput, permissions: ['ORDERS_CREATE'] },
      // Channels
      { title: 'Sales Channels', href: '/dashboard/channels', icon: Network, permissions: ['ORDERS_VIEW'] },
      { title: 'Marketplaces', href: '/dashboard/channels/marketplaces', icon: Store, permissions: ['ORDERS_VIEW'] },
      { title: 'Channel Pricing', href: '/dashboard/channels/pricing', icon: DollarSign, permissions: ['ORDERS_VIEW'] },
      // Distribution Network
      { title: 'Dealers', href: '/dashboard/distribution/dealers', icon: Handshake, permissions: ['ORDERS_VIEW'] },
      { title: 'Franchisees', href: '/dashboard/distribution/franchisees', icon: Building2, permissions: ['ORDERS_VIEW'] },
      { title: 'Pricing Tiers', href: '/dashboard/distribution/pricing-tiers', icon: Layers, permissions: ['ORDERS_VIEW'] },
      // Promotions
      { title: 'Promotions', href: '/dashboard/marketing/promotions', icon: BadgePercent, permissions: ['MARKETING_VIEW'] },
      { title: 'Sales Commissions', href: '/dashboard/marketing/commissions', icon: Banknote, permissions: ['MARKETING_VIEW'] },
    ],
  },

  // ==================== 4. CRM ====================
  {
    title: 'CRM',
    icon: UserCircle,
    permissions: ['CRM_VIEW'],
    moduleCode: 'crm_service',
    children: [
      { title: 'Customers', href: '/dashboard/crm/customers', icon: UserCircle, permissions: ['CRM_VIEW'] },
      { title: 'Customer 360', href: '/dashboard/crm/customer-360', icon: Target, permissions: ['CRM_VIEW'] },
      { title: 'Leads', href: '/dashboard/crm/leads', icon: UserPlus, permissions: ['CRM_VIEW'] },
      { title: 'Call Center', href: '/dashboard/crm/call-center', icon: Phone, permissions: ['CRM_VIEW'] },
    ],
  },

  // ==================== 4.5 COMMUNITY PARTNERS (Meesho-style) ====================
  {
    title: 'Community Partners',
    icon: Share2,
    permissions: [],
    badge: 'NEW',
    moduleCode: 'sales_distribution',
    children: [
      { title: 'Partner Dashboard', href: '/dashboard/partners', icon: BarChart3, permissions: [] },
      { title: 'All Partners', href: '/dashboard/partners/list', icon: UsersRound, permissions: [] },
      { title: 'Partner Tiers', href: '/dashboard/partners/tiers', icon: Trophy, permissions: [] },
      { title: 'Partner Commissions', href: '/dashboard/partners/commissions', icon: Wallet, permissions: [] },
      { title: 'Payouts', href: '/dashboard/partners/payouts', icon: Banknote, permissions: [] },
      { title: 'Partner Orders', href: '/dashboard/partners/orders', icon: ShoppingCart, permissions: [] },
    ],
  },

  // ==================== 5. PROCUREMENT (P2P) ====================
  {
    title: 'Procurement',
    icon: FileInput,
    permissions: ['VENDORS_VIEW', 'PROCUREMENT_VIEW'],
    moduleCode: 'procurement',
    children: [
      { title: 'Vendors', href: '/dashboard/procurement/vendors', icon: Building2, permissions: ['VENDORS_VIEW'] },
      { title: 'Purchase Requisitions', href: '/dashboard/procurement/requisitions', icon: FileText, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Purchase Orders', href: '/dashboard/procurement/purchase-orders', icon: Clipboard, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Goods Receipt (GRN)', href: '/dashboard/procurement/grn', icon: PackageSearch, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Vendor Invoices', href: '/dashboard/procurement/vendor-invoices', icon: Receipt, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Vendor Proformas', href: '/dashboard/procurement/vendor-proformas', icon: FileCheck, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Sales Returns (SRN)', href: '/dashboard/procurement/sales-returns', icon: FileOutput, permissions: ['PROCUREMENT_VIEW'] },
      { title: '3-Way Matching', href: '/dashboard/procurement/three-way-match', icon: Scale, permissions: ['PROCUREMENT_VIEW'] },
    ],
  },

  // ==================== 6. INVENTORY ====================
  {
    title: 'Inventory',
    icon: Boxes,
    permissions: ['INVENTORY_VIEW'],
    moduleCode: 'oms_fulfillment',
    children: [
      { title: 'Stock Summary', href: '/dashboard/inventory', icon: BarChart3, permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Items', href: '/dashboard/inventory/stock-items', icon: Package, permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Movements', href: '/dashboard/inventory/movements', icon: History, permissions: ['INVENTORY_VIEW'] },
      { title: 'Warehouses', href: '/dashboard/inventory/warehouses', icon: Warehouse, permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Transfers', href: '/dashboard/inventory/transfers', icon: ArrowRightLeft, permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Adjustments', href: '/dashboard/inventory/adjustments', icon: Calculator, permissions: ['INVENTORY_VIEW'] },
    ],
  },

  // ==================== 7. WAREHOUSE (WMS) ====================
  {
    title: 'Warehouse (WMS)',
    icon: Grid3X3,
    permissions: ['INVENTORY_VIEW', 'ORDERS_VIEW'],
    moduleCode: 'oms_fulfillment',
    children: [
      { title: 'Zones', href: '/dashboard/wms/zones', icon: Layers, permissions: ['INVENTORY_VIEW'] },
      { title: 'Bins & Locations', href: '/dashboard/wms/bins', icon: Grid3X3, permissions: ['INVENTORY_VIEW'] },
      { title: 'Bin Enquiry', href: '/dashboard/wms/bin-enquiry', icon: PackageSearch, permissions: ['INVENTORY_VIEW'] },
      { title: 'Putaway Rules', href: '/dashboard/wms/putaway-rules', icon: Route, permissions: ['INVENTORY_VIEW'] },
      { title: 'Picklists', href: '/dashboard/orders/picklists', icon: ClipboardList, permissions: ['ORDERS_VIEW'] },
    ],
  },

  // ==================== 8. LOGISTICS & SHIPPING ====================
  {
    title: 'Logistics',
    icon: Truck,
    permissions: ['LOGISTICS_VIEW'],
    moduleCode: 'oms_fulfillment',
    children: [
      { title: 'Shipments', href: '/dashboard/logistics/shipments', icon: Truck, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Manifests', href: '/dashboard/logistics/manifests', icon: FileText, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Order Allocation', href: '/dashboard/orders/allocation', icon: GitBranch, permissions: ['ORDERS_VIEW'] },
      { title: 'Allocation Rules', href: '/dashboard/logistics/allocation-rules', permissions: ['LOGISTICS_VIEW'] },
      { title: 'Transporters', href: '/dashboard/logistics/transporters', icon: Building2, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Rate Cards', href: '/dashboard/logistics/rate-cards', icon: IndianRupee, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Rate Cards - B2B', href: '/dashboard/logistics/rate-cards/b2b', permissions: ['LOGISTICS_VIEW'] },
      { title: 'Rate Cards - FTL', href: '/dashboard/logistics/rate-cards/ftl', permissions: ['LOGISTICS_VIEW'] },
      { title: 'Serviceability', href: '/dashboard/logistics/serviceability', icon: MapPin, permissions: ['LOGISTICS_VIEW'] },
      { title: 'SLA Dashboard', href: '/dashboard/logistics/sla-dashboard', icon: Gauge, permissions: ['LOGISTICS_VIEW'] },
    ],
  },

  // ==================== 9. PLANNING (S&OP) ====================
  {
    title: 'Planning (S&OP)',
    icon: Target,
    permissions: ['REPORTS_VIEW', 'INVENTORY_VIEW'],
    badge: 'NEW',
    moduleCode: 'scm_ai',
    children: [
      { title: 'S&OP Dashboard', href: '/dashboard/snop', icon: Target, permissions: ['REPORTS_VIEW'] },
      { title: 'Demand Forecasting', href: '/dashboard/snop/forecasts', icon: LineChart, permissions: ['REPORTS_VIEW'] },
      { title: 'Supply Planning', href: '/dashboard/snop/supply-plans', icon: GitBranch, permissions: ['INVENTORY_VIEW'] },
      { title: 'Scenario Analysis', href: '/dashboard/snop/scenarios', icon: Layers, permissions: ['REPORTS_VIEW'] },
      { title: 'Inventory Optimization', href: '/dashboard/snop/inventory-optimization', icon: TrendingUp, permissions: ['INVENTORY_VIEW'] },
    ],
  },

  // ==================== 10. FINANCE & ACCOUNTING ====================
  // Organized by business flow: Receivables → Payables → Banking → Core Accounting → Reports → Tax → Assets
  {
    title: 'Finance',
    icon: DollarSign,
    permissions: ['FINANCE_VIEW', 'ACCOUNTS_VIEW', 'REPORTS_VIEW'],
    moduleCode: 'finance',
    children: [
      // -------- RECEIVABLES (Order-to-Cash) --------
      // Flow: Order → Ship → Invoice → Receipt → AR
      { title: '── Receivables ──', href: '#', permissions: ['FINANCE_VIEW'] },
      { title: 'Sales Invoices', href: '/dashboard/billing/invoices', icon: Receipt, permissions: ['FINANCE_VIEW'] },
      { title: 'Credit Notes', href: '/dashboard/billing/credit-notes', icon: FileOutput, permissions: ['FINANCE_VIEW'] },
      { title: 'Payment Receipts', href: '/dashboard/billing/receipts', icon: Banknote, permissions: ['FINANCE_VIEW'] },

      // -------- PAYABLES (Procure-to-Pay) --------
      // Flow: PO → GRN → Vendor Invoice → Payment → AP
      { title: '── Payables ──', href: '#', permissions: ['FINANCE_VIEW'] },
      { title: 'Vendor Invoices', href: '/dashboard/procurement/vendor-invoices', icon: FileInput, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Vendor Payments', href: '/dashboard/finance/vendor-payments', icon: CreditCard, permissions: ['FINANCE_VIEW'] },

      // -------- BANKING & CASH --------
      { title: '── Banking ──', href: '#', permissions: ['BANK_RECON_VIEW'] },
      { title: 'Bank Reconciliation', href: '/dashboard/finance/bank-reconciliation', icon: Landmark, permissions: ['BANK_RECON_VIEW'] },

      // -------- CORE ACCOUNTING (Double-Entry) --------
      // Flow: Transaction → Journal Entry → General Ledger
      { title: '── Accounting ──', href: '#', permissions: ['ACCOUNTS_VIEW'] },
      { title: 'Chart of Accounts', href: '/dashboard/finance/chart-of-accounts', icon: FolderTree, permissions: ['ACCOUNTS_VIEW'] },
      { title: 'Journal Entries', href: '/dashboard/finance/journal-entries', icon: FileText, permissions: ['JOURNALS_VIEW'] },
      { title: 'Auto Journal', href: '/dashboard/finance/auto-journal', icon: Cog, permissions: ['JOURNALS_VIEW'] },
      { title: 'General Ledger', href: '/dashboard/finance/general-ledger', icon: ScrollText, permissions: ['ACCOUNTS_VIEW'] },
      { title: 'Cost Centers', href: '/dashboard/finance/cost-centers', icon: Building, permissions: ['COST_CENTERS_VIEW'] },
      { title: 'Financial Periods', href: '/dashboard/finance/periods', icon: Calendar, permissions: ['PERIODS_VIEW'] },

      // -------- FINANCIAL REPORTS --------
      // Flow: GL → Trial Balance → Financial Statements
      { title: '── Reports ──', href: '#', permissions: ['REPORTS_VIEW'] },
      { title: 'Trial Balance', href: '/dashboard/reports/trial-balance', icon: BarChart3, permissions: ['REPORTS_VIEW'] },
      { title: 'Profit & Loss', href: '/dashboard/reports/profit-loss', icon: TrendingUp, permissions: ['REPORTS_VIEW'] },
      { title: 'Balance Sheet', href: '/dashboard/reports/balance-sheet', icon: Scale, permissions: ['REPORTS_VIEW'] },
      { title: 'Channel P&L', href: '/dashboard/reports/channel-pl', icon: Network, permissions: ['REPORTS_VIEW'] },
      { title: 'Channel Balance Sheet', href: '/dashboard/reports/channel-balance-sheet', icon: Landmark, permissions: ['REPORTS_VIEW'] },

      // -------- TAX COMPLIANCE (GST/TDS) --------
      { title: '── Tax Compliance ──', href: '#', permissions: ['GST_VIEW'] },
      { title: 'GST Filing Dashboard', href: '/dashboard/finance/gst-filing', icon: FileCheck, permissions: ['GST_VIEW'] },
      { title: 'GSTR-1 (Outward)', href: '/dashboard/finance/gstr1', icon: FileCheck, permissions: ['GST_VIEW'] },
      { title: 'GSTR-2A (Inward)', href: '/dashboard/finance/gstr2a', icon: FileCheck, permissions: ['GST_VIEW'] },
      { title: 'GSTR-3B (Summary)', href: '/dashboard/finance/gstr3b', icon: FileCheck, permissions: ['GST_VIEW'] },
      { title: 'ITC Management', href: '/dashboard/finance/itc', icon: Calculator, permissions: ['GST_VIEW'] },
      { title: 'HSN Summary', href: '/dashboard/finance/hsn-summary', icon: ClipboardList, permissions: ['GST_VIEW'] },
      { title: 'TDS Management', href: '/dashboard/finance/tds', icon: IndianRupee, permissions: ['TDS_VIEW'] },
      { title: 'E-Way Bills', href: '/dashboard/billing/eway-bills', icon: Truck, permissions: ['FINANCE_VIEW'] },

      // -------- ASSETS --------
      { title: '── Assets ──', href: '#', permissions: ['ASSETS_VIEW'] },
      { title: 'Fixed Assets', href: '/dashboard/finance/fixed-assets', icon: Building2, permissions: ['ASSETS_VIEW'] },
    ],
  },

  // ==================== 11. SERVICE & SUPPORT ====================
  {
    title: 'Service',
    icon: Wrench,
    permissions: ['SERVICE_VIEW'],
    moduleCode: 'crm_service',
    children: [
      { title: 'Service Requests', href: '/dashboard/service/requests', icon: Headphones, permissions: ['SERVICE_VIEW'] },
      { title: 'New Request', href: '/dashboard/service/requests/new', icon: FileInput, permissions: ['SERVICE_CREATE'] },
      { title: 'Installations', href: '/dashboard/service/installations', icon: CalendarCheck, permissions: ['SERVICE_VIEW'] },
      { title: 'Warranty Claims', href: '/dashboard/service/warranty-claims', icon: ShieldCheck, permissions: ['SERVICE_VIEW'] },
      { title: 'AMC Contracts', href: '/dashboard/service/amc', icon: HeartHandshake, permissions: ['SERVICE_VIEW'] },
      { title: 'Technicians', href: '/dashboard/service/technicians', icon: HardHat, permissions: ['SERVICE_VIEW'] },
      { title: 'Escalations', href: '/dashboard/crm/escalations', icon: AlertTriangle, permissions: ['SERVICE_VIEW'] },
    ],
  },

  // ==================== 12. HUMAN RESOURCES ====================
  {
    title: 'Human Resources',
    icon: Briefcase,
    permissions: ['HR_VIEW'],
    moduleCode: 'hrms',
    children: [
      { title: 'HR Dashboard', href: '/dashboard/hr', icon: BarChart3, permissions: ['HR_VIEW'] },
      { title: 'Employees', href: '/dashboard/hr/employees', icon: UsersRound, permissions: ['HR_VIEW'] },
      { title: 'Departments', href: '/dashboard/hr/departments', icon: Building2, permissions: ['HR_VIEW'] },
      { title: 'Attendance', href: '/dashboard/hr/attendance', icon: CalendarCheck, permissions: ['HR_VIEW'] },
      { title: 'Leave Management', href: '/dashboard/hr/leaves', icon: Calendar, permissions: ['HR_VIEW'] },
      { title: 'Payroll', href: '/dashboard/hr/payroll', icon: CreditCard, permissions: ['HR_VIEW'] },
      { title: 'Performance', href: '/dashboard/hr/performance', icon: Award, permissions: ['HR_VIEW'] },
      { title: 'HR Reports', href: '/dashboard/hr/reports', icon: BarChart3, permissions: ['HR_VIEW'] },
    ],
  },

  // ==================== 13. MASTER DATA ====================
  {
    title: 'Master Data',
    icon: Package,
    permissions: ['PRODUCTS_VIEW'],
    moduleCode: 'oms_fulfillment',
    children: [
      { title: 'Products', href: '/dashboard/catalog', icon: Package, permissions: ['PRODUCTS_VIEW'] },
      { title: 'New Product', href: '/dashboard/catalog/new', icon: FileInput, permissions: ['PRODUCTS_CREATE'] },
      { title: 'Categories', href: '/dashboard/catalog/categories', icon: FolderTree, permissions: ['PRODUCTS_VIEW'] },
      { title: 'Brands', href: '/dashboard/catalog/brands', icon: Tag, permissions: ['PRODUCTS_VIEW'] },
      { title: 'Serialization', href: '/dashboard/serialization', icon: Barcode, permissions: ['PRODUCTS_VIEW'] },
    ],
  },

  // ==================== 14. D2C CONTENT (CMS) ====================
  // Organized by: Overview → Layout → Homepage → Content → SEO → Settings
  {
    title: 'D2C Content',
    icon: Globe,
    permissions: ['CMS_VIEW'],
    moduleCode: 'd2c_storefront',
    children: [
      // Overview
      { title: 'CMS Overview', href: '/dashboard/cms', icon: Globe, permissions: ['CMS_VIEW'] },

      // -------- LAYOUT & NAVIGATION --------
      { title: '── Layout ──', href: '#', permissions: ['CMS_VIEW'] },
      { title: 'Header Navigation', href: '/dashboard/cms/navigation', icon: Menu, permissions: ['CMS_VIEW'] },
      { title: 'Mega Menu', href: '/dashboard/cms/mega-menu', icon: LayoutGrid, permissions: ['CMS_VIEW'] },
      { title: 'Feature Bars', href: '/dashboard/cms/feature-bars', icon: Star, permissions: ['CMS_VIEW'] },

      // -------- HOMEPAGE CONTENT --------
      { title: '── Homepage ──', href: '#', permissions: ['CMS_VIEW'] },
      { title: 'Hero Banners', href: '/dashboard/cms/banners', icon: Image, permissions: ['CMS_VIEW'] },
      { title: 'USPs/Features', href: '/dashboard/cms/usps', icon: Award, permissions: ['CMS_VIEW'] },
      { title: 'Testimonials', href: '/dashboard/cms/testimonials', icon: MessageSquare, permissions: ['CMS_VIEW'] },
      { title: 'Announcements', href: '/dashboard/cms/announcements', icon: Bell, permissions: ['CMS_VIEW'] },

      // -------- PAGES & SEO --------
      { title: '── Pages & SEO ──', href: '#', permissions: ['CMS_VIEW'] },
      { title: 'Static Pages', href: '/dashboard/cms/pages', icon: FileText, permissions: ['CMS_VIEW'] },
      { title: 'FAQ Management', href: '/dashboard/cms/faq', icon: HelpCircle, permissions: ['CMS_VIEW'] },
      { title: 'Video Guides', href: '/dashboard/cms/video-guides', icon: Video, permissions: ['CMS_VIEW'] },
      { title: 'Partner Page', href: '/dashboard/cms/partner-content', icon: Users, permissions: ['CMS_VIEW'] },
      { title: 'Contact Settings', href: '/dashboard/cms/contact-settings', icon: Phone, permissions: ['CMS_VIEW'] },
      { title: 'SEO Settings', href: '/dashboard/cms/seo', icon: Search, permissions: ['CMS_VIEW'] },

      // -------- SETTINGS --------
      { title: '── Settings ──', href: '#', permissions: ['CMS_VIEW'] },
      { title: 'Site Settings', href: '/dashboard/cms/settings', icon: Settings, permissions: ['CMS_VIEW'] },
    ],
  },

  // ==================== 15. ADMINISTRATION ====================
  {
    title: 'Administration',
    icon: Cog,
    permissions: ['ACCESS_CONTROL_VIEW', 'SETTINGS_VIEW'],
    moduleCode: 'system_admin',
    children: [
      { title: 'Users', href: '/dashboard/access-control/users', icon: Users, permissions: ['ACCESS_CONTROL_VIEW'] },
      { title: 'Roles', href: '/dashboard/access-control/roles', icon: Shield, permissions: ['ACCESS_CONTROL_VIEW'] },
      { title: 'Permissions', href: '/dashboard/access-control/permissions', icon: ShieldCheck, permissions: ['ACCESS_CONTROL_VIEW'] },
      { title: 'Approvals', href: '/dashboard/approvals', icon: CheckSquare, permissions: ['ORDERS_VIEW'] },
      { title: 'Audit Logs', href: '/dashboard/audit-logs', icon: History, permissions: ['ACCESS_CONTROL_VIEW'] },
      { title: 'Notifications', href: '/dashboard/notifications', icon: Bell, permissions: [] },
      { title: 'Settings', href: '/dashboard/settings', icon: Settings, permissions: ['SETTINGS_VIEW'] },
      { title: 'Subscriptions', href: '/dashboard/settings/subscriptions', icon: CreditCard, permissions: ['SETTINGS_VIEW'] },
      { title: 'Billing', href: '/dashboard/settings/billing', icon: Receipt, permissions: ['SETTINGS_VIEW'] },
    ],
  },
];
