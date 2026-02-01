# ACTUAL ERP STRUCTURE - COMPLETE BREAKDOWN
## ilms.ai - Current System Organization

**Generated:** 2026-01-31
**Purpose:** Complete section-by-section breakdown of existing ERP system

---

## BACKEND API STRUCTURE

### Total Backend Endpoints: 78 Files

Located in: `app/api/v1/endpoints/`

#### Complete List of Backend APIs:

1. **abandoned_cart.py** - Abandoned cart recovery
2. **access_control.py** - Access control rules
3. **accounting.py** - Chart of accounts, journal entries, GL
4. **address.py** - Address validation (Google Places + DigiPin)
5. **ai.py** - AI-powered analytics and ML features
6. **amc.py** - Annual Maintenance Contracts
7. **approvals.py** - Multi-level approval workflows
8. **audit_logs.py** - System audit trails
9. **auth.py** - Authentication and JWT tokens
10. **auto_journal.py** - Automatic journal entry generation
11. **banking.py** - Bank reconciliation and transactions
12. **billing.py** - E-invoicing, GST compliance
13. **brands.py** - Product brand management
14. **call_center.py** - Call center CRM operations
15. **campaigns.py** - Marketing campaigns
16. **categories.py** - Product category hierarchy
17. **channel_reports.py** - Channel-wise P&L reports
18. **channels.py** - Sales channel management
19. **cms.py** - Content management system
20. **commissions.py** - Commission plans and tracking
21. **company.py** - Company/business entity setup
22. **coupons.py** - Discount coupon management
23. **credentials.py** - Encrypted credential storage
24. **customers.py** - Customer master and addresses
25. **d2c_auth.py** - D2C customer authentication
26. **dashboard_charts.py** - Dashboard data aggregation
27. **dealers.py** - Dealer management and pricing
28. **escalations.py** - Issue escalation management
29. **fixed_assets.py** - Fixed asset tracking
30. **franchisees.py** - Franchisee network management
31. **grn.py** - Goods Receipt Notes processing
32. **gst_filing.py** - GST return filing (GSTR-1, 3B, 2A)
33. **hr.py** - HR, payroll, attendance, leave
34. **insights.py** - AI-powered business insights
35. **installations.py** - Installation management
36. **inventory.py** - Stock management and movements
37. **leads.py** - Lead management and scoring
38. **manifests.py** - Transporter manifest generation
39. **marketplaces.py** - Marketplace API integrations
40. **notifications.py** - In-app notifications
41. **order_tracking.py** - Public order tracking
42. **orders.py** - Order creation and management
43. **partners.py** - Community partners (Meesho-style)
44. **payments.py** - Payment processing
45. **permissions.py** - Permission management
46. **picklists.py** - Warehouse picking lists
47. **portal.py** - Customer portal operations
48. **products.py** - Product catalog CRUD
49. **promotions.py** - Promotions and loyalty
50. **purchase.py** - Purchase order management
51. **questions.py** - Product Q&A functionality
52. **rate_cards.py** - Shipping rate card management
53. **reports.py** - Financial and operational reports
54. **returns.py** - Return order processing
55. **reviews.py** - Product reviews and ratings
56. **roles.py** - Role-based access control
57. **sales_returns.py** - Sales returns to vendors (SRN)
58. **serialization.py** - Barcode and serial tracking
59. **service_requests.py** - Service ticket management
60. **serviceability.py** - Pincode serviceability checks
61. **shipments.py** - Shipment tracking and management
62. **shipping.py** - Shiprocket integration
63. **snop.py** - Sales & Operations Planning
64. **stock_adjustments.py** - Inventory adjustments
65. **storefront.py** - Public storefront APIs
66. **tds.py** - TDS certificate generation
67. **technicians.py** - Technician assignment and scheduling
68. **transfers.py** - Inter-warehouse stock transfers
69. **transporters.py** - Carrier/transporter management
70. **uploads.py** - File upload handling
71. **users.py** - User management
72. **vendor_invoices.py** - Vendor invoice processing
73. **vendor_payments.py** - Payment to vendors
74. **vendor_proformas.py** - Vendor quotations/proformas
75. **vendors.py** - Vendor master management
76. **warehouses.py** - Warehouse configuration
77. **wms.py** - Warehouse zones, bins, putaway rules

---

## FRONTEND DASHBOARD STRUCTURE

### Location: `frontend/src/app/dashboard/`

---

## SECTION 1: DASHBOARD (HOME)

**Route:** `/dashboard`

**Features:**
- Overview KPIs and metrics
- Key performance indicators
- Quick action buttons
- Recent activity feed
- Chart widgets

**Related APIs:**
- `dashboard_charts.py`

**Database Tables:**
- Aggregates from multiple tables

---

## SECTION 2: INTELLIGENCE (AI HUB)

**Route:** `/dashboard/ai`

**Sub-sections:**

### 2.1 AI Insights
**Route:** `/dashboard/insights`
**Features:**
- AI-powered business insights
- Predictive analytics
- Smart recommendations

### 2.2 Reorder Suggestions
**Route:** `/dashboard/insights/reorder`
**Features:**
- ML-based reorder point suggestions
- Stock level predictions
- Automated purchase recommendations

### 2.3 Churn Risk Analysis
**Route:** `/dashboard/insights/churn-risk`
**Features:**
- Customer churn prediction
- Risk scoring
- Retention strategies

### 2.4 Slow-Moving Stock Detection
**Route:** `/dashboard/insights/slow-moving`
**Features:**
- Identify slow-moving inventory
- Aging analysis
- Clearance recommendations

**Related APIs:**
- `ai.py` - AI analytics
- `insights.py` - Business insights

**Database Tables:**
- `demand_forecasts`
- `inventory_optimizations`
- Various analytics tables

---

## SECTION 3: SALES / ORDERS

**Route:** `/dashboard/orders`

**Sub-sections:**

### 3.1 Orders (Main)
**Route:** `/dashboard/orders`
**Features:**
- Order list with filters
- Status tracking
- Multi-channel order view
- Order search and export

### 3.2 Create New Order
**Route:** `/dashboard/orders/new`
**Features:**
- Order creation form
- Customer selection
- Product selection
- Pricing and discounts
- Payment and shipping details

