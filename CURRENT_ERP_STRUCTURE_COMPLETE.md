# Current ERP System - Complete Structure
## ilms.ai - Section-by-Section Breakdown (As-Is)

**Date:** 2026-01-31
**Purpose:** Complete mapping of the existing ERP system structure

---

## PART 1: DASHBOARD SECTIONS (Admin ERP Panel)

---

### 1. DASHBOARD (Home/Overview)
**Location:** `/dashboard`

**Features:**
- KPI cards (revenue, orders, customers, inventory value)
- Sales charts
- Recent orders
- Low stock alerts
- Revenue trends

**Backend APIs:**
- `dashboard_charts.py` - Dashboard data aggregation

**Database Tables:**
- Queries across multiple tables for aggregated data

---

### 2. INTELLIGENCE (AI Hub)
**Location:** `/dashboard/ai`, `/dashboard/insights/*`

#### 2.1 AI Hub (`/dashboard/ai`)
**Features:**
- AI-powered insights dashboard
- Smart recommendations
- Predictive analytics overview

**Backend APIs:**
- `ai.py` - Advanced AI services (forecasting, ML reconciliation)
- `insights.py` - AI-powered insights

#### 2.2 Reorder Suggestions (`/dashboard/insights/reorder`)
**Features:**
- AI-generated reorder point suggestions
- Stock replenishment recommendations
- Lead time analysis

#### 2.3 Churn Risk Analysis (`/dashboard/insights/churn-risk`)
**Features:**
- Customer churn prediction
- Risk scoring
- Retention recommendations

#### 2.4 Slow-Moving Stock (`/dashboard/insights/slow-moving`)
**Features:**
- Identify slow-moving inventory
- Stock aging analysis
- Clearance recommendations

**Database Tables:**
- `demand_forecasts`
- `forecast_adjustments`
- `inventory_optimizations`
- `external_factors`

---

### 3. ORDERS (Order Management)
**Location:** `/dashboard/orders/*`

#### 3.1 All Orders (`/dashboard/orders`)
**Features:**
- Order list with filters (status, date, channel, customer)
- Order search
- Bulk actions
- Status updates
- Order details view

#### 3.2 Create Order (`/dashboard/orders/new`)
**Features:**
- Manual order creation
- Customer selection
- Product selection with variants
- Pricing calculation
- Discount application
- Shipping address
- Payment method

#### 3.3 Order Details (`/dashboard/orders/[id]`)
**Features:**
- Full order view
- Status history timeline
- Items with pricing
- Customer details
- Shipping details
- Payment information
- Actions: Cancel, Refund, Print Invoice

#### 3.4 Order Allocation (`/dashboard/orders/allocation`)
**Features:**
- Allocation rules configuration
- Warehouse priority
- Pincode-based allocation
- Payment method-based allocation
- Order value thresholds

#### 3.5 Picklists (`/dashboard/orders/picklists`)
**Features:**
- Generate picklists for order picking
- Batch picking
- Pick status tracking
- Print picklist
- Mark items as picked

**Backend APIs:**
- `orders.py` - Order CRUD, status management
- `returns.py` - Return order processing
- `picklists.py` - Picklist generation
- `allocations.py` - Allocation rules (custom endpoint or part of orders)

**Database Tables:**
- `orders`
- `order_items`
- `order_status_history`
- `payments`
- `invoices`
- `returns`
- `return_items`
- `picklists`
- `picklist_items`
- `allocation_rules`
- `allocation_logs`

---

### 4. CRM (Customer Relationship Management)
**Location:** `/dashboard/crm/*`

#### 4.1 Customers (`/dashboard/crm/customers`)
**Features:**
- Customer list with search/filters
- Customer profile management
- Contact information
- Address book
- Customer tags/segments
- Credit limit management

#### 4.2 Customer 360 View (`/dashboard/crm/customer-360`)
**Features:**
- Complete customer view
- Order history
- Payment history
- Service requests
- Communication history
- Lifetime value
- Churn risk score

#### 4.3 Leads (`/dashboard/crm/leads`)
**Features:**
- Lead management
- Lead scoring
- Lead status tracking
- Lead assignment to sales reps
- Conversion tracking
- Follow-up reminders

#### 4.4 Call Center (`/dashboard/crm/call-center`)
**Features:**
- Call logging
- Call disposition codes
- Call recordings management
- Callback scheduling
- Agent performance tracking

#### 4.5 Escalations (`/dashboard/crm/escalations`)
**Features:**
- Issue escalation management
- Priority levels
- SLA tracking
- Escalation history
- Resolution tracking
- Auto-escalation rules

**Backend APIs:**
- `customers.py` - Customer management
- `leads.py` - Lead management with scoring
- `call_center.py` - Call center operations
- `escalations.py` - Escalation management
- `campaigns.py` - Marketing campaigns

**Database Tables:**
- `customers`
- `customer_addresses`
- `leads`
- `lead_activities`
- `calls`
- `call_dispositions`
- `escalations`
- `escalation_histories`
- `callback_schedules`

---

### 5. PARTNERS (Community Partners - Meesho-style)
**Location:** `/dashboard/partners/*`

#### 5.1 Partners List (`/dashboard/partners/list`)
**Features:**
- Partner directory
- Partner status (pending, active, suspended)
- KYC status
- Performance metrics

#### 5.2 Partner Details (`/dashboard/partners/[id]`)
**Features:**
- Partner profile
- Business information
- Bank details
- KYC documents
- Performance dashboard

#### 5.3 Partner Tiers (`/dashboard/partners/tiers`)
**Features:**
- Tier management (Bronze, Silver, Gold, Platinum)
- Tier benefits configuration
- Commission rates per tier
- Tier upgrade criteria

#### 5.4 Partner Orders (`/dashboard/partners/orders`)
**Features:**
- Orders placed by partners
- Order tracking
- Commission calculation
- Order status

#### 5.5 Commissions (`/dashboard/partners/commissions`)
**Features:**
- Commission calculation
- Commission tracking per partner
- Commission plans
- Earning history

#### 5.6 Payouts (`/dashboard/partners/payouts`)
**Features:**
- Payout processing
- Payout history
- Payout status
- Bank transfer integration

**Backend APIs:**
- `partners.py` - Community partner management
- `commissions.py` - Commission tracking
- Payment integration for payouts

