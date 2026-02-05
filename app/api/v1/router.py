from fastapi import APIRouter

from app.api.v1.endpoints import (
    # Tenant Onboarding (Phase 3)
    onboarding,
    module_management,
    tenant_admin,
    subscription_billing,  # Phase 5
    # Testing (Phase 1 Multi-Tenant)
    test_modules,
    # Access Control
    auth,
    roles,
    permissions,
    users,
    access_control,
    # GST e-Filing & ITC
    gst_filing,
    # CMS (D2C Content Management)
    cms,
    # File Uploads
    uploads,
    # Address Lookup (Google Places + DigiPin)
    address,
    # HR & Payroll
    hr,
    # Fixed Assets
    fixed_assets,
    # Notifications
    notifications,
    # AI Insights
    insights,
    # AI Services (Advanced)
    ai,
    # S&OP (Sales and Operations Planning)
    snop,
    # Product Catalog
    categories,
    brands,
    products,
    # CRM & Orders
    customers,
    orders,
    # Inventory Management
    warehouses,
    inventory,
    transfers,
    stock_adjustments,  # Stock Adjustments & Audits
    # Service Management
    service_requests,
    technicians,
    installations,  # Installation & Warranty
    # Vendor & Procurement
    vendors,
    purchase,
    grn,  # Goods Receipt Notes
    vendor_invoices,  # Vendor Invoice & 3-Way Matching
    vendor_proformas,  # Vendor Proforma/Quotations
    vendor_payments,  # Vendor Payments (Finance)
    sales_returns,  # Sales Return Notes (SRN)
    # Accounting & Finance
    accounting,
    billing,
    banking,  # Bank Statement Import & Reconciliation
    credentials,  # Encrypted Credentials Management
    auto_journal,  # Auto Journal Entry Generation
    tds,  # TDS Certificate Generation
    # Dealer/Distributor
    dealers,
    # Commission & Incentives
    commissions,
    # Promotions & Loyalty
    promotions,
    # Multi-Channel Commerce
    channels,
    marketplaces,  # Marketplace API Integration
    channel_reports,  # Channel P&L & Balance Sheet
    # Reports (Dashboard)
    reports,  # Channel P&L for frontend dashboard
    # Company/Business Entity
    company,
    # OMS/WMS
    transporters,
    wms,
    picklists,
    shipments,
    manifests,
    serviceability,  # Pincode Serviceability & Order Allocation
    rate_cards,  # Rate Cards (D2C, B2B, FTL)
    # DOM (Distributed Order Management)
    dom,
    # Advanced WMS (Wave Picking, Task Interleaving, Slot Optimization)
    wms_advanced,
    # Omnichannel (BOPIS/BORIS/Ship-from-Store)
    omnichannel,
    # Labor Management (Workforce Optimization)
    labor,
    # Mobile WMS (RF Scanner & Mobile Operations)
    mobile_wms,
    # Yard Management (Dock Scheduling & Yard Operations)
    yard_management,
    # Quality Control (Inspection & Quality Management)
    quality_control,
    # Call Center CRM
    call_center,
    # Lead Management
    leads,
    # Escalation Management
    escalations,
    # Campaign Management
    campaigns,
    # Franchisee CRM
    franchisees,
    # Serialization (Barcode Generation)
    serialization,
    # Multi-Level Approval Workflow
    approvals,
    # Payments (Razorpay)
    payments,
    # Public Storefront APIs
    storefront,
    # Customer Self-Service Portal
    portal,
    # D2C Customer Authentication
    d2c_auth,
    # Product Reviews & Q&A
    reviews,
    questions,
    # Coupons
    coupons,
    # Returns & Refunds
    returns,
    # Order Tracking
    order_tracking,
    # Abandoned Cart
    abandoned_cart,
    # Shipping (Shiprocket Integration)
    shipping,
    # AMC/Warranty Management
    amc,
    # Audit Logs
    audit_logs,
    # Dashboard Charts
    dashboard_charts,
    # Community Partners (Meesho-style)
    partners,
)


# Create main API router
api_router = APIRouter(prefix="/api/v1")