### 3.3 Order Details
**Route:** `/dashboard/orders/[id]`
**Features:**
- Complete order information
- Status timeline
- Edit order details
- Print invoice
- Shipment tracking
- Return initiation

### 3.4 Order Allocation
**Route:** `/dashboard/orders/allocation`
**Features:**
- Order-to-warehouse allocation
- Allocation rules management
- Manual allocation
- Allocation logs

### 3.5 Picklists
**Route:** `/dashboard/orders/picklists`
**Features:**
- Generate picking lists
- Picklist status tracking
- Warehouse assignment
- Print picklists

**Related APIs:**
- `orders.py` - Order CRUD
- `returns.py` - Return processing
- `allocations.py` (within orders.py)
- `picklists.py` - Picklist generation

**Database Tables:**
- `orders`
- `order_items`
- `order_status_history`
- `allocation_rules`
- `allocation_logs`
- `picklists`
- `picklist_items`

---

## SECTION 4: CHANNELS (MULTI-CHANNEL COMMERCE)

**Route:** `/dashboard/channels`

**Sub-sections:**

### 4.1 Channel Management
**Route:** `/dashboard/channels`
**Features:**
- Sales channel list (D2C, B2B, Marketplace)
- Channel configuration
- Enable/disable channels

### 4.2 Channel Pricing
**Route:** `/dashboard/channels/pricing`
**Features:**
- Channel-specific pricing rules
- Bulk price updates
- Pricing tiers per channel

### 4.3 Channel Inventory
**Route:** `/dashboard/channels/inventory`
**Features:**
- Channel inventory allocation
- Stock sync across channels
- Inventory reservations

### 4.4 Channel Orders
**Route:** `/dashboard/channels/orders`
**Features:**
- View orders by channel
- Channel order sync
- Order import from marketplaces

### 4.5 Marketplace Integration
**Route:** `/dashboard/channels/marketplaces`
**Features:**
- Amazon/Flipkart integration
- Marketplace API configuration
- Order sync settings
- Product listing sync

### 4.6 Channel Reports
**Route:** `/dashboard/channels/reports`
**Features:**
- Channel-wise P&L
- Channel performance metrics
- Commission tracking

**Related APIs:**
- `channels.py` - Channel management
- `marketplaces.py` - Marketplace integrations
- `channel_reports.py` - Channel analytics

**Database Tables:**
- `sales_channels`
- `channel_pricing`
- `channel_inventory`
- `channel_orders`
- `channel_commissions`

---

## SECTION 5: DISTRIBUTION

**Route:** `/dashboard/distribution`

**Sub-sections:**

### 5.1 Dealers
**Route:** `/dashboard/distribution/dealers`
**Features:**
- Dealer master list
- Dealer registration
- Credit limit management
- Dealer ledger
- Dealer performance tracking

### 5.2 Franchisees
**Route:** `/dashboard/distribution/franchisees`
**Features:**
- Franchisee network management
- Contract management
- Territory assignment
- Support tickets

### 5.3 Pricing Tiers
**Route:** `/dashboard/distribution/pricing-tiers`
**Features:**
- Dealer tier pricing
- Volume-based discounts
- Pricing schemes

### 5.4 Franchisee Serviceability
**Route:** `/dashboard/distribution/franchisee-serviceability`
**Features:**
- Territory serviceability matrix
- Pincode mapping to franchisees

**Related APIs:**
- `dealers.py` - Dealer management
- `franchisees.py` - Franchisee operations

**Database Tables:**
- `dealers`
- `dealer_pricing`
- `dealer_tier_pricing`
- `dealer_credit_ledgers`
- `dealer_targets`
- `dealer_schemes`
- `franchisees`
- `franchisee_contracts`
- `franchisee_territories`
- `franchisee_support_tickets`

---

## SECTION 6: PARTNERS (COMMUNITY PARTNERS - MEESHO STYLE)

**Route:** `/dashboard/partners`

**Sub-sections:**

### 6.1 Partner List
**Route:** `/dashboard/partners/list`
**Features:**
- Community partner directory
- Partner status management
- KYC verification

### 6.2 Partner Details
**Route:** `/dashboard/partners/[id]`
**Features:**
- Partner profile
- Performance metrics
- Order history

### 6.3 Partner Orders
**Route:** `/dashboard/partners/orders`
**Features:**
- Orders from partners
- Order tracking
- Partner order management

### 6.4 Partner Tiers
**Route:** `/dashboard/partners/tiers`
**Features:**
- Partner tier management
- Tier benefits
- Upgrade criteria

### 6.5 Commissions
**Route:** `/dashboard/partners/commissions`
**Features:**
- Commission plan management
- Commission calculation
- Earnings tracking

### 6.6 Payouts
**Route:** `/dashboard/partners/payouts`
**Features:**
- Payout processing
- Payment history
- Bank account management

**Related APIs:**
- `partners.py` - Community partner operations
- `commissions.py` - Commission management

**Database Tables:**
- `community_partners`
- `partner_commissions`
- `commission_plans`
- `commission_transactions`
- `commission_payouts`

---

## SECTION 7: PROCUREMENT (PURCHASE-TO-PAY)

**Route:** `/dashboard/procurement`

**Sub-sections:**

### 7.1 Vendors
**Route:** `/dashboard/procurement/vendors`
**Features:**
- Vendor master list
- Vendor registration
- Contact management
- Vendor ledger
- Vendor performance

### 7.2 Purchase Requisitions
**Route:** `/dashboard/procurement/requisitions`
**Features:**
- Create requisitions
- Requisition approval workflow
- Convert to PO

### 7.3 Purchase Orders
**Route:** `/dashboard/procurement/purchase-orders`
**Features:**
- Create PO
- PO approval
- PO tracking
- PO amendments
- Print PO

### 7.4 Goods Receipt Notes (GRN)
**Route:** `/dashboard/procurement/grn`
**Features:**
- GRN creation against PO
- Quality check recording
- Acceptance/rejection
- Serialization on GRN
- Stock updates

### 7.5 Vendor Proformas/Quotations
**Route:** `/dashboard/procurement/vendor-proformas`
**Features:**
- Vendor quotation management
- Quotation comparison
- Convert to PO