**Database Tables:**
- `community_partners`
- `partner_tiers`
- `partner_orders`
- `partner_commissions`
- `partner_payouts`
- `partner_kyc_documents`
- `commission_plans`
- `commission_transactions`

---

### 6. PROCUREMENT (Purchase-to-Pay)
**Location:** `/dashboard/procurement/*`

#### 6.1 Vendors (`/dashboard/procurement/vendors`)
**Features:**
- Vendor master data
- Vendor contacts
- Vendor documents
- Credit terms
- Payment terms
- Vendor rating
- Vendor ledger

#### 6.2 Purchase Requisitions (`/dashboard/procurement/requisitions`)
**Features:**
- PR creation
- PR approval workflow
- PR to PO conversion
- PR status tracking

#### 6.3 Purchase Orders (`/dashboard/procurement/purchase-orders`)
**Features:**
- PO creation
- PO approval workflow
- PO amendments
- PO status tracking
- Supplier acknowledgment
- Expected delivery date

#### 6.4 Goods Receipt Note (GRN) (`/dashboard/procurement/grn`)
**Features:**
- GRN creation against PO
- Quality inspection
- Accept/reject items
- Serialization on receipt
- Barcode generation
- Stock update on GRN acceptance

#### 6.5 Vendor Invoices (`/dashboard/procurement/vendor-invoices`)
**Features:**
- Vendor invoice recording
- Invoice matching with PO and GRN
- GST validation
- TDS calculation
- Invoice approval
- Payment scheduling

#### 6.6 Vendor Proformas (`/dashboard/procurement/vendor-proformas`)
**Features:**
- Proforma/quotation management
- Proforma comparison
- Proforma to PO conversion

#### 6.7 Sales Returns to Vendor (`/dashboard/procurement/sales-returns`)
**Features:**
- Return note creation
- Return reason codes
- Credit note from vendor
- Stock adjustment

#### 6.8 Three-Way Matching (`/dashboard/procurement/three-way-match`)
**Features:**
- PO vs GRN vs Invoice matching
- Discrepancy highlighting
- Variance analysis
- Match approval

**Backend APIs:**
- `vendors.py` - Vendor management
- `purchase.py` - Purchase requisition and PO management
- `grn.py` - GRN processing
- `vendor_invoices.py` - Vendor invoice management
- `vendor_proformas.py` - Proforma management
- `sales_returns.py` - Sales return to vendor
- `approvals.py` - Multi-level approval workflows

**Database Tables:**
- `vendors`
- `vendor_contacts`
- `vendor_ledgers`
- `purchase_requisitions`
- `purchase_orders`
- `po_items`
- `goods_receipt_notes`
- `grn_items`
- `vendor_invoices`
- `vendor_invoice_items`
- `vendor_proformas`
- `vendor_proforma_items`
- `sales_return_notes`
- `sales_return_items`
- `approval_requests`
- `approval_history`

---

### 7. INVENTORY (Inventory Management)
**Location:** `/dashboard/inventory/*`

#### 7.1 Stock Summary (`/dashboard/inventory`)
**Features:**
- Real-time stock levels
- Multi-warehouse view
- Stock value
- Available vs allocated stock
- Reorder point alerts
- Stock aging

#### 7.2 Stock Items (`/dashboard/inventory/stock-items`)
**Features:**
- Stock item master
- Item details (SKU, barcode, serial numbers)
- Item location (warehouse, zone, bin)
- Item history
- Item movement tracking

#### 7.3 Stock Movements (`/dashboard/inventory/movements`)
**Features:**
- Movement log (in, out, transfer, adjustment)
- Movement search/filter
- Transaction reference
- Timestamp and user tracking

#### 7.4 Stock Transfers (`/dashboard/inventory/transfers`)
**Features:**
- Inter-warehouse transfer creation
- Transfer approval
- Transfer in-transit tracking
- Transfer receipt
- Transfer status

#### 7.5 Stock Adjustments (`/dashboard/inventory/adjustments`)
**Features:**
- Stock adjustment creation
- Adjustment reasons (damage, theft, found, cycle count)
- Adjustment approval
- Adjustment history
- Variance reports

#### 7.6 Warehouses (`/dashboard/inventory/warehouses`)
**Features:**
- Warehouse master data
- Warehouse address
- Warehouse manager
- Warehouse capacity
- Active/inactive status

**Backend APIs:**
- `inventory.py` - Stock tracking and movements
- `transfers.py` - Inter-warehouse transfers
- `stock_adjustments.py` - Stock adjustments
- `warehouses.py` - Warehouse configuration
- `serialization.py` - Barcode and serial number management

**Database Tables:**
- `stock_items`
- `inventory_summary`
- `stock_movements`
- `stock_transfers`
- `stock_transfer_items`
- `stock_adjustments`
- `stock_adjustment_items`
- `warehouses`
- `serialization_sequences`
- `po_serials`

---

### 8. WAREHOUSE (WMS - Warehouse Management System)
**Location:** `/dashboard/wms/*`

#### 8.1 Zones (`/dashboard/wms/zones`, `/dashboard/inventory/zones`)
**Features:**
- Warehouse zone management (Racks, Shelves, etc.)
- Zone naming and configuration
- Zone capacity
- Zone type (storage, picking, packing, staging)

#### 8.2 Bins (`/dashboard/wms/bins`, `/dashboard/inventory/bins`)
**Features:**
- Bin location management
- Bin naming (A-01-01)
- Bin capacity
- Bin occupancy status

#### 8.3 Bin Enquiry (`/dashboard/wms/bin-enquiry`)
**Features:**
- Search stock by bin location
- Find which bin contains a product
- Bin utilization report

#### 8.4 Putaway Rules (`/dashboard/wms/putaway-rules`)
**Features:**
- Configure putaway logic
- Zone assignment rules
- Bin allocation rules
- FIFO/LIFO strategies

**Backend APIs:**
- `wms.py` - WMS operations (zones, bins, putaway)

**Database Tables:**
- `warehouse_zones`
- `warehouse_bins`
- `putaway_rules`
- `bin_allocation_logs`

---

### 9. LOGISTICS (Shipping & Transportation)
**Location:** `/dashboard/logistics/*`

