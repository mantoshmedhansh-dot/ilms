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
  Award,
  Globe,
  Image,
  MessageSquare,
  Search,
  Menu,
  Star,
  LayoutGrid,
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
 * ILMS.AI ERP - CONSOLIDATED 6-MODULE NAVIGATION
 *
 * Module Structure:
 * 1. Core Platform - Dashboard, Administration, Settings
 * 2. OMS & WMS - Orders, Procurement, Inventory, Warehouse, Logistics, Master Data
 * 3. Finance - Accounting, Billing, Tax Compliance, Banking
 * 4. Sales & CX - CRM, Service, D2C Storefront, Marketing
 * 5. AI Insights - Intelligence, Forecasting, S&OP Planning
 * 6. HRMS - Employees, Attendance, Payroll, Performance
 */

export const navigation: NavItem[] = [
  // ==================== 1. CORE PLATFORM ====================
  {
    title: 'Core Platform',
    icon: LayoutDashboard,
    permissions: [],
    moduleCode: 'core',
    children: [
      // Dashboard
      { title: '── Dashboard ──', href: '#', permissions: [] },
      { title: 'Overview', href: '/dashboard', icon: LayoutDashboard, permissions: [] },

      // Administration
      { title: '── Administration ──', href: '#', permissions: ['ACCESS_CONTROL_VIEW'] },
      { title: 'Users', href: '/dashboard/access-control/users', icon: Users, permissions: ['ACCESS_CONTROL_VIEW'] },
      { title: 'Roles', href: '/dashboard/access-control/roles', icon: Shield, permissions: ['ACCESS_CONTROL_VIEW'] },
      { title: 'Permissions', href: '/dashboard/access-control/permissions', icon: ShieldCheck, permissions: ['ACCESS_CONTROL_VIEW'] },
      { title: 'Approvals', href: '/dashboard/approvals', icon: CheckSquare, permissions: ['ORDERS_VIEW'] },
      { title: 'Audit Logs', href: '/dashboard/audit-logs', icon: History, permissions: ['ACCESS_CONTROL_VIEW'] },

      // Settings
      { title: '── Settings ──', href: '#', permissions: ['SETTINGS_VIEW'] },
      { title: 'Notifications', href: '/dashboard/notifications', icon: Bell, permissions: [] },
      { title: 'System Settings', href: '/dashboard/settings', icon: Settings, permissions: ['SETTINGS_VIEW'] },
      { title: 'Subscriptions', href: '/dashboard/settings/subscriptions', icon: CreditCard, permissions: ['SETTINGS_VIEW'] },
      { title: 'Billing', href: '/dashboard/settings/billing', icon: Receipt, permissions: ['SETTINGS_VIEW'] },
    ],
  },

  // ==================== 2. OMS & WMS ====================
  {
    title: 'OMS & WMS',
    icon: Boxes,
    permissions: ['ORDERS_VIEW', 'INVENTORY_VIEW'],
    moduleCode: 'oms_wms',
    children: [
      // Orders & Sales
      { title: '── Orders ──', href: '#', permissions: ['ORDERS_VIEW'] },
      { title: 'All Orders', href: '/dashboard/orders', icon: ShoppingCart, permissions: ['ORDERS_VIEW'] },
      { title: 'New Order', href: '/dashboard/orders/new', icon: FileInput, permissions: ['ORDERS_CREATE'] },
      { title: 'Picklists', href: '/dashboard/orders/picklists', icon: ClipboardList, permissions: ['ORDERS_VIEW'] },

      // Channels & Distribution
      { title: '── Channels ──', href: '#', permissions: ['ORDERS_VIEW'] },
      { title: 'Sales Channels', href: '/dashboard/channels', icon: Network, permissions: ['ORDERS_VIEW'] },
      { title: 'Marketplaces', href: '/dashboard/channels/marketplaces', icon: Store, permissions: ['ORDERS_VIEW'] },
      { title: 'Channel Pricing', href: '/dashboard/channels/pricing', icon: DollarSign, permissions: ['ORDERS_VIEW'] },
      { title: 'Omnichannel (BOPIS)', href: '/dashboard/omnichannel', icon: Store, permissions: ['ORDERS_VIEW'] },
      { title: 'Dealers', href: '/dashboard/distribution/dealers', icon: Handshake, permissions: ['ORDERS_VIEW'] },
      { title: 'Franchisees', href: '/dashboard/distribution/franchisees', icon: Building2, permissions: ['ORDERS_VIEW'] },
      { title: 'Pricing Tiers', href: '/dashboard/distribution/pricing-tiers', icon: Layers, permissions: ['ORDERS_VIEW'] },

      // Promotions
      { title: '── Promotions ──', href: '#', permissions: ['MARKETING_VIEW'] },
      { title: 'Promotions', href: '/dashboard/marketing/promotions', icon: BadgePercent, permissions: ['MARKETING_VIEW'] },
      { title: 'Coupons', href: '/dashboard/marketing/coupons', icon: BadgePercent, permissions: ['MARKETING_VIEW'] },
      { title: 'Sales Commissions', href: '/dashboard/marketing/commissions', icon: Banknote, permissions: ['MARKETING_VIEW'] },

      // Procurement
      { title: '── Procurement ──', href: '#', permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Vendors', href: '/dashboard/procurement/vendors', icon: Building2, permissions: ['VENDORS_VIEW'] },
      { title: 'Purchase Requisitions', href: '/dashboard/procurement/requisitions', icon: FileText, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Purchase Orders', href: '/dashboard/procurement/purchase-orders', icon: Clipboard, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Goods Receipt (GRN)', href: '/dashboard/procurement/grn', icon: PackageSearch, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Vendor Proformas', href: '/dashboard/procurement/vendor-proformas', icon: FileCheck, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Sales Returns (SRN)', href: '/dashboard/procurement/sales-returns', icon: FileOutput, permissions: ['PROCUREMENT_VIEW'] },
      { title: '3-Way Matching', href: '/dashboard/procurement/three-way-match', icon: Scale, permissions: ['PROCUREMENT_VIEW'] },

      // Inventory
      { title: '── Inventory ──', href: '#', permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Summary', href: '/dashboard/inventory', icon: BarChart3, permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Items', href: '/dashboard/inventory/stock-items', icon: Package, permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Movements', href: '/dashboard/inventory/movements', icon: History, permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Transfers', href: '/dashboard/inventory/transfers', icon: ArrowRightLeft, permissions: ['INVENTORY_VIEW'] },
      { title: 'Stock Adjustments', href: '/dashboard/inventory/adjustments', icon: Calculator, permissions: ['INVENTORY_VIEW'] },

      // Warehouse (WMS)
      { title: '── Warehouse ──', href: '#', permissions: ['INVENTORY_VIEW'] },
      { title: 'Warehouses', href: '/dashboard/wms/warehouses', icon: Warehouse, permissions: ['INVENTORY_VIEW'] },
      { title: 'Zones', href: '/dashboard/wms/zones', icon: Layers, permissions: ['INVENTORY_VIEW'] },
      { title: 'Bins & Locations', href: '/dashboard/wms/bins', icon: Grid3X3, permissions: ['INVENTORY_VIEW'] },
      { title: 'Bin Enquiry', href: '/dashboard/wms/bin-enquiry', icon: PackageSearch, permissions: ['INVENTORY_VIEW'] },
      { title: 'Putaway Rules', href: '/dashboard/wms/putaway-rules', icon: Route, permissions: ['INVENTORY_VIEW'] },
      { title: 'Wave Picking', href: '/dashboard/wms/waves', icon: Boxes, permissions: ['INVENTORY_VIEW'] },
      { title: 'Labor Management', href: '/dashboard/wms/labor', icon: HardHat, permissions: ['INVENTORY_VIEW'] },
      { title: 'Mobile WMS', href: '/dashboard/wms/mobile', icon: Barcode, permissions: ['INVENTORY_VIEW'] },
      { title: 'Yard Management', href: '/dashboard/wms/yard', icon: MapPin, permissions: ['INVENTORY_VIEW'] },
      { title: 'Quality Control', href: '/dashboard/wms/quality', icon: ShieldCheck, permissions: ['INVENTORY_VIEW'] },
      { title: 'Kitting & Assembly', href: '/dashboard/wms/kitting', icon: GitBranch, permissions: ['INVENTORY_VIEW'] },
      { title: 'Returns Processing', href: '/dashboard/wms/returns', icon: FileOutput, permissions: ['INVENTORY_VIEW'] },
      { title: 'Warehouse Billing', href: '/dashboard/wms/billing', icon: Receipt, permissions: ['INVENTORY_VIEW'] },
      { title: 'Cycle Counting', href: '/dashboard/wms/cycle-count', icon: Clipboard, permissions: ['INVENTORY_VIEW'] },
      { title: 'WMS Reports', href: '/dashboard/wms/reports', icon: BarChart3, permissions: ['INVENTORY_VIEW'] },

      // Logistics
      { title: '── Logistics ──', href: '#', permissions: ['LOGISTICS_VIEW'] },
      { title: 'Shipments', href: '/dashboard/logistics/shipments', icon: Truck, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Order Tracking', href: '/dashboard/logistics/tracking', icon: MapPin, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Manifests', href: '/dashboard/logistics/manifests', icon: FileText, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Order Allocation', href: '/dashboard/orders/allocation', icon: GitBranch, permissions: ['ORDERS_VIEW'] },
      { title: 'Allocation Rules', href: '/dashboard/logistics/allocation-rules', permissions: ['LOGISTICS_VIEW'] },
      { title: 'DOM (Order Routing)', href: '/dashboard/logistics/dom', icon: Network, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Backorders', href: '/dashboard/logistics/backorders', icon: Clock, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Preorders', href: '/dashboard/logistics/preorders', icon: Calendar, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Transporters', href: '/dashboard/logistics/transporters', icon: Building2, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Rate Cards', href: '/dashboard/logistics/rate-cards', icon: IndianRupee, permissions: ['LOGISTICS_VIEW'] },
      { title: 'Rate Cards - B2B', href: '/dashboard/logistics/rate-cards/b2b', permissions: ['LOGISTICS_VIEW'] },
      { title: 'Rate Cards - FTL', href: '/dashboard/logistics/rate-cards/ftl', permissions: ['LOGISTICS_VIEW'] },
      { title: 'Serviceability', href: '/dashboard/logistics/serviceability', icon: MapPin, permissions: ['LOGISTICS_VIEW'] },
      { title: 'SLA Dashboard', href: '/dashboard/logistics/sla-dashboard', icon: Gauge, permissions: ['LOGISTICS_VIEW'] },

      // Master Data
      { title: '── Master Data ──', href: '#', permissions: ['PRODUCTS_VIEW'] },
      { title: 'Products', href: '/dashboard/catalog', icon: Package, permissions: ['PRODUCTS_VIEW'] },
      { title: 'New Product', href: '/dashboard/catalog/new', icon: FileInput, permissions: ['PRODUCTS_CREATE'] },
      { title: 'Categories', href: '/dashboard/catalog/categories', icon: FolderTree, permissions: ['PRODUCTS_VIEW'] },
      { title: 'Brands', href: '/dashboard/catalog/brands', icon: Tag, permissions: ['PRODUCTS_VIEW'] },
      { title: 'Serialization', href: '/dashboard/serialization', icon: Barcode, permissions: ['PRODUCTS_VIEW'] },
    ],
  },

  // ==================== 3. FINANCE ====================
  {
    title: 'Finance',
    icon: DollarSign,
    permissions: ['FINANCE_VIEW', 'ACCOUNTS_VIEW', 'REPORTS_VIEW'],
    moduleCode: 'finance',
    children: [
      // Receivables (Order-to-Cash)
      { title: '── Receivables ──', href: '#', permissions: ['FINANCE_VIEW'] },
      { title: 'Sales Invoices', href: '/dashboard/billing/invoices', icon: Receipt, permissions: ['FINANCE_VIEW'] },
      { title: 'Credit Notes', href: '/dashboard/billing/credit-notes', icon: FileOutput, permissions: ['FINANCE_VIEW'] },
      { title: 'Payment Receipts', href: '/dashboard/billing/receipts', icon: Banknote, permissions: ['FINANCE_VIEW'] },

      // Payables (Procure-to-Pay)
      { title: '── Payables ──', href: '#', permissions: ['FINANCE_VIEW'] },
      { title: 'Vendor Invoices', href: '/dashboard/procurement/vendor-invoices', icon: FileInput, permissions: ['PROCUREMENT_VIEW'] },
      { title: 'Vendor Payments', href: '/dashboard/finance/vendor-payments', icon: CreditCard, permissions: ['FINANCE_VIEW'] },

      // Banking & Cash
      { title: '── Banking ──', href: '#', permissions: ['BANK_RECON_VIEW'] },
      { title: 'Bank Reconciliation', href: '/dashboard/finance/bank-reconciliation', icon: Landmark, permissions: ['BANK_RECON_VIEW'] },

      // Core Accounting (Double-Entry)
      { title: '── Accounting ──', href: '#', permissions: ['ACCOUNTS_VIEW'] },
      { title: 'Chart of Accounts', href: '/dashboard/finance/chart-of-accounts', icon: FolderTree, permissions: ['ACCOUNTS_VIEW'] },
      { title: 'Journal Entries', href: '/dashboard/finance/journal-entries', icon: FileText, permissions: ['JOURNALS_VIEW'] },
      { title: 'Auto Journal', href: '/dashboard/finance/auto-journal', icon: Cog, permissions: ['JOURNALS_VIEW'] },
      { title: 'General Ledger', href: '/dashboard/finance/general-ledger', icon: ScrollText, permissions: ['ACCOUNTS_VIEW'] },
      { title: 'Cost Centers', href: '/dashboard/finance/cost-centers', icon: Building, permissions: ['COST_CENTERS_VIEW'] },
      { title: 'Financial Periods', href: '/dashboard/finance/periods', icon: Calendar, permissions: ['PERIODS_VIEW'] },

      // Financial Reports
      { title: '── Reports ──', href: '#', permissions: ['REPORTS_VIEW'] },
      { title: 'Trial Balance', href: '/dashboard/reports/trial-balance', icon: BarChart3, permissions: ['REPORTS_VIEW'] },
      { title: 'Profit & Loss', href: '/dashboard/reports/profit-loss', icon: TrendingUp, permissions: ['REPORTS_VIEW'] },
      { title: 'Balance Sheet', href: '/dashboard/reports/balance-sheet', icon: Scale, permissions: ['REPORTS_VIEW'] },
      { title: 'Channel P&L', href: '/dashboard/reports/channel-pl', icon: Network, permissions: ['REPORTS_VIEW'] },
      { title: 'Channel Balance Sheet', href: '/dashboard/reports/channel-balance-sheet', icon: Landmark, permissions: ['REPORTS_VIEW'] },

      // Tax Compliance (GST/TDS)
      { title: '── Tax Compliance ──', href: '#', permissions: ['GST_VIEW'] },
      { title: 'GST Filing Dashboard', href: '/dashboard/finance/gst-filing', icon: FileCheck, permissions: ['GST_VIEW'] },
      { title: 'GSTR-1 (Outward)', href: '/dashboard/finance/gstr1', icon: FileCheck, permissions: ['GST_VIEW'] },
      { title: 'GSTR-2A (Inward)', href: '/dashboard/finance/gstr2a', icon: FileCheck, permissions: ['GST_VIEW'] },
      { title: 'GSTR-3B (Summary)', href: '/dashboard/finance/gstr3b', icon: FileCheck, permissions: ['GST_VIEW'] },
      { title: 'ITC Management', href: '/dashboard/finance/itc', icon: Calculator, permissions: ['GST_VIEW'] },
      { title: 'HSN Summary', href: '/dashboard/finance/hsn-summary', icon: ClipboardList, permissions: ['GST_VIEW'] },
      { title: 'TDS Management', href: '/dashboard/finance/tds', icon: IndianRupee, permissions: ['TDS_VIEW'] },
      { title: 'E-Way Bills', href: '/dashboard/billing/eway-bills', icon: Truck, permissions: ['FINANCE_VIEW'] },

      // Assets
      { title: '── Assets ──', href: '#', permissions: ['ASSETS_VIEW'] },
      { title: 'Fixed Assets', href: '/dashboard/finance/fixed-assets', icon: Building2, permissions: ['ASSETS_VIEW'] },
    ],
  },

  // ==================== 4. SALES & CX ====================
  {
    title: 'Sales & CX',
    icon: UserCircle,
    permissions: ['CRM_VIEW', 'SERVICE_VIEW', 'CMS_VIEW'],
    moduleCode: 'sales_cx',
    children: [
      // CRM
      { title: '── CRM ──', href: '#', permissions: ['CRM_VIEW'] },
      { title: 'Customers', href: '/dashboard/crm/customers', icon: UserCircle, permissions: ['CRM_VIEW'] },
      { title: 'Customer 360', href: '/dashboard/crm/customer-360', icon: Target, permissions: ['CRM_VIEW'] },
      { title: 'Leads', href: '/dashboard/crm/leads', icon: UserPlus, permissions: ['CRM_VIEW'] },
      { title: 'Call Center', href: '/dashboard/crm/call-center', icon: Phone, permissions: ['CRM_VIEW'] },
      { title: 'Abandoned Carts', href: '/dashboard/crm/abandoned-carts', icon: ShoppingCart, permissions: ['CRM_VIEW'] },

      // Service & Support
      { title: '── Service ──', href: '#', permissions: ['SERVICE_VIEW'] },
      { title: 'Service Requests', href: '/dashboard/service/requests', icon: Headphones, permissions: ['SERVICE_VIEW'] },
      { title: 'New Request', href: '/dashboard/service/requests/new', icon: FileInput, permissions: ['SERVICE_CREATE'] },
      { title: 'Installations', href: '/dashboard/service/installations', icon: CalendarCheck, permissions: ['SERVICE_VIEW'] },
      { title: 'Warranty Claims', href: '/dashboard/service/warranty-claims', icon: ShieldCheck, permissions: ['SERVICE_VIEW'] },
      { title: 'AMC Contracts', href: '/dashboard/service/amc', icon: HeartHandshake, permissions: ['SERVICE_VIEW'] },
      { title: 'Technicians', href: '/dashboard/service/technicians', icon: HardHat, permissions: ['SERVICE_VIEW'] },
      { title: 'Escalations', href: '/dashboard/crm/escalations', icon: AlertTriangle, permissions: ['SERVICE_VIEW'] },

      // D2C Content (CMS)
      { title: '── D2C Storefront ──', href: '#', permissions: ['CMS_VIEW'] },
      { title: 'CMS Overview', href: '/dashboard/cms', icon: Globe, permissions: ['CMS_VIEW'] },
      { title: 'Header Navigation', href: '/dashboard/cms/navigation', icon: Menu, permissions: ['CMS_VIEW'] },
      { title: 'Mega Menu', href: '/dashboard/cms/mega-menu', icon: LayoutGrid, permissions: ['CMS_VIEW'] },
      { title: 'Feature Bars', href: '/dashboard/cms/feature-bars', icon: Star, permissions: ['CMS_VIEW'] },
      { title: 'Hero Banners', href: '/dashboard/cms/banners', icon: Image, permissions: ['CMS_VIEW'] },
      { title: 'USPs/Features', href: '/dashboard/cms/usps', icon: Award, permissions: ['CMS_VIEW'] },
      { title: 'Testimonials', href: '/dashboard/cms/testimonials', icon: MessageSquare, permissions: ['CMS_VIEW'] },
      { title: 'Announcements', href: '/dashboard/cms/announcements', icon: Bell, permissions: ['CMS_VIEW'] },
      { title: 'Static Pages', href: '/dashboard/cms/pages', icon: FileText, permissions: ['CMS_VIEW'] },
      { title: 'FAQ Management', href: '/dashboard/cms/faq', icon: HelpCircle, permissions: ['CMS_VIEW'] },
      { title: 'Video Guides', href: '/dashboard/cms/video-guides', icon: Video, permissions: ['CMS_VIEW'] },
      { title: 'Partner Page', href: '/dashboard/cms/partner-content', icon: Users, permissions: ['CMS_VIEW'] },
      { title: 'Contact Settings', href: '/dashboard/cms/contact-settings', icon: Phone, permissions: ['CMS_VIEW'] },
      { title: 'SEO Settings', href: '/dashboard/cms/seo', icon: Search, permissions: ['CMS_VIEW'] },
      { title: 'Site Settings', href: '/dashboard/cms/settings', icon: Settings, permissions: ['CMS_VIEW'] },
    ],
  },

  // ==================== 5. AI INSIGHTS ====================
  {
    title: 'AI Insights',
    icon: Brain,
    permissions: [],
    badge: 'AI',
    moduleCode: 'ai_insights',
    children: [
      // Intelligence
      { title: '── Intelligence ──', href: '#', permissions: [] },
      { title: 'AI Hub', href: '/dashboard/ai', icon: Lightbulb, permissions: [] },
      { title: 'Insights Dashboard', href: '/dashboard/insights', icon: TrendingUp, permissions: [] },
      { title: 'Reorder Suggestions', href: '/dashboard/insights/reorder', icon: PackageSearch, permissions: [] },
      { title: 'Churn Risk Analysis', href: '/dashboard/insights/churn-risk', icon: AlertTriangle, permissions: [] },
      { title: 'Slow Moving Stock', href: '/dashboard/insights/slow-moving', icon: Clock, permissions: [] },
      { title: 'Campaigns', href: '/dashboard/marketing/campaigns', icon: Megaphone, permissions: ['MARKETING_VIEW'] },

      // Planning (S&OP)
      { title: '── Planning (S&OP) ──', href: '#', permissions: ['REPORTS_VIEW'] },
      { title: 'S&OP Dashboard', href: '/dashboard/snop', icon: Target, permissions: ['REPORTS_VIEW'] },
      { title: 'Demand Forecasting', href: '/dashboard/snop/forecasts', icon: LineChart, permissions: ['REPORTS_VIEW'] },
      { title: 'Supply Planning', href: '/dashboard/snop/supply-plans', icon: GitBranch, permissions: ['INVENTORY_VIEW'] },
      { title: 'Scenario Analysis', href: '/dashboard/snop/scenarios', icon: Layers, permissions: ['REPORTS_VIEW'] },
      { title: 'Inventory Optimization', href: '/dashboard/snop/inventory-optimization', icon: TrendingUp, permissions: ['INVENTORY_VIEW'] },
    ],
  },

  // ==================== 6. HRMS ====================
  {
    title: 'HRMS',
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
];