### 7.6 Vendor Invoices
**Route:** `/dashboard/procurement/vendor-invoices`
**Features:**
- Vendor invoice entry
- 3-way matching (PO-GRN-Invoice)
- Invoice approval
- TDS calculation

### 7.7 Sales Returns (to Vendors)
**Route:** `/dashboard/procurement/sales-returns`
**Features:**
- Create SRN (Sales Return Note)
- Return to supplier
- Credit note tracking

### 7.8 3-Way Match
**Route:** `/dashboard/procurement/three-way-match`
**Features:**
- PO vs GRN vs Invoice matching
- Variance analysis
- Exception handling

**Related APIs:**
- `vendors.py` - Vendor management
- `purchase.py` - Purchase orders
- `grn.py` - GRN processing
- `vendor_proformas.py` - Quotations
- `vendor_invoices.py` - Invoice processing
- `sales_returns.py` - Returns to vendors
- `approvals.py` - Approval workflows

**Database Tables:**
- `vendors`
- `vendor_contacts`
- `vendor_ledgers`
- `purchase_requisitions`
- `purchase_orders`
- `goods_receipt_notes`
- `grn_items`
- `vendor_invoices`
- `vendor_proformas`
- `vendor_proforma_items`
- `sales_return_notes`
- `sales_return_items`
- `approval_requests`
- `approval_history`

---

## SECTION 8: INVENTORY MANAGEMENT

**Route:** `/dashboard/inventory`

**Sub-sections:**

### 8.1 Stock Summary
**Route:** `/dashboard/inventory`
**Features:**
- Current stock levels across all warehouses
- Stock valuation
- Low stock alerts
- Stock aging

### 8.2 Stock Items
**Route:** `/dashboard/inventory/stock-items`
**Features:**
- Stock item master
- Serial number tracking
- Barcode management
- Stock item history

### 8.3 Stock Movements
**Route:** `/dashboard/inventory/movements`
**Features:**
- All stock movement logs
- Movement types (IN/OUT/TRANSFER)
- Movement history and audit

### 8.4 Stock Transfers
**Route:** `/dashboard/inventory/transfers`
**Features:**
- Inter-warehouse transfers
- Transfer creation
- Transfer approval
- In-transit tracking

### 8.5 Stock Adjustments
**Route:** `/dashboard/inventory/adjustments`
**Features:**
- Stock adjustment entry
- Adjustment reasons
- Approval workflow
- Variance reporting

### 8.6 Warehouses
**Route:** `/dashboard/inventory/warehouses`
**Features:**
- Warehouse master
- Warehouse configuration
- Serviceability settings

### 8.7 Zones (redirects to WMS)
**Route:** `/dashboard/inventory/zones`
**Features:** (See WMS section)

### 8.8 Bins (redirects to WMS)
**Route:** `/dashboard/inventory/bins`
**Features:** (See WMS section)

**Related APIs:**
- `inventory.py` - Stock management
- `stock_adjustments.py` - Adjustments
- `transfers.py` - Stock transfers
- `warehouses.py` - Warehouse config
- `serialization.py` - Barcode tracking

**Database Tables:**
- `stock_items`
- `inventory_summary`
- `stock_movements`
- `stock_transfers`
- `stock_transfer_items`
- `stock_adjustments`
- `stock_adjustment_items`
- `inventory_audits`
- `warehouses`
- `warehouse_serviceability`
- `serialization_sequences`
- `po_serials`
- `supplier_codes`

---

## SECTION 9: WAREHOUSE MANAGEMENT SYSTEM (WMS)

**Route:** `/dashboard/wms`

**Sub-sections:**

### 9.1 Zones
**Route:** `/dashboard/wms/zones`
**Features:**
- Warehouse zone management
- Zone types (Racks, Shelves, etc.)
- Zone capacity
- Zone status

### 9.2 Bins
**Route:** `/dashboard/wms/bins`
**Features:**
- Bin location master
- Bin capacity
- Bin occupancy
- Bin status (active/inactive)

### 9.3 Bin Enquiry
**Route:** `/dashboard/wms/bin-enquiry`
**Features:**
- Search stock by bin
- Find which bin contains specific item
- Bin occupancy report

### 9.4 Putaway Rules
**Route:** `/dashboard/wms/putaway-rules`
**Features:**
- Define putaway rules
- Auto-allocation rules for incoming stock
- Zone-based putaway
- Product-specific rules

**Related APIs:**
- `wms.py` - WMS operations
- `picklists.py` - Picking operations

**Database Tables:**
- `warehouse_zones`
- `warehouse_bins`
- `putaway_rules`
- `picklists`
- `picklist_items`

---

## SECTION 10: LOGISTICS & SHIPPING

**Route:** `/dashboard/logistics`

**Sub-sections:**

### 10.1 Shipments
**Route:** `/dashboard/logistics/shipments`
**Features:**
- Create shipments
- Shipment tracking
- AWB number assignment
- Status updates
- Proof of delivery

### 10.2 Manifests
**Route:** `/dashboard/logistics/manifests`
**Features:**
- Generate transporter manifests
- Manifest handover
- Manifest closure

### 10.3 Transporters/Carriers
**Route:** `/dashboard/logistics/transporters`
**Features:**
- Transporter master
- Carrier configuration
- Performance tracking

### 10.4 Rate Cards
**Route:** `/dashboard/logistics/rate-cards`
**Features:**
- D2C rate cards
- B2B rate cards
- FTL (Full Truck Load) pricing
- Weight-slab pricing

### 10.5 Serviceability Matrix
**Route:** `/dashboard/logistics/serviceability`
**Features:**
- Pincode serviceability
- Carrier-wise serviceability
- Delivery timelines (TAT)

### 10.6 Allocation Rules
**Route:** `/dashboard/logistics/allocation-rules`
**Features:**
- Order allocation rule engine
- Rules based on pincode, payment, value
- Priority configuration

### 10.7 Allocation Logs
**Route:** `/dashboard/logistics/allocation-logs`
**Features:**
- Allocation history
- Rule execution logs
- Allocation performance

### 10.8 Shipping Calculator
**Route:** `/dashboard/logistics/calculator`
**Features:**
- Freight cost calculator
- Rate comparison

### 10.9 SLA Dashboard
**Route:** `/dashboard/logistics/sla-dashboard`
**Features:**
- Delivery SLA monitoring
- On-time delivery metrics
- Carrier performance