#### 9.1 Shipments (`/dashboard/logistics/shipments`)
**Features:**
- Shipment creation
- Shipment tracking
- AWB (Airway Bill) assignment
- Carrier assignment
- Shipment status updates
- Tracking link generation
- POD (Proof of Delivery)

#### 9.2 Manifests (`/dashboard/logistics/manifests`)
**Features:**
- Manifest creation for carrier handover
- Manifest items (batch of shipments)
- Manifest printing
- Handover confirmation

#### 9.3 Carriers/Transporters (`/dashboard/logistics/carriers`, `/dashboard/logistics/transporters`)
**Features:**
- Carrier master data
- Carrier contact details
- Carrier performance tracking
- Integration settings (Shiprocket, Delhivery, etc.)

#### 9.4 Rate Cards (`/dashboard/logistics/rate-cards`)
**Features:**
- Shipping rate configuration
- D2C rate cards
- B2B rate cards
- FTL (Full Truck Load) rates
- Weight slab-based pricing
- Zone-based pricing

#### 9.5 Serviceability (`/dashboard/logistics/serviceability`)
**Features:**
- Pincode serviceability matrix
- Carrier serviceability
- TAT (Turn Around Time) by pincode
- Cash on Delivery (COD) availability

#### 9.6 Allocation Rules (`/dashboard/logistics/allocation-rules`)
**Features:**
- Order allocation to warehouse rules
- Pincode-based allocation
- Payment method-based allocation
- Order value-based allocation

#### 9.7 Allocation Logs (`/dashboard/logistics/allocation-logs`)
**Features:**
- View allocation decisions
- Allocation performance tracking
- Rule effectiveness

#### 9.8 SLA Dashboard (`/dashboard/logistics/sla-dashboard`)
**Features:**
- Shipping SLA monitoring
- On-time delivery %
- Delayed shipments
- Carrier performance

#### 9.9 Shipping Calculator (`/dashboard/logistics/calculator`)
**Features:**
- Calculate shipping cost
- Compare carrier rates
- TAT estimation

**Backend APIs:**
- `shipments.py` - Shipment management
- `manifests.py` - Manifest generation
- `transporters.py` - Carrier management
- `rate_cards.py` - Rate card management
- `serviceability.py` - Pincode serviceability
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

### 10. S&OP (Sales & Operations Planning)
**Location:** `/dashboard/snop/*`

#### 10.1 Demand Forecasts (`/dashboard/snop/forecasts`)
**Features:**
- ML-based demand forecasting
- Forecast by product/category
- Forecast adjustments (manual overrides)
- External factors (weather, promotions, festivals)
- Forecast accuracy tracking

#### 10.2 Supply Plans (`/dashboard/snop/supply-plans`)
**Features:**
- Supply planning based on forecasts
- Procurement recommendations
- Production scheduling
- Lead time consideration

#### 10.3 Scenarios (`/dashboard/snop/scenarios`)
**Features:**
- What-if scenario analysis
- Impact simulation
- Scenario comparison

#### 10.4 Inventory Optimization (`/dashboard/snop/inventory-optimization`)
**Features:**
- Optimal stock level calculation
- Safety stock recommendations
- Reorder point optimization

**Backend APIs:**
- `snop.py` - S&OP planning operations
- `ai.py` - ML forecasting models

**Database Tables:**
- `demand_forecasts`
- `forecast_adjustments`
- `supply_plans`
- `snop_scenarios`
- `external_factors`
- `inventory_optimizations`

---

### 11. FINANCE (Finance & Accounting)
**Location:** `/dashboard/finance/*`

#### 11.1 Chart of Accounts (`/dashboard/finance/chart-of-accounts`)
**Features:**
- Account master (Assets, Liabilities, Income, Expenses)
- Account hierarchy
- Account groups
- Opening balances

#### 11.2 Journal Entries (`/dashboard/finance/journal-entries`)
**Features:**
- Manual journal entry creation
- Debit/credit lines
- Cost center allocation
- Narration
- Attachment support
- Approval workflow

#### 11.3 General Ledger (`/dashboard/finance/general-ledger`)
**Features:**
- GL view by account
- Transaction drill-down
- Period-wise balance
- Running balance

#### 11.4 Auto Journal (`/dashboard/finance/auto-journal`)
**Features:**
- Automatic journal entry generation rules
- Order to GL posting
- Purchase to GL posting
- Payment to GL posting

#### 11.5 Cost Centers (`/dashboard/finance/cost-centers`)
**Features:**
- Cost center master
- Cost center hierarchy
- Cost center-wise reports

#### 11.6 Financial Periods (`/dashboard/finance/periods`)
**Features:**
- Financial year setup
- Period opening/closing
- Period lock for posting

#### 11.7 Bank Reconciliation (`/dashboard/finance/bank-reconciliation`)
**Features:**
- Bank statement import
- **ML-powered auto-matching** with GL entries
- Manual matching
- Reconciliation report
- Unmatched transactions

#### 11.8 GST Filing (`/dashboard/finance/gst-filing`)
**Features:**
- GST return overview
- Filing status

#### 11.9 GSTR-1 (`/dashboard/finance/gstr1`)
**Features:**
- Outward supplies report
- B2B invoices
- B2C invoices
- Export invoices
- Auto-filing to GST portal

#### 11.10 GSTR-3B (`/dashboard/finance/gstr3b`)
**Features:**
- Summary return
- Tax liability
- ITC available
- Payment details
- Auto-filing

#### 11.11 GSTR-2A (`/dashboard/finance/gstr2a`)
**Features:**
- Inward supplies (auto-populated by GSTN)
- Supplier invoice matching
- ITC reconciliation

#### 11.12 ITC Management (`/dashboard/finance/itc`)
**Features:**
- Input Tax Credit tracking
- ITC claims
- ITC reversal
- GSTR-2A vs 2B matching

#### 11.13 HSN Summary (`/dashboard/finance/hsn-summary`)
**Features:**
- HSN code-wise summary
- Quantity and value
- Tax amount

#### 11.14 TDS (`/dashboard/finance/tds`)
**Features:**
- TDS deduction on vendor payments
- TDS rate master (per section)
- Form 16A generation
- TDS return filing

#### 11.15 Vendor Payments (`/dashboard/finance/vendor-payments`)
**Features:**
- Payment to vendors
- Payment mode (bank transfer, cheque, cash)
- Payment voucher
- TDS deduction
- Payment ledger