# ==================== Tenant Onboarding (Phase 3 - Public) ====================
api_router.include_router(
    onboarding.router,
    prefix="/onboarding",
    tags=["Onboarding"]
)

# ==================== Module Management (Phase 3C) ====================
api_router.include_router(
    module_management.router,
    prefix="/modules",
    tags=["Module Management"]
)

# ==================== Tenant Administration (Phase 3D) ====================
api_router.include_router(
    tenant_admin.router,
    prefix="/admin",
    tags=["Tenant Administration"]
)

# ==================== Subscription Billing (Phase 5) ====================
api_router.include_router(
    subscription_billing.router,
    prefix="/billing",
    tags=["Subscription Billing"]
)

# ==================== Testing (Phase 1 Multi-Tenant) ====================
api_router.include_router(
    test_modules.router,
    tags=["Testing - Phase 1 Multi-Tenant"]
)

# ==================== Access Control ====================
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)
api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["Roles"]
)
api_router.include_router(
    permissions.router,
    prefix="/permissions",
    tags=["Permissions"]
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)
api_router.include_router(
    access_control.router,
    prefix="/access-control",
    tags=["Access Control"]
)

# ==================== Product Catalog ====================
api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["Categories"]
)
api_router.include_router(
    brands.router,
    prefix="/brands",
    tags=["Brands"]
)
api_router.include_router(
    products.router,
    prefix="/products",
    tags=["Products"]
)

# ==================== CRM & Orders ====================
api_router.include_router(
    customers.router,
    prefix="/customers",
    tags=["Customers"]
)
api_router.include_router(
    orders.router,
    prefix="/orders",
    tags=["Orders"]
)

# ==================== Inventory Management ====================
api_router.include_router(
    warehouses.router,
    prefix="/warehouses",
    tags=["Warehouses"]
)
api_router.include_router(
    inventory.router,
    prefix="/inventory",
    tags=["Inventory"]
)
api_router.include_router(
    transfers.router,
    prefix="/transfers",
    tags=["Stock Transfers"]
)

# ==================== Service Management ====================
api_router.include_router(
    service_requests.router,
    prefix="/service-requests",
    tags=["Service Requests"]
)
api_router.include_router(
    technicians.router,
    prefix="/technicians",
    tags=["Technicians"]
)
api_router.include_router(
    installations.router,
    prefix="/installations",
    tags=["Installations & Warranty"]
)

# ==================== Vendor & Procurement (P2P) ====================
api_router.include_router(
    vendors.router,
    prefix="/vendors",
    tags=["Vendors/Suppliers"]
)
api_router.include_router(
    purchase.router,
    prefix="/purchase",
    tags=["Purchase/Procurement"]
)

# ==================== Accounting & Finance ====================
api_router.include_router(
    accounting.router,
    prefix="/accounting",
    tags=["Accounting"]
)
api_router.include_router(
    billing.router,
    prefix="/billing",
    tags=["Billing/E-Invoice"]
)
api_router.include_router(
    banking.router,
    prefix="/banking",
    tags=["Banking/Reconciliation"]
)
api_router.include_router(
    credentials.router,
    prefix="/credentials",
    tags=["Credentials/Security"]
)
api_router.include_router(
    auto_journal.router,
    prefix="/auto-journal",
    tags=["Auto Journal Entry"]
)
api_router.include_router(
    tds.router,
    prefix="/tds",
    tags=["TDS Certificates"]
)

# ==================== GST e-Filing & ITC ====================
api_router.include_router(
    gst_filing.router,
    prefix="/gst",
    tags=["GST e-Filing & ITC"]
)

# ==================== Dealer/Distributor ====================
api_router.include_router(
    dealers.router,
    prefix="/dealers",
    tags=["Dealers/Distributors"]
)

# ==================== Commission & Incentives ====================
api_router.include_router(
    commissions.router,
    prefix="/commissions",
    tags=["Commissions"]
)

# ==================== Promotions & Loyalty ====================
api_router.include_router(
    promotions.router,
    prefix="/promotions",
    tags=["Promotions/Loyalty"]
)