**Related APIs:**
- `shipments.py` - Shipment management
- `manifests.py` - Manifest generation
- `transporters.py` - Carrier management
- `rate_cards.py` - Rate card management
- `serviceability.py` - Serviceability checks
- `shipping.py` - Shiprocket integration
- `order_tracking.py` - Public tracking

**Database Tables:**
- `shipments`
- `shipment_tracking`
- `manifests`
- `manifest_items`
- `transporters`
- `transporter_serviceability`
- `rate_cards`
- `allocation_rules`
- `allocation_logs`

---

## SECTION 11: PLANNING (S&OP)

**Route:** `/dashboard/snop`

**Sub-sections:**

### 11.1 Demand Forecasts
**Route:** `/dashboard/snop/forecasts`
**Features:**
- ML-based demand forecasting
- Holt-Winters, ensemble methods
- External factors (weather, festivals)
- Forecast accuracy tracking

### 11.2 Supply Plans
**Route:** `/dashboard/snop/supply-plans`
**Features:**
- Supply planning
- Production scheduling
- Procurement planning

### 11.3 Scenario Analysis
**Route:** `/dashboard/snop/scenarios`
**Features:**
- What-if scenario planning
- Scenario comparison
- Risk analysis

### 11.4 Inventory Optimization
**Route:** `/dashboard/snop/inventory-optimization`
**Features:**
- Optimal inventory levels
- Reorder point suggestions
- Safety stock calculation

**Related APIs:**
- `snop.py` - S&OP operations
- `ai.py` - ML forecasting

**Database Tables:**
- `demand_forecasts`
- `forecast_adjustments`
- `supply_plans`
- `snop_scenarios`
- `external_factors`
- `inventory_optimizations`

---

## SECTION 12: FINANCE & ACCOUNTING

**Route:** `/dashboard/finance`

**Sub-sections:**

### 12.1 Chart of Accounts
**Route:** `/dashboard/finance/chart-of-accounts`
**Features:**
- Account hierarchy
- Account creation
- Account types (Asset, Liability, Income, Expense)

### 12.2 Journal Entries
**Route:** `/dashboard/finance/journal-entries`
**Features:**
- Manual journal entry
- Double-entry bookkeeping
- Approval workflow

### 12.3 General Ledger
**Route:** `/dashboard/finance/general-ledger`
**Features:**
- GL posting
- Account-wise ledger
- Period-wise view

### 12.4 Auto Journal
**Route:** `/dashboard/finance/auto-journal`
**Features:**
- Automatic journal entry generation
- Order-to-journal automation
- Invoice-to-journal automation

### 12.5 Cost Centers
**Route:** `/dashboard/finance/cost-centers`
**Features:**
- Cost center master
- Cost allocation
- Department-wise costing

### 12.6 Financial Periods
**Route:** `/dashboard/finance/periods`
**Features:**
- Accounting period management
- Period opening/closing
- Year-end closing

### 12.7 Bank Reconciliation
**Route:** `/dashboard/finance/bank-reconciliation`
**Features:**
- Bank statement upload
- ML-powered auto-matching
- Manual reconciliation
- Variance tracking

### 12.8 Vendor Payments
**Route:** `/dashboard/finance/vendor-payments`
**Features:**
- Payment to vendors
- Payment approval
- TDS deduction
- Payment reconciliation

### 12.9 GST Filing
**Route:** `/dashboard/finance/gst-filing`
**Features:**
- GSTR-1 preparation
- GSTR-3B filing
- GSTR-2A reconciliation

### 12.10 GSTR-1
**Route:** `/dashboard/finance/gstr1`
**Features:**
- Outward supplies reporting
- B2B, B2C classification
- GSTR-1 JSON generation

### 12.11 GSTR-3B
**Route:** `/dashboard/finance/gstr3b`
**Features:**
- Summary return
- Tax liability calculation
- ITC claims

### 12.12 GSTR-2A
**Route:** `/dashboard/finance/gstr2a`
**Features:**
- Inward supply data
- Vendor invoice reconciliation

### 12.13 ITC (Input Tax Credit)
**Route:** `/dashboard/finance/itc`
**Features:**
- ITC ledger
- ITC matching
- ITC reversal

### 12.14 HSN Summary
**Route:** `/dashboard/finance/hsn-summary`
**Features:**
- HSN-wise sales summary
- GST reporting

### 12.15 TDS Management
**Route:** `/dashboard/finance/tds`
**Features:**
- TDS deduction tracking
- Form 16A certificate generation
- TDS payment

### 12.16 Fixed Assets
**Route:** `/dashboard/finance/fixed-assets`
**Features:**
- Asset register
- Depreciation calculation
- Asset disposal

**Related APIs:**
- `accounting.py` - Core accounting
- `banking.py` - Bank reconciliation
- `auto_journal.py` - Auto JE generation
- `gst_filing.py` - GST operations
- `tds.py` - TDS management
- `fixed_assets.py` - Asset tracking
- `vendor_payments.py` - Payment processing

**Database Tables:**
- `chart_of_accounts`
- `general_ledgers`
- `journal_entries`
- `journal_entry_lines`
- `financial_periods`
- `cost_centers`
- `bank_reconciliation`
- `banking_transactions`
- `auto_journal_entries`
- `tds_deductions`
- `tds_rates`
- `form_16a_certificates`
- `itc_ledger`
- `fixed_assets`
- `asset_depreciation`

---

## SECTION 13: BILLING & INVOICING

**Route:** `/dashboard/billing`

**Sub-sections:**

### 13.1 Tax Invoices
**Route:** `/dashboard/billing/invoices`
**Features:**
- Invoice generation
- E-invoice (IRN generation via NIC)
- GST calculation
- Invoice printing

### 13.2 Credit Notes
**Route:** `/dashboard/billing/credit-notes`
**Features:**
- Credit note creation
- Return-based credit notes
- GST adjustments

### 13.3 E-way Bills
**Route:** `/dashboard/billing/eway-bills`
**Features:**
- E-way bill generation
- Auto-generation for shipments > ₹50,000
- E-way bill tracking

### 13.4 Payment Receipts
**Route:** `/dashboard/billing/receipts`
**Features:**
- Payment receipt entry
- Receipt against invoice
- Payment reconciliation