#### 11.16 Fixed Assets (`/dashboard/finance/fixed-assets`)
**Features:**
- Asset master
- Asset depreciation
- Asset disposal
- Asset register

**Backend APIs:**
- `accounting.py` - Chart of accounts, journal entries, GL
- `banking.py` - Bank reconciliation with ML
- `auto_journal.py` - Auto journal generation
- `gst_filing.py` - GST filing (GSTR-1, 3B, 2A, ITC)
- `tds.py` - TDS management
- `vendor_payments.py` - Vendor payment processing
- `fixed_assets.py` - Fixed asset management
- `billing.py` - E-invoicing, GST calculation

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
- `form16a_certificates`
- `itc_ledgers`
- `gst_returns`
- `fixed_assets`
- `asset_depreciation`

---

### 12. BILLING (Invoicing & Tax)
**Location:** `/dashboard/billing/*`

#### 12.1 Invoices (`/dashboard/billing/invoices`)
**Features:**
- Tax invoice generation
- E-invoice (IRN generation via NIC portal)
- Invoice template
- GST calculation
- QR code generation
- Invoice PDF download

#### 12.2 Credit Notes (`/dashboard/billing/credit-notes`)
**Features:**
- Credit note for returns
- Credit note against invoice
- GST adjustment

#### 12.3 E-way Bills (`/dashboard/billing/eway-bills`)
**Features:**
- E-way bill generation for goods movement
- Auto-generation for orders > ₹50,000
- Multi-vehicle EWB
- EWB tracking

#### 12.4 Payment Receipts (`/dashboard/billing/receipts`)
**Features:**
- Payment receipt vouchers
- Customer payment recording
- Payment allocation to invoices
- Payment reconciliation

**Backend APIs:**
- `billing.py` - Invoice generation, E-invoice, E-way bill
- `payments.py` - Payment processing

**Database Tables:**
- `tax_invoices`
- `invoice_items`
- `e_way_bills`
- `credit_debit_notes`
- `payment_receipts`

---

### 13. SERVICE (After-Sales Service)
**Location:** `/dashboard/service/*`

#### 13.1 Service Requests (`/dashboard/service/requests`)
**Features:**
- Service ticket creation
- Customer complaint
- Technician assignment
- Service status (open, in-progress, closed)
- SLA tracking
- Parts replacement tracking

#### 13.2 Technicians (`/dashboard/service/technicians`)
**Features:**
- Technician master data
- Skill matrix
- Availability calendar
- Location/territory
- Performance tracking

#### 13.3 Installations (`/dashboard/service/installations`)
**Features:**
- Installation request management
- Installation scheduling
- Technician assignment
- Installation completion
- Customer feedback

#### 13.4 AMC (Annual Maintenance Contract) (`/dashboard/service/amc`)
**Features:**
- AMC plan creation (1 year, 2 years, etc.)
- AMC subscription
- AMC renewal reminders
- Service calls under AMC
- AMC revenue tracking

#### 13.5 Warranty Claims (`/dashboard/service/warranty-claims`)
**Features:**
- Warranty claim logging
- Claim approval
- Parts replacement under warranty
- Claim settlement

**Backend APIs:**
- `service_requests.py` - Service request management
- `technicians.py` - Technician management
- `installations.py` - Installation tracking
- `amc.py` - AMC contract management

**Database Tables:**
- `service_requests`
- `technicians`
- `installations`
- `amc_contracts`
- `amc_plans`
- `warranty_claims`
- `service_parts`

---

### 14. HR (Human Resource Management)
**Location:** `/dashboard/hr/*`

#### 14.1 Employees (`/dashboard/hr/employees`)
**Features:**
- Employee master data
- Personal information
- Employment details
- Salary information
- Document management

#### 14.2 Departments (`/dashboard/hr/departments`)
**Features:**
- Department master
- Department hierarchy
- Department head assignment

#### 14.3 Attendance (`/dashboard/hr/attendance`)
**Features:**
- Daily attendance marking
- Attendance calendar
- Late arrivals
- Early departures
- Attendance reports

#### 14.4 Leaves (`/dashboard/hr/leaves`)
**Features:**
- Leave balance tracking
- Leave request workflow
- Leave approval
- Leave types (casual, sick, earned)
- Leave encashment

#### 14.5 Payroll (`/dashboard/hr/payroll`)
**Features:**
- Monthly payroll processing
- Salary calculation
- Deductions (PF, ESI, TDS)
- Allowances
- Payslip generation
- Bank file for salary transfer

#### 14.6 Performance (`/dashboard/hr/performance`)
**Features:**
- Performance review cycles
- KPI tracking
- Review forms
- 360-degree feedback

#### 14.7 HR Reports (`/dashboard/hr/reports`)
**Features:**
- Headcount reports
- Attendance reports
- Leave reports
- Salary reports

**Backend APIs:**
- `hr.py` - Employee, attendance, payroll, leave management

**Database Tables:**
- `employees`
- `departments`
- `salary_structures`
- `attendance`
- `leave_balances`
- `leave_requests`
- `payroll`
- `payslips`
- `performance_reviews`

---

### 15. CHANNELS (Multi-Channel Commerce)
**Location:** `/dashboard/channels/*`

#### 15.1 Sales Channels (`/dashboard/channels`)
**Features:**
- Channel master (D2C, B2B, Amazon, Flipkart, etc.)
- Channel configuration
- API credentials
- Active/inactive status

#### 15.2 Channel Pricing (`/dashboard/channels/pricing`)
**Features:**
- Channel-specific pricing
- Markup/markdown rules
- Pricing sync to marketplaces

#### 15.3 Channel Inventory (`/dashboard/channels/inventory`)
**Features:**
- Inventory allocation per channel
- Real-time sync to marketplaces
- Channel-wise stock levels

#### 15.4 Marketplace Integration (`/dashboard/channels/marketplaces`)
**Features:**
- Amazon Seller Central integration
- Flipkart integration
- Order sync from marketplaces
- Product listing sync
- Inventory sync

#### 15.5 Channel Orders (`/dashboard/channels/orders`)
**Features:**
- Orders from all channels
- Channel-wise filtering
- Order sync status

#### 15.6 Channel Reports (`/dashboard/channels/reports`)
**Features:**
- Channel-wise sales reports
- Channel P&L
- Channel performance
- Commission tracking