# ==================== Multi-Channel Commerce ====================
api_router.include_router(
    channels.router,
    prefix="/channels",
    tags=["Sales Channels"]
)
api_router.include_router(
    marketplaces.router,
    prefix="/marketplaces",
    tags=["Marketplace Integration"]
)

# ==================== Company/Business Entity ====================
api_router.include_router(
    company.router,
    prefix="/company",
    tags=["Company/Business Entity"]
)

# ==================== OMS/WMS - Logistics & Fulfillment ====================
api_router.include_router(
    transporters.router,
    prefix="/transporters",
    tags=["Transporters/Carriers"]
)
api_router.include_router(
    wms.router,
    prefix="/wms",
    tags=["WMS (Zones/Bins/PutAway)"]
)
api_router.include_router(
    picklists.router,
    prefix="/picklists",
    tags=["Picklists (Order Picking)"]
)
api_router.include_router(
    shipments.router,
    prefix="/shipments",
    tags=["Shipments"]
)
api_router.include_router(
    manifests.router,
    prefix="/manifests",
    tags=["Manifests (Transporter Handover)"]
)
api_router.include_router(
    serviceability.router,
    tags=["Serviceability & Order Allocation"]
)
api_router.include_router(
    rate_cards.router,
    prefix="/rate-cards",
    tags=["Rate Cards (D2C/B2B/FTL)"]
)

# ==================== DOM (Distributed Order Management) ====================
api_router.include_router(
    dom.router,
    prefix="/dom",
    tags=["Distributed Order Management"]
)

# ==================== Advanced WMS (Wave Picking, Task Interleaving) ====================
api_router.include_router(
    wms_advanced.router,
    prefix="/wms-advanced",
    tags=["Advanced WMS"]
)

# ==================== Omnichannel (BOPIS/BORIS/Ship-from-Store) ====================
api_router.include_router(
    omnichannel.router,
    prefix="/omnichannel",
    tags=["Omnichannel"]
)

# ==================== Labor Management (Workforce Optimization) ====================
api_router.include_router(
    labor.router,
    prefix="/labor",
    tags=["Labor Management"]
)

# ==================== Mobile WMS (RF Scanner & Mobile Operations) ====================
api_router.include_router(
    mobile_wms.router,
    prefix="/mobile-wms",
    tags=["Mobile WMS"]
)

# ==================== Yard Management (Dock Scheduling & Yard Operations) ====================
api_router.include_router(
    yard_management.router,
    prefix="/yard",
    tags=["Yard Management"]
)

# ==================== Quality Control (Inspection & Quality Management) ====================
api_router.include_router(
    quality_control.router,
    prefix="/qc",
    tags=["Quality Control"]
)

# ==================== Call Center CRM ====================
api_router.include_router(
    call_center.router,
    prefix="/call-center",
    tags=["Call Center CRM"]
)

# ==================== Lead Management ====================
api_router.include_router(
    leads.router,
    prefix="/leads",
    tags=["Lead Management"]
)

# ==================== Escalation Management ====================
api_router.include_router(
    escalations.router,
    prefix="/escalations",
    tags=["Escalation Management"]
)

# ==================== Campaign Management ====================
api_router.include_router(
    campaigns.router,
    prefix="/campaigns",
    tags=["Campaign Management"]
)

# ==================== Franchisee CRM ====================
api_router.include_router(
    franchisees.router,
    prefix="/franchisees",
    tags=["Franchisee CRM"]
)

# ==================== Serialization (Barcode Generation) ====================
api_router.include_router(
    serialization.router,
    prefix="/serialization",
    tags=["Serialization (Barcode Generation)"]
)

# ==================== Multi-Level Approval Workflow ====================
api_router.include_router(
    approvals.router,
    tags=["Approvals (Finance)"]
)

# ==================== Payments (Razorpay) ====================
api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"]
)

# ==================== Public Storefront APIs (No Auth) ====================
api_router.include_router(
    storefront.router,
    prefix="/storefront",
    tags=["Storefront (Public)"]
)

# ==================== Address Lookup (Google Places + DigiPin) ====================
api_router.include_router(
    address.router,
    prefix="/address",
    tags=["Address Lookup"]
)