**Related APIs:**
- `billing.py` - Invoicing and e-way bills
- `payments.py` - Payment processing

**Database Tables:**
- `tax_invoices`
- `invoice_items`
- `e_way_bills`
- `credit_debit_notes`
- `payment_receipts`
- `payments`

---

## SECTION 14: REPORTS

**Route:** `/dashboard/reports`

**Sub-sections:**

### 14.1 Profit & Loss
**Route:** `/dashboard/reports/profit-loss`
**Features:**
- P&L statement
- Period comparison
- Drill-down by account

### 14.2 Balance Sheet
**Route:** `/dashboard/reports/balance-sheet`
**Features:**
- Balance sheet
- Asset/Liability breakdown
- Net worth calculation

### 14.3 Trial Balance
**Route:** `/dashboard/reports/trial-balance`
**Features:**
- Trial balance report
- Debit/Credit totals
- Period-wise view

### 14.4 Channel P&L
**Route:** `/dashboard/reports/channel-pl`
**Features:**
- Channel-wise profit & loss
- Commission deductions
- Net profitability

### 14.5 Channel Balance Sheet
**Route:** `/dashboard/reports/channel-balance-sheet`
**Features:**
- Channel-wise balance sheet
- Outstanding receivables
- Inventory by channel

**Related APIs:**
- `reports.py` - Financial reporting
- `channel_reports.py` - Channel analytics

**Database Tables:**
- Aggregates from accounting tables

---

## SECTION 15: SERVICE MANAGEMENT

**Route:** `/dashboard/service`

**Sub-sections:**

### 15.1 Service Requests
**Route:** `/dashboard/service/requests`
**Features:**
- Create service tickets
- Ticket status tracking
- SLA monitoring
- Auto-assignment to technicians

### 15.2 Technicians
**Route:** `/dashboard/service/technicians`
**Features:**
- Technician master
- Skill management
- Availability calendar
- Performance tracking

### 15.3 Installations
**Route:** `/dashboard/service/installations`
**Features:**
- Installation scheduling
- Installation tracking
- Installation certificate
- Warranty activation

### 15.4 AMC (Annual Maintenance Contracts)
**Route:** `/dashboard/service/amc`
**Features:**
- AMC plan management
- AMC subscription
- Renewal tracking
- Service call entitlements

### 15.5 Warranty Claims
**Route:** `/dashboard/service/warranty-claims`
**Features:**
- Warranty claim creation
- Claim approval workflow
- Parts replacement tracking
- Claim settlement

**Related APIs:**
- `service_requests.py` - Service ticket management
- `technicians.py` - Technician operations
- `installations.py` - Installation tracking
- `amc.py` - AMC management

**Database Tables:**
- `service_requests`
- `technicians`
- `installations`
- `amc_contracts`
- `amc_plans`
- `warranty_claims`

---

## SECTION 16: CRM (CUSTOMER RELATIONSHIP MANAGEMENT)

**Route:** `/dashboard/crm`

**Sub-sections:**

### 16.1 Customers
**Route:** `/dashboard/crm/customers`
**Features:**
- Customer master list
- Customer registration
- Address management
- Customer preferences

### 16.2 Customer 360
**Route:** `/dashboard/crm/customer-360`
**Features:**
- 360-degree customer view
- Order history
- Service history
- Communication logs
- Lifetime value

### 16.3 Leads
**Route:** `/dashboard/crm/leads`
**Features:**
- Lead capture
- Lead scoring
- Lead assignment
- Lead nurturing
- Lead conversion

### 16.4 Call Center
**Route:** `/dashboard/crm/call-center`
**Features:**
- Call logging
- Call disposition
- Callback scheduling
- Call recording management
- Agent performance

### 16.5 Escalations
**Route:** `/dashboard/crm/escalations`
**Features:**
- Issue escalation
- Escalation matrix
- SLA tracking
- Escalation resolution

**Related APIs:**
- `customers.py` - Customer management
- `leads.py` - Lead operations
- `call_center.py` - Call center CRM
- `escalations.py` - Escalation handling

**Database Tables:**
- `customers`
- `customer_addresses`
- `leads`
- `lead_activities`
- `calls`
- `call_dispositions`
- `escalations`
- `escalation_histories`

---

## SECTION 17: MARKETING

**Route:** `/dashboard/marketing`

**Sub-sections:**

### 17.1 Campaigns
**Route:** `/dashboard/marketing/campaigns`
**Features:**
- Campaign creation
- Email/SMS campaigns
- Campaign analytics
- ROI tracking

### 17.2 Promotions
**Route:** `/dashboard/marketing/promotions`
**Features:**
- Discount promotions
- Coupon management
- Bundle offers
- Loyalty programs

### 17.3 Commissions
**Route:** `/dashboard/marketing/commissions`
**Features:**
- Affiliate commission plans
- Commission calculation
- Payout tracking

**Related APIs:**
- `campaigns.py` - Campaign management
- `promotions.py` - Promotion engine
- `coupons.py` - Coupon codes
- `commissions.py` - Commission tracking

**Database Tables:**
- `campaigns`
- `campaign_recipients`
- `promotions`
- `coupons`
- `commission_plans`
- `commission_transactions`

---

## SECTION 18: HUMAN RESOURCES (HRMS)

**Route:** `/dashboard/hr`

**Sub-sections:**

### 18.1 Employees
**Route:** `/dashboard/hr/employees`
**Features:**
- Employee master
- Employee onboarding
- Personal details
- Bank account info

### 18.2 Departments
**Route:** `/dashboard/hr/departments`
**Features:**
- Department structure
- Department hierarchy
- Department heads

### 18.3 Attendance
**Route:** `/dashboard/hr/attendance`
**Features:**
- Daily attendance marking
- Attendance reports
- Shift management
- Overtime tracking

### 18.4 Leave Management
**Route:** `/dashboard/hr/leaves`
**Features:**
- Leave request
- Leave approval workflow
- Leave balance
- Leave policies

### 18.5 Payroll
**Route:** `/dashboard/hr/payroll`
**Features:**
- Salary structure
- Payroll processing
- Payslip generation
- Statutory deductions (PF, ESI)

### 18.6 Performance
**Route:** `/dashboard/hr/performance`
**Features:**
- Performance reviews
- Goal setting
- Appraisal tracking