**Backend APIs:**
- `channels.py` - Sales channel management
- `marketplaces.py` - Marketplace API integrations
- `channel_reports.py` - Channel-wise P&L

**Database Tables:**
- `sales_channels`
- `channel_pricing`
- `channel_inventory`
- `channel_orders`
- `channel_commissions`
- `marketplace_listings`

---

### 16. DISTRIBUTION (Dealer/Franchisee Network)
**Location:** `/dashboard/distribution/*`

#### 16.1 Dealers (`/dashboard/distribution/dealers`)
**Features:**
- Dealer master data
- Dealer contact
- Credit limit
- Payment terms
- Dealer territory
- Dealer status

#### 16.2 Pricing Tiers (`/dashboard/distribution/pricing-tiers`)
**Features:**
- Dealer tier management (Silver, Gold, Platinum)
- Tier-based pricing
- Volume-based discounts

#### 16.3 Franchisees (`/dashboard/distribution/franchisees`)
**Features:**
- Franchisee master data
- Franchise agreement
- Territory assignment
- Royalty tracking
- Support ticket management

#### 16.4 Franchisee Serviceability (`/dashboard/distribution/franchisee-serviceability`)
**Features:**
- Pincode assignment to franchisees
- Territory mapping

**Backend APIs:**
- `dealers.py` - Dealer management
- `franchisees.py` - Franchisee network management

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

### 17. MARKETING
**Location:** `/dashboard/marketing/*`

#### 17.1 Campaigns (`/dashboard/marketing/campaigns`)
**Features:**
- Marketing campaign creation
- Campaign type (email, SMS, WhatsApp)
- Target audience selection
- Campaign scheduling
- Campaign performance tracking

#### 17.2 Promotions (`/dashboard/marketing/promotions`)
**Features:**
- Promotion management
- Discount codes/coupons
- Promotion validity
- Usage limits
- Promotion performance

#### 17.3 Commissions (`/dashboard/marketing/commissions`)
**Features:**
- Commission plans for sales reps/partners
- Commission calculation
- Commission tracking

**Backend APIs:**
- `campaigns.py` - Campaign management
- `promotions.py` - Promotions and coupons
- `commissions.py` - Commission tracking
- `coupons.py` - Coupon management

**Database Tables:**
- `campaigns`
- `campaign_recipients`
- `promotions`
- `coupons`
- `coupon_usage`
- `commission_plans`
- `commission_transactions`

---

### 18. CATALOG (Product Management)
**Location:** `/dashboard/catalog/*`

#### 18.1 Products (`/dashboard/catalog`)
**Features:**
- Product master data
- Product name, SKU, description
- Product images
- Product specifications
- Product variants (size, color, etc.)
- Product documents (manuals, certificates)
- Product pricing
- Product status (active, inactive, discontinued)

#### 18.2 Create/Edit Product (`/dashboard/catalog/new`, `/dashboard/catalog/[id]`)
**Features:**
- Product form
- Variant management
- Image upload (multiple images)
- Specification editor
- Pricing configuration
- Inventory settings

#### 18.3 Categories (`/dashboard/catalog/categories`)
**Features:**
- Category hierarchy
- Parent-child relationships
- Category images
- Category SEO

#### 18.4 Brands (`/dashboard/catalog/brands`)
**Features:**
- Brand master
- Brand logo
- Brand description

**Backend APIs:**
- `products.py` - Product CRUD with variants, specs, images
- `categories.py` - Category management
- `brands.py` - Brand management

**Database Tables:**
- `products`
- `product_variants`
- `product_images`
- `product_specifications`
- `product_documents`
- `product_costs`
- `categories`
- `brands`

---

### 19. SERIALIZATION (Barcode Management)
**Location:** `/dashboard/serialization`

**Features:**
- Serialization configuration
- Barcode generation rules
- Serial number tracking
- QR code generation
- Label printing

**Backend APIs:**
- `serialization.py` - Barcode and serial number management

**Database Tables:**
- `serialization_sequences`
- `po_serials`
- `model_code_references`
- `supplier_codes`

---

### 20. CMS (Content Management System)
**Location:** `/dashboard/cms/*`

#### 20.1 Banners (`/dashboard/cms/banners`)
**Features:**
- Homepage banner management
- Banner images
- Banner links
- Banner scheduling (start/end date)
- Desktop/mobile variants

#### 20.2 USPs (`/dashboard/cms/usps`)
**Features:**
- Unique Selling Points
- Icon, title, description

#### 20.3 Testimonials (`/dashboard/cms/testimonials`)
**Features:**
- Customer testimonials
- Ratings
- Customer name, photo

#### 20.4 Feature Bars (`/dashboard/cms/feature-bars`)
**Features:**
- Top announcement bar
- Promotional messages

#### 20.5 Mega Menu (`/dashboard/cms/mega-menu`)
**Features:**
- Navigation menu configuration
- Multi-level menu
- Featured categories

#### 20.6 Navigation (`/dashboard/cms/navigation`)
**Features:**
- Header/footer navigation links
- Link ordering

#### 20.7 Pages (`/dashboard/cms/pages`)
**Features:**
- Static page management
- Page builder
- Version history
- Rich text editor

#### 20.8 FAQ (`/dashboard/cms/faq`)
**Features:**
- FAQ management
- Question-answer pairs
- FAQ categories

#### 20.9 SEO (`/dashboard/cms/seo`)
**Features:**
- Meta titles
- Meta descriptions
- Keywords
- OG tags
- Page-wise SEO

#### 20.10 Announcements (`/dashboard/cms/announcements`)
**Features:**
- Site-wide announcements
- Announcement bar

#### 20.11 Video Guides (`/dashboard/cms/video-guides`)
**Features:**
- Video tutorial management
- YouTube embed links

#### 20.12 Partner Content (`/dashboard/cms/partner-content`)
**Features:**
- Content for partner portal
- Partner help articles

#### 20.13 Contact Settings (`/dashboard/cms/contact-settings`)
**Features:**
- Contact information
- Support email/phone

#### 20.14 CMS Settings (`/dashboard/cms/settings`)
**Features:**
- Global CMS configuration

**Backend APIs:**
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
- `cms_navigation`
- `video_guides`
- `demo_bookings`

---

### 21. REPORTS (Financial Reports)
**Location:** `/dashboard/reports/*`