# ==================== Customer Self-Service Portal ====================
api_router.include_router(
    portal.router,
    prefix="/portal",
    tags=["Customer Portal"]
)

# ==================== HR & Payroll ====================
api_router.include_router(
    hr.router,
    prefix="/hr",
    tags=["HR & Payroll"]
)

# ==================== Fixed Assets ====================
api_router.include_router(
    fixed_assets.router,
    prefix="/fixed-assets",
    tags=["Fixed Assets"]
)

# ==================== Notifications ====================
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"]
)

# ==================== AI Insights ====================
api_router.include_router(
    insights.router,
    prefix="/insights",
    tags=["AI Insights"]
)

# ==================== AI Services (Advanced) ====================
api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI Services"]
)

# ==================== S&OP (Sales and Operations Planning) ====================
api_router.include_router(
    snop.router,
    prefix="/snop",
    tags=["S&OP (Sales & Operations Planning)"]
)

# ==================== D2C Customer Authentication ====================
api_router.include_router(
    d2c_auth.router,
    tags=["D2C Customer Authentication"]
)

# ==================== Product Reviews ====================
api_router.include_router(
    reviews.router,
    tags=["Product Reviews"]
)

# ==================== Product Q&A ====================
api_router.include_router(
    questions.router,
    tags=["Product Q&A"]
)

# ==================== Coupons ====================
api_router.include_router(
    coupons.router,
    tags=["Coupons"]
)

# ==================== Returns & Refunds ====================
api_router.include_router(
    returns.router,
    tags=["Returns & Refunds"]
)

# ==================== Order Tracking ====================
api_router.include_router(
    order_tracking.router,
    tags=["Order Tracking"]
)

# ==================== Abandoned Cart ====================
api_router.include_router(
    abandoned_cart.router,
    tags=["Abandoned Cart"]
)

# ==================== Shipping (Shiprocket) ====================
api_router.include_router(
    shipping.router,
    prefix="/shipping",
    tags=["Shipping (Shiprocket)"]
)

# ==================== File Uploads ====================
api_router.include_router(
    uploads.router,
    prefix="/uploads",
    tags=["File Uploads"]
)

# ==================== Goods Receipt Notes (GRN) ====================
api_router.include_router(
    grn.router,
    prefix="/grn",
    tags=["Goods Receipt Notes"]
)

# ==================== Vendor Invoices ====================
api_router.include_router(
    vendor_invoices.router,
    prefix="/vendor-invoices",
    tags=["Vendor Invoices"]
)

# ==================== Vendor Payments ====================
api_router.include_router(
    vendor_payments.router,
    prefix="/vendor-payments",
    tags=["Vendor Payments"]
)

# ==================== Vendor Proformas/Quotations ====================
api_router.include_router(
    vendor_proformas.router,
    prefix="/vendor-proformas",
    tags=["Vendor Proformas"]
)

# ==================== Sales Returns (SRN) ====================
api_router.include_router(
    sales_returns.router,
    prefix="/sales-returns",
    tags=["Sales Returns"]
)

# ==================== Stock Adjustments ====================
api_router.include_router(
    stock_adjustments.router,
    prefix="/stock-adjustments",
    tags=["Stock Adjustments"]
)

# ==================== AMC/Warranty Management ====================
api_router.include_router(
    amc.router,
    prefix="/amc",
    tags=["AMC/Warranty"]
)

# ==================== Audit Logs ====================
api_router.include_router(
    audit_logs.router,
    prefix="/audit-logs",
    tags=["Audit Logs"]
)

# ==================== Dashboard Charts ====================
api_router.include_router(
    dashboard_charts.router,
    prefix="/dashboard",
    tags=["Dashboard Charts"]
)

# ==================== Channel Reports ====================
api_router.include_router(
    channel_reports.router,
    prefix="/channel-reports",
    tags=["Channel Reports"]
)

# ==================== Reports (Dashboard) ====================
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"]
)

# ==================== CMS (D2C Content Management) ====================
api_router.include_router(
    cms.router,
    prefix="/cms",
    tags=["CMS (Content Management)"]
)

# ==================== Community Partners (Meesho-style) ====================
api_router.include_router(
    partners.router,
    tags=["Community Partners"]
)