### 18.7 HR Reports
**Route:** `/dashboard/hr/reports`
**Features:**
- Headcount reports
- Attrition reports
- Payroll reports

**Related APIs:**
- `hr.py` - All HR operations (employees, attendance, payroll, leave)

**Database Tables:**
- `employees`
- `departments`
- `salary_structures`
- `attendance`
- `leave_balances`
- `leave_requests`
- `payroll`
- `payslips`

---

## SECTION 19: CATALOG MANAGEMENT

**Route:** `/dashboard/catalog`

**Sub-sections:**

### 19.1 Products
**Route:** `/dashboard/catalog`
**Features:**
- Product list
- Product search and filters

### 19.2 Create Product
**Route:** `/dashboard/catalog/new`
**Features:**
- Product creation form
- Product variants
- Specifications
- Images upload
- Pricing

### 19.3 Edit Product
**Route:** `/dashboard/catalog/[id]`
**Features:**
- Edit product details
- Manage variants
- Update pricing
- Image management
- Inventory levels

### 19.4 Categories
**Route:** `/dashboard/catalog/categories`
**Features:**
- Category hierarchy
- Category creation
- Category attributes

### 19.5 Brands
**Route:** `/dashboard/catalog/brands`
**Features:**
- Brand master
- Brand logos
- Brand description

**Related APIs:**
- `products.py` - Product CRUD
- `categories.py` - Category management
- `brands.py` - Brand management
- `reviews.py` - Product reviews
- `questions.py` - Product Q&A

**Database Tables:**
- `products`
- `categories`
- `brands`
- `product_images`
- `product_specifications`
- `product_variants`
- `product_documents`
- `product_reviews`
- `product_questions`
- `product_answers`
- `product_costs`

---

## SECTION 20: CONTENT MANAGEMENT SYSTEM (CMS)

**Route:** `/dashboard/cms`

**Sub-sections:**

### 20.1 Banners
**Route:** `/dashboard/cms/banners`
**Features:**
- Homepage banner management
- Banner scheduling
- Banner targeting
- Desktop/mobile variants

### 20.2 USPs (Unique Selling Points)
**Route:** `/dashboard/cms/usps`
**Features:**
- USP content management
- Icon selection
- Display order

### 20.3 Testimonials
**Route:** `/dashboard/cms/testimonials`
**Features:**
- Customer testimonials
- Rating display
- Testimonial moderation

### 20.4 Feature Bars
**Route:** `/dashboard/cms/feature-bars`
**Features:**
- Feature bar content
- Announcement bars
- Promotional strips

### 20.5 Mega Menu
**Route:** `/dashboard/cms/mega-menu`
**Features:**
- Navigation menu structure
- Mega menu configuration
- Category display

### 20.6 FAQ Management
**Route:** `/dashboard/cms/faq`
**Features:**
- FAQ content
- Category-wise FAQ
- FAQ ordering

### 20.7 Navigation
**Route:** `/dashboard/cms/navigation`
**Features:**
- Header/footer navigation
- Menu items
- Link management

### 20.8 Pages
**Route:** `/dashboard/cms/pages`
**Features:**
- Dynamic page creation
- Page builder
- Content versioning
- SEO-friendly URLs

### 20.9 SEO Configuration
**Route:** `/dashboard/cms/seo`
**Features:**
- Meta tags management
- Page titles and descriptions
- Schema markup
- Sitemap generation

### 20.10 Announcements
**Route:** `/dashboard/cms/announcements`
**Features:**
- Announcement bar content
- Scheduling
- Display rules

### 20.11 Video Guides
**Route:** `/dashboard/cms/video-guides`
**Features:**
- Product video guides
- Installation videos
- Video library

### 20.12 Partner Content
**Route:** `/dashboard/cms/partner-content`
**Features:**
- Partner portal content
- Partner onboarding content

### 20.13 Contact Settings
**Route:** `/dashboard/cms/contact-settings`
**Features:**
- Contact page configuration
- Support email/phone

### 20.14 CMS Settings
**Route:** `/dashboard/cms/settings`
**Features:**
- Global CMS settings
- Theme configuration

**Related APIs:**
- `cms.py` - All CMS operations

**Database Tables:**
- `cms_banners`
- `cms_pages`
- `cms_page_versions`
- `cms_seo`
- `cms_announcements`
- `cms_testimonials`
- `cms_features`
- `cms_usps`
- `cms_mega_menu`
- `cms_navigation`
- `video_guides`
- `demo_bookings`

---

## SECTION 21: ACCESS CONTROL & SECURITY

**Route:** `/dashboard/access-control`

**Sub-sections:**

### 21.1 Users
**Route:** `/dashboard/access-control/users`
**Features:**
- User management
- User creation
- Role assignment
- User status (active/inactive)

### 21.2 Roles
**Route:** `/dashboard/access-control/roles`
**Features:**
- Role creation
- Role hierarchy
- Permission assignment to roles

### 21.3 Permissions
**Route:** `/dashboard/access-control/permissions`
**Features:**
- Permission management
- Granular permission control
- Module-wise permissions

**Related APIs:**
- `users.py` - User CRUD
- `roles.py` - Role management
- `permissions.py` - Permission control
- `access_control.py` - Access rules

**Database Tables:**
- `users`
- `user_roles`
- `roles`
- `permissions`
- `role_permissions`
- `modules`

---

## SECTION 22: SYSTEM ADMINISTRATION

### 22.1 Approvals
**Route:** `/dashboard/approvals`
**Features:**
- Pending approval queue
- Approval history
- Multi-level approval workflows

### 22.2 Audit Logs
**Route:** `/dashboard/audit-logs`
**Features:**
- System activity logs
- User action tracking
- Change history
- Security audit trail

### 22.3 Notifications
**Route:** `/dashboard/notifications`
**Features:**
- In-app notifications
- Notification center
- Notification preferences

### 22.4 Serialization
**Route:** `/dashboard/serialization`
**Features:**
- Barcode generation settings
- Serial number sequence configuration
- PO serial management
- Supplier code mapping

### 22.5 Settings
**Route:** `/dashboard/settings`
**Features:**
- General system settings
- Company settings
- Integration settings