#### 21.1 Profit & Loss (`/dashboard/reports/profit-loss`)
**Features:**
- P&L statement
- Period comparison
- Revenue and expense breakdown

#### 21.2 Balance Sheet (`/dashboard/reports/balance-sheet`)
**Features:**
- Assets, liabilities, equity
- Current vs non-current
- Ratio analysis

#### 21.3 Trial Balance (`/dashboard/reports/trial-balance`)
**Features:**
- All account balances
- Debit/credit totals

#### 21.4 Channel P&L (`/dashboard/reports/channel-pl`)
**Features:**
- P&L by sales channel
- Channel profitability

#### 21.5 Channel Balance Sheet (`/dashboard/reports/channel-balance-sheet`)
**Features:**
- Balance sheet by channel

**Backend APIs:**
- `reports.py` - Financial and operational reports
- `channel_reports.py` - Channel-wise reports

**Database Tables:**
- Queries from GL, journals, and other tables

---

### 22. ACCESS CONTROL (Security & Permissions)
**Location:** `/dashboard/access-control/*`

#### 22.1 Users (`/dashboard/access-control/users`)
**Features:**
- User management
- User creation
- Email, phone
- Role assignment
- Active/inactive status

#### 22.2 Roles (`/dashboard/access-control/roles`)
**Features:**
- Role management (Admin, Manager, Sales, etc.)
- Role description
- Permission assignment to roles

#### 22.3 Permissions (`/dashboard/access-control/permissions`)
**Features:**
- Granular permission management
- Module-level permissions
- Action-level permissions (view, create, edit, delete)

**Backend APIs:**
- `auth.py` - JWT authentication, login, refresh tokens
- `users.py` - User management
- `roles.py` - Role management
- `permissions.py` - Permission management
- `access_control.py` - Access control rules

**Database Tables:**
- `users`
- `user_roles`
- `roles`
- `permissions`
- `role_permissions`
- `modules`

---

### 23. APPROVALS (Workflow Management)
**Location:** `/dashboard/approvals`

**Features:**
- Approval requests list
- Pending approvals
- Approval history
- Multi-level approval workflows
- Approval/rejection actions

**Backend APIs:**
- `approvals.py` - Multi-level approval workflows

**Database Tables:**
- `approval_requests`
- `approval_history`
- `approval_workflows`

---

### 24. NOTIFICATIONS
**Location:** `/dashboard/notifications`

**Features:**
- In-app notifications
- Notification types (info, warning, error, success)
- Read/unread status
- Notification preferences

**Backend APIs:**
- `notifications.py` - Notification management

**Database Tables:**
- `notifications`
- `notification_preferences`
- `notification_templates`

---

### 25. AUDIT LOGS
**Location:** `/dashboard/audit-logs`

**Features:**
- System audit trail
- User action logging
- Entity changes
- Before/after values
- Timestamp and user tracking

**Backend APIs:**
- `audit_logs.py` - Audit trail

**Database Tables:**
- `audit_logs`

---

### 26. SETTINGS
**Location:** `/dashboard/settings/*`

#### 26.1 Company Settings (`/dashboard/settings`)
**Features:**
- Company information
- Logo upload
- GST details
- PAN details
- Bank accounts

#### 26.2 Credentials (`/dashboard/settings/credentials` - possibly)
**Features:**
- Encrypted credential storage
- API keys
- Integration credentials

**Backend APIs:**
- `company.py` - Company/business entity setup
- `credentials.py` - Encrypted credential management

**Database Tables:**
- `company_entities`
- `company_branches`
- `company_bank_accounts`
- `encrypted_credentials`

---

## PART 2: STOREFRONT (D2C E-commerce Website)

**Base URL:** Customer-facing website (e.g., www.aquapurite.com)

---

### 1. PUBLIC PAGES (No Login Required)

#### 1.1 Homepage (`/`)
**Features:**
- Hero banners (carousel)
- Featured products
- Categories showcase
- USPs
- Testimonials
- Newsletter signup

#### 1.2 Products Listing (`/products`)
**Features:**
- Product grid/list view
- Filters (category, price, brand, rating)
- Sort (price, popularity, newest)
- Pagination
- Quick view

#### 1.3 Product Detail Page (`/products/[slug]`)
**Features:**
- Product images (gallery with zoom)
- Product name, SKU
- Price (with strikethrough for discounts)
- Product description
- Specifications
- Add to cart
- Add to wishlist
- Stock availability
- Delivery pincode check
- Product reviews
- Product Q&A
- Related products

#### 1.4 Product Comparison (`/products/compare`)
**Features:**
- Side-by-side product comparison
- Specification comparison

#### 1.5 Category Pages (`/category/[slug]`)
**Features:**
- Category-specific product listing
- Category banner
- Category description

#### 1.6 Shopping Cart (`/cart`)
**Features:**
- Cart items list
- Quantity update
- Remove item
- Apply coupon
- Price summary (subtotal, discount, tax, shipping, total)
- Proceed to checkout

#### 1.7 Checkout (`/checkout`)
**Features:**
- Shipping address selection/addition
- Billing address
- Delivery method selection
- Payment method (COD, Online, Wallets)
- Order summary
- Place order

#### 1.8 Order Success (`/order-success`)
**Features:**
- Order confirmation message
- Order number
- Estimated delivery date
- Download invoice

#### 1.9 Track Order (Public) (`/track/order/[orderNumber]`)
**Features:**
- Order status tracking
- Shipment tracking
- Timeline view

#### 1.10 Track Shipment (`/track/[awb]`)
**Features:**
- AWB-based tracking
- Real-time status

#### 1.11 FAQ (`/faq`)
**Features:**
- Frequently asked questions
- Search functionality

#### 1.12 Contact Us (`/contact`)
**Features:**
- Contact form
- Address, email, phone

#### 1.13 Return Policy (`/return-policy`)
**Features:**
- Return policy content

#### 1.14 Guides (`/guides`)
**Features:**
- User guides
- Video tutorials

#### 1.15 Abandoned Cart Recovery (`/recover-cart`)
**Features:**
- Recover cart link from email
- Pre-filled cart

#### 1.16 Referral Program (`/referral`)
**Features:**
- Referral link generation
- Referral rewards tracking