**Related APIs:**
- `approvals.py` - Approval workflows
- `audit_logs.py` - Audit trail
- `notifications.py` - Notification system
- `serialization.py` - Serial/barcode management
- `company.py` - Company settings
- `credentials.py` - Encrypted credentials

**Database Tables:**
- `approval_requests`
- `approval_history`
- `audit_logs`
- `notifications`
- `notification_preferences`
- `serialization_sequences`
- `company_entities`
- `company_branches`
- `credentials`

---

## D2C STOREFRONT STRUCTURE

### Location: `frontend/src/app/(storefront)/`

### Total Storefront Pages: 39+ Pages

---

## STOREFRONT SECTION 1: PUBLIC PAGES

### 1.1 Homepage
**Route:** `/`
**Features:**
- Hero banners
- Featured products
- USPs
- Testimonials
- Category showcase

### 1.2 Product Catalog
**Route:** `/products`
**Features:**
- Product listing
- Filters (category, brand, price)
- Sort options
- Pagination

### 1.3 Product Detail
**Route:** `/products/[slug]`
**Features:**
- Product images gallery
- Product details
- Specifications
- Reviews
- Q&A
- Add to cart
- Buy now

### 1.4 Product Comparison
**Route:** `/products/compare`
**Features:**
- Side-by-side product comparison
- Specification comparison

### 1.5 Category Pages
**Route:** `/category/[slug]`
**Features:**
- Category-specific browsing
- Category description
- Filters

### 1.6 Shopping Cart
**Route:** `/cart`
**Features:**
- Cart items
- Quantity adjustment
- Apply coupons
- Cart summary
- Proceed to checkout

### 1.7 Checkout
**Route:** `/checkout`
**Features:**
- Address selection
- Shipping method
- Payment options
- Order review
- Place order

### 1.8 Order Success
**Route:** `/order-success`
**Features:**
- Order confirmation
- Order summary
- Payment confirmation
- Track order link

### 1.9 Cart Recovery
**Route:** `/recover-cart`
**Features:**
- Abandoned cart recovery
- Restore cart items

**Related APIs:**
- `storefront.py` - Public storefront APIs
- `products.py` - Product catalog
- `categories.py` - Categories
- `reviews.py` - Reviews
- `questions.py` - Q&A
- `abandoned_cart.py` - Cart recovery

**Database Tables:**
- All product tables
- `abandoned_carts`
- `coupons`

---

## STOREFRONT SECTION 2: CUSTOMER ACCOUNT

### 2.1 Login
**Route:** `/account/login`
**Features:**
- Customer login
- OTP-based login
- Social login

### 2.2 Profile
**Route:** `/account/profile`
**Features:**
- Profile details
- Edit profile
- Change password

### 2.3 Addresses
**Route:** `/account/addresses`
**Features:**
- Saved addresses
- Add new address
- Edit/delete address
- Set default address

### 2.4 Orders
**Route:** `/account/orders`
**Features:**
- Order history
- Order status
- Filter orders

### 2.5 Order Details
**Route:** `/account/orders/[orderNumber]`
**Features:**
- Order details
- Track shipment
- Download invoice
- Initiate return

### 2.6 Order Return
**Route:** `/account/orders/[orderNumber]/return`
**Features:**
- Select items to return
- Return reason
- Refund method

### 2.7 Returns
**Route:** `/account/returns`
**Features:**
- Return history
- Return status tracking

### 2.8 Return Details
**Route:** `/account/returns/[rmaNumber]`
**Features:**
- Return details
- Refund status
- Return shipment tracking

### 2.9 Service Requests
**Route:** `/account/services`
**Features:**
- Service history
- New service request
- Track service status

### 2.10 Wishlist
**Route:** `/account/wishlist`
**Features:**
- Saved products
- Move to cart
- Remove from wishlist

### 2.11 Registered Devices
**Route:** `/account/devices`
**Features:**
- Registered product devices
- Warranty information
- AMC status

### 2.12 AMC Contracts
**Route:** `/account/amc`
**Features:**
- Active AMC contracts
- AMC renewal
- Service call history

**Related APIs:**
- `d2c_auth.py` - Customer authentication
- `portal.py` - Customer portal
- `customers.py` - Customer data
- `orders.py` - Order history
- `returns.py` - Return processing
- `service_requests.py` - Service tickets

**Database Tables:**
- `customers`
- `customer_addresses`
- `customer_otp`
- `orders`
- `returns`
- `wishlist_items`
- `service_requests`
- `amc_contracts`

---

## STOREFRONT SECTION 3: PARTNER PORTAL

### 3.1 Partner Dashboard
**Route:** `/partner`
**Features:**
- Partner dashboard
- Sales summary
- Earnings overview
- Pending payouts

### 3.2 Partner Login
**Route:** `/partner/login`
**Features:**
- Partner authentication

### 3.3 Partner Products
**Route:** `/partner/products`
**Features:**
- Product catalog for partners
- Share product links
- Generate referral links

### 3.4 Partner KYC
**Route:** `/partner/kyc`
**Features:**
- KYC form
- Document upload
- Verification status

### 3.5 Partner Earnings
**Route:** `/partner/earnings`
**Features:**
- Earnings dashboard
- Commission breakdown
- Order-wise earnings

### 3.6 Partner Payouts
**Route:** `/partner/payouts`
**Features:**
- Payout history
- Bank account management
- Request payout

### 3.7 Become a Partner
**Route:** `/become-partner`
**Features:**
- Partner onboarding form
- Tier information
- Benefits overview

**Related APIs:**
- `partners.py` - Partner operations
- `commissions.py` - Commission tracking

**Database Tables:**
- `community_partners`
- `partner_commissions`
- `commission_transactions`
- `commission_payouts`

---

## STOREFRONT SECTION 4: TRACKING & SUPPORT

### 4.1 Track Order
**Route:** `/track/order/[orderNumber]`
**Features:**
- Public order tracking
- Shipment status
- Delivery timeline

### 4.2 Track Shipment (AWB)
**Route:** `/track/[awb]`
**Features:**
- Track by AWB number
- Carrier tracking
- Real-time updates

### 4.3 FAQ
**Route:** `/faq`
**Features:**
- Frequently asked questions
- Category-wise FAQ
- Search FAQ

### 4.4 Contact Us
**Route:** `/contact`
**Features:**
- Contact form
- Support information
- Store locations

### 4.5 Return Policy
**Route:** `/return-policy`
**Features:**
- Return policy details
- Terms and conditions

### 4.6 Product Guides
**Route:** `/guides`
**Features:**
- Installation guides
- User manuals
- Video tutorials

### 4.7 Referral Program
**Route:** `/referral`
**Features:**
- Referral program details
- Referral link generation
- Referral tracking

**Related APIs:**
- `order_tracking.py` - Public tracking
- `cms.py` - Content pages

**Database Tables:**
- Various content tables

---

## STOREFRONT SECTION 5: DYNAMIC PAGES

### 5.1 Generic Slug Pages
**Route:** `/[slug]`
**Features:**
- CMS-driven dynamic pages
- About us, Privacy policy, Terms, etc.
- SEO-friendly URLs

---

## DATABASE SCHEMA SUMMARY

### Total Tables: 200+

**Core Database Groups:**

1. **Access Control** (7 tables): users, roles, permissions, user_roles, role_permissions, modules, audit_logs

2. **Products** (10 tables): products, categories, brands, product_images, product_specifications, product_variants, product_documents, product_reviews, product_questions, product_answers

3. **Orders** (8 tables): orders, order_items, order_status_history, payments, invoices, abandoned_carts, returns, wishlist_items

4. **Inventory** (12 tables): stock_items, inventory_summary, stock_movements, stock_transfers, stock_transfer_items, stock_adjustments, stock_adjustment_items, inventory_audits, warehouse_serviceability, serialization_sequences, po_serials, supplier_codes

5. **Warehouse** (6 tables): warehouses, warehouse_zones, warehouse_bins, picklists, picklist_items, putaway_rules

6. **Procurement** (12 tables): vendors, vendor_contacts, vendor_ledgers, purchase_requisitions, purchase_orders, goods_receipt_notes, grn_items, vendor_invoices, vendor_proformas, vendor_proforma_items, sales_return_notes, sales_return_items

7. **Finance** (25+ tables): chart_of_accounts, general_ledgers, journal_entries, journal_entry_lines, financial_periods, cost_centers, bank_reconciliation, banking_transactions, auto_journal_entries, tds_deductions, tds_rates, form_16a_certificates, itc_ledger, fixed_assets, asset_depreciation, tax_invoices, invoice_items, e_way_bills, credit_debit_notes, payment_receipts

8. **Service** (6 tables): service_requests, technicians, installations, amc_contracts, amc_plans, warranty_claims

9. **Logistics** (12 tables): shipments, shipment_tracking, manifests, manifest_items, transporters, transporter_serviceability, rate_cards, allocation_rules, allocation_logs

10. **CRM** (10 tables): customers, customer_addresses, leads, lead_activities, calls, call_dispositions, escalations, escalation_histories, campaigns, campaign_recipients

11. **Multi-Channel** (8 tables): sales_channels, channel_pricing, channel_inventory, channel_orders, channel_commissions, commission_plans, commission_transactions, commission_payouts

12. **Distribution** (10 tables): dealers, dealer_pricing, dealer_tier_pricing, dealer_credit_ledgers, dealer_targets, dealer_schemes, franchisees, franchisee_contracts, franchisee_territories, franchisee_support_tickets

13. **HR** (8 tables): departments, employees, salary_structures, attendance, leave_balances, leave_requests, payroll, payslips

14. **CMS** (12+ tables): cms_banners, cms_pages, cms_page_versions, cms_seo, cms_announcements, cms_testimonials, cms_features, cms_usps, cms_mega_menu, cms_navigation, video_guides, demo_bookings

15. **Analytics** (6 tables): demand_forecasts, forecast_adjustments, supply_plans, snop_scenarios, external_factors, inventory_optimizations

16. **Supporting** (10+ tables): document_sequences, notifications, notification_preferences, notification_templates, company_entities, company_branches, company_bank_accounts, credentials, approval_requests, approval_history

---

## COMPLETE SECTION SUMMARY

### Dashboard Sections (22 major sections):

1. **Dashboard** - Home/Overview
2. **Intelligence** - AI Hub (4 sub-sections)
3. **Sales/Orders** - Order management (5 sub-sections)
4. **Channels** - Multi-channel commerce (6 sub-sections)
5. **Distribution** - Dealers & franchisees (4 sub-sections)
6. **Partners** - Community partners (6 sub-sections)
7. **Procurement** - P2P (8 sub-sections)
8. **Inventory** - Stock management (8 sub-sections)
9. **WMS** - Warehouse management (4 sub-sections)
10. **Logistics** - Shipping & fulfillment (9 sub-sections)
11. **Planning** - S&OP (4 sub-sections)
12. **Finance** - Accounting (16 sub-sections)
13. **Billing** - Invoicing (4 sub-sections)
14. **Reports** - Financial reports (5 sub-sections)
15. **Service** - After-sales (5 sub-sections)
16. **CRM** - Customer management (5 sub-sections)
17. **Marketing** - Campaigns & promotions (3 sub-sections)
18. **HR** - Human resources (7 sub-sections)
19. **Catalog** - Product management (5 sub-sections)
20. **CMS** - Content management (14 sub-sections)
21. **Access Control** - Users, roles, permissions (3 sub-sections)
22. **Administration** - System admin (5 sub-sections)

### D2C Storefront Sections (5 major sections):

1. **Public Pages** (9 pages)
2. **Customer Account** (12 pages)
3. **Partner Portal** (7 pages)
4. **Tracking & Support** (7 pages)
5. **Dynamic Pages** (CMS-driven)

---

## NOTES FOR MODULARIZATION

Based on this structure, you can now decide how to organize these sections into modules. Consider:

1. **Which sections naturally group together?**
2. **Which sections depend on each other?**
3. **Which sections can standalone?**
4. **Which sections are must-have vs optional?**
5. **How would customers want to buy these features?**

**Example groupings to consider:**
- Core Operations: Orders + Inventory
- Procurement: All procurement sub-sections
- Finance: Finance + Billing + Reports
- Commerce: Channels + D2C Storefront
- Customer Management: CRM + Service
- And so on...

---

This is the COMPLETE, ACTUAL structure of your ERP system as it exists today. Use this to decide your own module organization strategy.