#### 1.17 Dynamic Pages (`/[slug]`)
**Features:**
- CMS-driven pages (About Us, Terms, Privacy Policy, etc.)

---

### 2. CUSTOMER ACCOUNT PAGES (Login Required)

#### 2.1 Customer Login (`/account/login`)
**Features:**
- Email/phone + password login
- OTP login option
- Social login (optional)
- Forgot password

#### 2.2 Customer Profile (`/account/profile`)
**Features:**
- Personal information
- Edit profile
- Change password

#### 2.3 Addresses (`/account/addresses`)
**Features:**
- Saved addresses
- Add/edit/delete address
- Default address

#### 2.4 Order History (`/account/orders`)
**Features:**
- Past orders list
- Order status
- Track order
- Download invoice
- Reorder

#### 2.5 Order Details (`/account/orders/[orderNumber]`)
**Features:**
- Full order details
- Items ordered
- Shipping address
- Payment details
- Invoice download
- Request return

#### 2.6 Return Order (`/account/orders/[orderNumber]/return`)
**Features:**
- Return request form
- Select items to return
- Return reason
- Refund method

#### 2.7 Returns (`/account/returns`)
**Features:**
- Return history
- RMA status tracking

#### 2.8 Return Details (`/account/returns/[rmaNumber]`)
**Features:**
- Return status
- Refund status

#### 2.9 Service Requests (`/account/services`)
**Features:**
- Service request list
- Create service request
- Track service status

#### 2.10 Wishlist (`/account/wishlist`)
**Features:**
- Saved products
- Move to cart
- Remove from wishlist

#### 2.11 Registered Devices (`/account/devices`)
**Features:**
- Product registration
- Warranty tracking
- Device serial numbers

#### 2.12 AMC Subscriptions (`/account/amc`)
**Features:**
- Active AMC contracts
- AMC renewal
- Service calls under AMC

---

### 3. PARTNER PORTAL (Community Partners - Meesho-style)

#### 3.1 Become Partner (`/become-partner`)
**Features:**
- Partner onboarding form
- KYC submission

#### 3.2 Partner Login (`/partner/login`)
**Features:**
- Partner authentication

#### 3.3 Partner Dashboard (`/partner`)
**Features:**
- Earnings summary
- Active orders
- Performance metrics
- Tier status

#### 3.4 Partner Products (`/partner/products`)
**Features:**
- Product catalog for partners
- Share product links
- Generate referral links

#### 3.5 Partner KYC (`/partner/kyc`)
**Features:**
- KYC document upload
- Verification status

#### 3.6 Partner Earnings (`/partner/earnings`)
**Features:**
- Earnings breakdown
- Commission by order
- Total earnings

#### 3.7 Partner Payouts (`/partner/payouts`)
**Features:**
- Payout history
- Payout status
- Bank details

---

### STOREFRONT BACKEND APIs

- `storefront.py` - Public storefront APIs (products, cart, etc.)
- `d2c_auth.py` - D2C customer authentication
- `portal.py` - Customer portal operations
- `abandoned_cart.py` - Abandoned cart recovery
- `coupons.py` - Coupon validation
- `reviews.py` - Product reviews
- `questions.py` - Product Q&A
- `order_tracking.py` - Public order tracking
- `address.py` - Google Places + DigiPin integration

---

## PART 3: BACKEND API SUMMARY

### Complete List of Backend Endpoints (78 files)

1. `abandoned_cart.py` - Abandoned cart recovery
2. `access_control.py` - Access control rules
3. `accounting.py` - Chart of accounts, journal entries, GL
4. `address.py` - Address validation (Google Places + DigiPin)
5. `ai.py` - AI services (forecasting, ML reconciliation)
6. `amc.py` - AMC contract management
7. `approvals.py` - Multi-level approval workflows
8. `audit_logs.py` - System audit trails
9. `auth.py` - JWT authentication, login, refresh tokens
10. `auto_journal.py` - Auto journal entry generation
11. `banking.py` - Bank reconciliation with ML
12. `billing.py` - E-invoicing, GST calculation, E-way bills
13. `brands.py` - Brand management
14. `call_center.py` - Call center CRM
15. `campaigns.py` - Marketing campaigns
16. `categories.py` - Product categories
17. `channel_reports.py` - Channel-wise P&L reports
18. `channels.py` - Sales channel management
19. `cms.py` - Content management system
20. `commissions.py` - Commission plan management
21. `company.py` - Company/business entity setup
22. `coupons.py` - Coupon management
23. `credentials.py` - Encrypted credential management
24. `customers.py` - Customer profiles, addresses
25. `d2c_auth.py` - D2C customer authentication
26. `dashboard_charts.py` - Dashboard data aggregation
27. `dealers.py` - Dealer management
28. `escalations.py` - Issue escalation management
29. `fixed_assets.py` - Fixed asset management
30. `franchisees.py` - Franchisee CRM and contracts
31. `grn.py` - Goods Receipt Notes (GRN) processing
32. `gst_filing.py` - GSTR-1, GSTR-3B, GSTR-2A, ITC filing
33. `hr.py` - Employees, attendance, payroll, leave management
34. `insights.py` - AI-powered insights
35. `installations.py` - Installation tracking
36. `inventory.py` - Stock management and movements
37. `leads.py` - Lead management with scoring
38. `manifests.py` - Transporter manifest generation
39. `marketplaces.py` - Marketplace API integrations
40. `notifications.py` - In-app notifications
41. `order_tracking.py` - Public order tracking
42. `orders.py` - Order creation, status management
43. `partners.py` - Community partners (Meesho-style)
44. `payments.py` - Payment processing
45. `permissions.py` - Granular permission management
46. `picklists.py` - Order picking lists
47. `portal.py` - Customer portal operations
48. `products.py` - Product CRUD with variants, specs, images
49. `promotions.py` - Promotions and loyalty programs
50. `purchase.py` - Purchase requisitions and PO management
51. `questions.py` - Product Q&A functionality
52. `rate_cards.py` - D2C, B2B, FTL rate card management
53. `reports.py` - Financial and operational reports
54. `returns.py` - Return order and refund processing
55. `reviews.py` - Product reviews and ratings
56. `roles.py` - Role-based access control management
57. `sales_returns.py` - Sales Return Notes (SRN) to vendors
58. `serialization.py` - Barcode generation and serial tracking
59. `service_requests.py` - Service request management
60. `serviceability.py` - Pincode serviceability checks
61. `shipments.py` - Shipment creation and tracking
62. `shipping.py` - Shiprocket integration
63. `snop.py` - S&OP (Sales & Operations Planning)
64. `stock_adjustments.py` - Inventory adjustments and audits
65. `storefront.py` - Public storefront APIs
66. `tds.py` - TDS certificate generation
67. `technicians.py` - Technician assignment & scheduling
68. `transfers.py` - Inter-warehouse stock transfers
69. `transporters.py` - Carrier management
70. `uploads.py` - File upload management
71. `users.py` - User management with role assignments
72. `vendor_invoices.py` - Vendor invoice processing
73. `vendor_payments.py` - Payment to vendors
74. `vendor_proformas.py` - Vendor quotations/proformas
75. `vendors.py` - Vendor management and ledger
76. `warehouses.py` - Warehouse configuration
77. `wms.py` - Warehouse zones, bins, putaway rules
78. Additional endpoint files may exist

---

## PART 4: DATABASE TABLES (200+ tables)

### Core Tables by Category

**Authentication & Access (7 tables)**
- users
- user_roles
- roles
- permissions
- role_permissions
- modules
- audit_logs

**Products (10 tables)**
- products
- product_variants
- product_images
- product_specifications
- product_documents
- product_costs
- categories
- brands
- product_reviews
- product_questions

**Orders (10 tables)**
- orders
- order_items
- order_status_history
- payments
- invoices
- invoice_items
- returns
- return_items
- abandoned_carts
- wishlist_items

**Customers (3 tables)**
- customers
- customer_addresses
- customer_otp

**Inventory (12 tables)**
- stock_items
- inventory_summary
- stock_movements
- stock_transfers
- stock_transfer_items
- stock_adjustments
- stock_adjustment_items
- inventory_audits
- warehouses
- warehouse_serviceability
- serialization_sequences
- po_serials

**Warehouse (6 tables)**
- warehouse_zones
- warehouse_bins
- picklists
- picklist_items
- putaway_rules
- bin_allocation_logs

**Procurement (18 tables)**
- vendors
- vendor_contacts
- vendor_ledgers
- purchase_requisitions
- purchase_requisition_items
- purchase_orders
- po_items
- goods_receipt_notes
- grn_items
- vendor_invoices
- vendor_invoice_items
- vendor_proformas
- vendor_proforma_items
- sales_return_notes
- sales_return_items
- approval_requests
- approval_history
- approval_workflows

**Finance (25 tables)**
- chart_of_accounts
- general_ledgers
- journal_entries
- journal_entry_lines
- financial_periods
- cost_centers
- bank_reconciliation
- banking_transactions
- auto_journal_entries
- tax_invoices
- e_way_bills
- credit_debit_notes
- payment_receipts
- tds_deductions
- tds_rates
- form16a_certificates
- itc_ledgers
- gst_returns
- tax_configurations
- fixed_assets
- asset_depreciation
- vendor_payments
- dealer_payments
- cost_allocations
- financial_reports

**Logistics (12 tables)**
- shipments
- shipment_tracking
- manifests
- manifest_items
- transporters
- transporter_serviceability
- rate_cards
- allocation_rules
- allocation_logs
- shipping_labels
- pod_documents
- sla_logs

**CRM (15 tables)**
- leads
- lead_activities
- calls
- call_recordings
- call_dispositions
- callback_schedules
- escalations
- escalation_histories
- campaigns
- campaign_recipients
- campaign_performance
- notifications
- notification_preferences
- notification_templates
- customer_segments

**Service (10 tables)**
- service_requests
- service_parts
- technicians
- technician_schedules
- installations
- amc_contracts
- amc_plans
- amc_service_calls
- warranty_claims
- warranty_terms

**Multi-Channel (8 tables)**
- sales_channels
- channel_pricing
- channel_inventory
- channel_orders
- channel_commissions
- marketplace_listings
- marketplace_sync_logs
- channel_performance

**Distribution (15 tables)**
- dealers
- dealer_pricing
- dealer_tier_pricing
- dealer_credit_ledgers
- dealer_targets
- dealer_schemes
- dealer_orders
- franchisees
- franchisee_contracts
- franchisee_territories
- franchisee_support_tickets
- community_partners
- partner_tiers
- partner_commissions
- partner_payouts

**HR (12 tables)**
- employees
- departments
- salary_structures
- attendance
- leave_balances
- leave_requests
- leave_types
- payroll
- payslips
- performance_reviews
- performance_kpis
- employee_documents

**Analytics (8 tables)**
- demand_forecasts
- forecast_adjustments
- supply_plans
- snop_scenarios
- external_factors
- inventory_optimizations
- forecast_accuracy
- planning_cycles

**CMS (15 tables)**
- cms_banners
- cms_pages
- cms_page_versions
- cms_seo
- cms_announcements
- cms_testimonials
- cms_features
- cms_usps
- cms_navigation
- cms_mega_menu
- cms_faq
- video_guides
- demo_bookings
- contact_submissions
- partner_content

**Marketing (8 tables)**
- promotions
- coupons
- coupon_usage
- commission_plans
- commission_earners
- commission_transactions
- affiliate_referrals
- loyalty_points

**System (10 tables)**
- document_sequences
- model_code_references
- supplier_codes
- encrypted_credentials
- company_entities
- company_branches
- company_bank_accounts
- system_settings
- email_logs
- sms_logs

**Total:** 200+ tables

---

## SUMMARY

### Dashboard Sections: 26 major sections
1. Dashboard (Home)
2. Intelligence (AI Hub)
3. Orders
4. CRM
5. Partners
6. Procurement
7. Inventory
8. Warehouse (WMS)
9. Logistics
10. S&OP
11. Finance
12. Billing
13. Service
14. HR
15. Channels
16. Distribution
17. Marketing
18. Catalog
19. Serialization
20. CMS
21. Reports
22. Access Control
23. Approvals
24. Notifications
25. Audit Logs
26. Settings

### Storefront Pages: 40+ pages
- Public pages (17)
- Customer account pages (12)
- Partner portal pages (7+)

### Backend APIs: 78 endpoint files

### Database Tables: 200+ tables

---

**This is the COMPLETE structure of your existing ERP system. Use this document to decide how you want to organize your modules.**
