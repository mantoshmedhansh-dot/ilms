# ilms.ai - Module Structure Map
**Quick Reference Guide for Module Organization**

---

## MODULE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                         ilms.ai ERP Platform                     │
│                     Multi-Tenant SaaS Architecture               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┬──────────────────┬──────────────────┬─────────────────┐
│   COMMERCE       │   OPERATIONS     │   FINANCE        │   PEOPLE        │
├──────────────────┼──────────────────┼──────────────────┼─────────────────┤
│ • D2C Storefront │ • OMS            │ • Finance &      │ • CRM           │
│ • Multi-Channel  │ • Inventory      │   Accounting     │ • HRMS          │
│ • Distribution   │ • WMS            │                  │ • Service Mgmt  │
│ • CMS            │ • Procurement    │                  │                 │
│                  │ • Logistics      │                  │                 │
└──────────────────┴──────────────────┴──────────────────┴─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      ADVANCED MODULES                            │
│                     • Analytics & AI                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 14 INDEPENDENT MODULES

### 🛒 COMMERCE MODULES

#### 1. D2C Storefront (E-commerce)
**Who needs it:** B2C sellers, online retailers
**Price:** ₹4,999/month
**Key Features:**
- Product catalog & browsing
- Shopping cart & checkout
- Payment gateway (Razorpay)
- Order tracking
- Customer accounts
- Reviews & ratings
- Partner/affiliate portal

**Database:** 20+ tables (products, customers, orders, cms_*)
**APIs:** 15+ endpoints
**Pages:** 39 storefront pages

**Dependencies:** OMS, Inventory, CMS

---

#### 2. Multi-Channel Commerce
**Who needs it:** Omnichannel retailers, marketplace sellers
**Price:** ₹5,999/month
**Key Features:**
- Sales channel management (B2B, B2C, Marketplace)
- Channel-specific pricing
- Marketplace integrations (Amazon, Flipkart)
- Channel inventory sync
- Commission tracking
- Channel P&L reports

**Database:** 8+ tables (channels, channel_pricing, channel_orders)
**APIs:** 10+ endpoints
**Pages:** 8 dashboard pages

**Dependencies:** OMS, Inventory

---

#### 3. Distribution Management
**Who needs it:** Manufacturers with dealer networks, franchisors
**Price:** ₹5,999/month
**Key Features:**
- Dealer management
- Franchisee network
- Tiered pricing
- Credit management
- Community partners (Meesho-style)
- Commission & payouts
- Target tracking

**Database:** 15+ tables (dealers, franchisees, partners, commissions)
**APIs:** 12+ endpoints
**Pages:** 10 dashboard pages

**Dependencies:** OMS

---

#### 4. Content Management System (CMS)
**Who needs it:** Companies managing website content
**Price:** ₹1,999/month
**Key Features:**
- Banner management
- Page builder with versioning
- SEO configuration
- Navigation & mega menu
- FAQ management
- Testimonials
- Video guides

**Database:** 8+ tables (cms_*)
**APIs:** 5+ endpoints
**Pages:** 11 CMS sections

**Dependencies:** None (often used with D2C)

---

### ⚙️ OPERATIONS MODULES

#### 5. Order Management System (OMS)
**Who needs it:** ANY company processing orders
**Price:** ₹3,999/month
**Key Features:**
- Multi-channel order creation
- Order status tracking
- Order allocation rules
- Payment processing
- Invoice generation
- Returns & refunds
- Order analytics

**Database:** 15+ tables (orders, order_items, invoices, returns)
**APIs:** 20+ endpoints
**Pages:** 12 dashboard pages

**Dependencies:** Inventory

---

#### 6. Inventory Management
**Who needs it:** Companies managing stock
**Price:** ₹2,999/month (CORE MODULE)
**Key Features:**
- Real-time stock tracking
- Multi-location inventory
- Stock transfers
- Stock adjustments
- Reorder points
- Serialization/barcodes
- Stock valuation

**Database:** 12+ tables (stock_items, stock_movements, transfers)
**APIs:** 15+ endpoints
**Pages:** 8 dashboard pages

**Dependencies:** None (standalone core module)

---

#### 7. Warehouse Management System (WMS)
**Who needs it:** Companies with complex warehouse operations
**Price:** ₹4,999/month
**Key Features:**
- Zone, rack, bin management
- Putaway rules engine
- Picklist generation
- Bin allocation
- Cycle counting
- Warehouse analytics
- Multi-warehouse support

**Database:** 10+ tables (warehouses, zones, bins, picklists)
**APIs:** 12+ endpoints
**Pages:** 9 dashboard pages

**Dependencies:** Inventory

---

#### 8. Procurement (Purchase-to-Pay)
**Who needs it:** Companies managing supplier purchases
**Price:** ₹4,999/month
**Key Features:**
- Vendor management
- Purchase requisition workflow
- Purchase orders
- GRN processing
- 3-way matching
- Vendor invoices & payments
- Approval workflows

**Database:** 18+ tables (vendors, purchase_orders, grn, invoices)
**APIs:** 18+ endpoints
**Pages:** 14 dashboard pages

**Dependencies:** Inventory

---

#### 9. Logistics & Shipping
**Who needs it:** Companies managing shipments
**Price:** ₹3,999/month
**Key Features:**
- Shipment tracking
- Multi-carrier management
- Manifest generation
- Rate card management
- Serviceability matrix
- Shiprocket integration
- SLA monitoring

**Database:** 12+ tables (shipments, manifests, transporters, rate_cards)
**APIs:** 15+ endpoints
**Pages:** 10 dashboard pages

**Dependencies:** OMS, Inventory

---

### 💰 FINANCE MODULE

#### 10. Finance & Accounting
**Who needs it:** ALL businesses (legal requirement)
**Price:** ₹6,999/month
**Key Features:**
- Chart of accounts & GL
- Journal entries
- AP/AR management
- Bank reconciliation (ML-powered)
- Financial reports (P&L, Balance Sheet)
- GST compliance (GSTR-1, 3B, 2A, ITC)
- TDS & Form 16A
- E-invoice & E-way bill
- Fixed assets

**Database:** 25+ tables (accounts, journals, GL, tax, banking)
**APIs:** 25+ endpoints
**Pages:** 15 finance sections

**Dependencies:** None (can integrate with OMS, Procurement)

---

### 👥 PEOPLE MODULES

#### 11. Customer Relationship Management (CRM)
**Who needs it:** Sales teams, customer-facing businesses
**Price:** ₹3,999/month
**Key Features:**
- Customer 360° view
- Lead management & scoring
- Call center integration
- Escalation management
- Campaign management
- Customer segmentation
- Churn analysis

**Database:** 15+ tables (customers, leads, calls, campaigns)
**APIs:** 15+ endpoints
**Pages:** 10 CRM sections

**Dependencies:** None (integrates with OMS)

---

#### 12. Service Management (After-Sales)
**Who needs it:** Service providers, warranty management
**Price:** ₹3,999/month
**Key Features:**
- Service request management
- Technician scheduling
- Installation tracking
- Warranty management
- AMC contracts
- Parts tracking
- SLA monitoring

**Database:** 10+ tables (service_requests, technicians, installations, amc)
**APIs:** 12+ endpoints
**Pages:** 8 service sections

**Dependencies:** OMS

---

#### 13. Human Resource Management System (HRMS)
**Who needs it:** Companies managing employees
**Price:** ₹4,999/month
**Key Features:**
- Employee management
- Attendance tracking
- Leave management
- Payroll processing
- Salary structures
- Payslip generation
- Performance reviews

**Database:** 12+ tables (employees, attendance, payroll, leave)
**APIs:** 10+ endpoints
**Pages:** 9 HR sections

**Dependencies:** None (integrates with Finance for payroll accounting)

---

### 🤖 ADVANCED MODULE

#### 14. Analytics & AI
**Who needs it:** Data-driven companies wanting insights
**Price:** ₹7,999/month
**Key Features:**
- Demand forecasting (ML-based)
- Sales & Operations Planning (S&OP)
- Scenario planning
- Reorder suggestions
- Slow-moving stock detection
- Churn risk analysis
- ML bank reconciliation
- Custom dashboards

**Database:** 8+ tables (forecasts, supply_plans, scenarios)
**APIs:** 12+ endpoints
**Pages:** 8 analytics sections

**Dependencies:** OMS, Inventory (needs data to analyze)

---

## DEPENDENCY MAP

```
                    ┌─────────────┐
                    │  Inventory  │ ◄─── Core Module
                    │   (Core)    │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐     ┌─────────┐     ┌──────────┐
    │   WMS    │     │   OMS   │     │Procure-  │
    └──────────┘     └────┬────┘     │ment      │
                          │          └─────┬────┘
                          │                │
          ┌───────────────┼────────┬───────┘
          ▼               ▼        ▼
    ┌──────────┐   ┌──────────┐ ┌─────────┐
    │Logistics │   │   D2C    │ │ Finance │
    └──────────┘   │Storefront│ │  (AP)   │
                   └─────┬────┘ └─────────┘
                         │
                   ┌─────┴─────┐
                   ▼           ▼
              ┌────────┐  ┌────────┐
              │  CMS   │  │ Service│
              └────────┘  └────────┘

    ┌──────────────────────────────────┐
    │     Multi-Channel Commerce       │
    │  (requires OMS + Inventory)      │
    └──────────────────────────────────┘

    ┌──────────────────────────────────┐
    │      Distribution Mgmt           │
    │      (requires OMS)              │
    └──────────────────────────────────┘

    ┌──────────────────────────────────┐
    │      Analytics & AI              │
    │  (requires OMS + Inventory)      │
    └──────────────────────────────────┘

    ┌──────────────────────────────────┐
    │      Standalone Modules          │
    │  • CRM  • HRMS  • Finance        │
    └──────────────────────────────────┘
```

---

## PRE-PACKAGED BUNDLES

### 🌱 Starter Bundle - ₹9,999/month
**For:** Small businesses starting with ERP
**Includes:**
- ✅ Inventory Management
- ✅ OMS
- ✅ CRM
- ✅ Finance (Basic - no GST filing)

**Limits:** 5 users, 1000 orders/month

---

### 🚀 Professional Bundle - ₹24,999/month
**For:** Growing businesses with warehouses
**Includes:**
- ✅ Everything in Starter
- ✅ WMS
- ✅ Procurement
- ✅ Logistics
- ✅ Service Management
- ✅ Finance (Full with GST)

**Limits:** 20 users, 5000 orders/month

---

### 🏢 Enterprise Bundle - Custom Pricing
**For:** Large enterprises needing everything
**Includes:**
- ✅ ALL 14 modules
- ✅ Unlimited users
- ✅ Unlimited transactions
- ✅ Dedicated support
- ✅ Custom integrations

---

## À LA CARTE PRICING SUMMARY

| Module | Price/Month | Category |
|--------|-------------|----------|
| Inventory | ₹2,999 | Core |
| OMS | ₹3,999 | Core |
| WMS | ₹4,999 | Operations |
| Procurement | ₹4,999 | Operations |
| Logistics | ₹3,999 | Operations |
| Finance | ₹6,999 | Finance |
| Multi-Channel | ₹5,999 | Commerce |
| Distribution | ₹5,999 | Commerce |
| D2C Storefront | ₹4,999 | Commerce |
| CRM | ₹3,999 | People |
| Service Mgmt | ₹3,999 | People |
| HRMS | ₹4,999 | People |
| Analytics & AI | ₹7,999 | Advanced |
| CMS | ₹1,999 | Add-on |

**Total if bought separately:** ₹63,986/month
**Enterprise Bundle:** ~₹50,000/month (save ₹13,986)

---

## CUSTOMER USE CASES

### 🏭 Use Case 1: Small Manufacturer
**Business:** Makes consumer durables
**Needs:** Track inventory, manage suppliers, basic accounting
**Modules:** Inventory + Procurement + Finance (Basic)
**Cost:** ₹9,999/month (Starter Bundle)

---

### 🛍️ Use Case 2: D2C Brand
**Business:** Online-only water purifier brand
**Needs:** E-commerce, order processing, shipping, customer support
**Modules:** D2C Storefront + OMS + Inventory + Logistics + CRM
**Cost:** ₹19,995/month

---

### 📦 Use Case 3: Distributor with Warehouses
**Business:** Distributes to dealers across India
**Needs:** Advanced warehousing, dealer network, logistics
**Modules:** OMS + Inventory + WMS + Distribution + Logistics
**Cost:** ₹22,995/month

---

### 🏢 Use Case 4: Omnichannel Enterprise
**Business:** Sells via website, marketplaces, and dealers
**Needs:** Everything
**Modules:** All 14 modules
**Cost:** ₹50,000/month (Enterprise Bundle)

---

## TECHNICAL STACK OVERVIEW

```
┌──────────────────────────────────────────────────────┐
│                    FRONTEND                          │
│  Next.js 14 + TypeScript + Tailwind + shadcn/ui     │
│          (Dynamic module-based routing)              │
└──────────────────┬───────────────────────────────────┘
                   │ REST APIs
┌──────────────────▼───────────────────────────────────┐
│                    BACKEND                           │
│     FastAPI + SQLAlchemy (Async) + Python 3.11      │
│        (Tenant-aware middleware + decorators)        │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│                   DATABASE                           │
│            PostgreSQL (Supabase)                     │
│                                                      │
│  Schema: public (tenants, modules, subscriptions)    │
│  Schema: tenant_001 (Customer 1 data)               │
│  Schema: tenant_002 (Customer 2 data)               │
│  Schema: tenant_NNN (Customer N data)               │
└──────────────────────────────────────────────────────┘
```

---

## MULTI-TENANCY STRATEGY

### Schema-per-Tenant Approach (Recommended)

**Structure:**
```
Database: ilms_erp
├── public schema
│   ├── tenants (company master)
│   ├── modules (module definitions)
│   ├── plans (pricing plans)
│   ├── tenant_subscriptions (who has what)
│   └── feature_flags (granular control)
│
├── tenant_001 (Aquapurite)
│   ├── All 200+ tables (all modules)
│   └── Full data isolation
│
├── tenant_002 (Customer A)
│   ├── Only subscribed module tables
│   │   (e.g., OMS, Inventory, Finance)
│   └── Their data only
│
└── tenant_003 (Customer B)
    ├── Different module set
    │   (e.g., D2C, OMS, CRM, Logistics)
    └── Their data only
```

**Benefits:**
- ✅ Strong data isolation (security)
- ✅ Easy backup/restore per customer
- ✅ Can create only needed tables
- ✅ Performance isolation
- ✅ Schema-level permissions

---

## ACCESS CONTROL FLOW

```
1. User logs in → JWT token issued with tenant_id

2. API request comes in
   ↓
3. Tenant middleware extracts tenant_id
   ↓
4. Database session set to tenant schema
   ↓
5. Module decorator checks subscription
   ↓
6. If not subscribed → HTTP 403 Error
   ↓
7. If subscribed → Process request
   ↓
8. Return response
```

**Code Example:**
```python
@router.post("/api/wms/zones")
@require_module("wms")  # ← Checks subscription
async def create_zone(request: Request, data: ZoneCreate):
    tenant = request.state.tenant  # ← From middleware
    # Use tenant-specific schema
    return await create_zone_in_db(tenant.schema, data)
```

---

## IMPLEMENTATION TIMELINE

### Phase 1: Foundation (2 weeks)
- Multi-tenant database setup
- Tenant management system
- Subscription tracking

### Phase 2: Module Separation (4 weeks)
- Refactor backend with decorators
- Module dependency management
- Dynamic route registration

### Phase 3: Frontend Modularization (3 weeks)
- Dynamic navigation
- Feature gates
- Tenant settings UI

### Phase 4: Testing & Migration (2 weeks)
- Data migration
- Multi-tenant testing
- Security audit

### Phase 5: Billing & Launch (2 weeks)
- Payment integration
- Subscription management
- Customer portal

**Total:** ~13 weeks (3 months)

---

## KEY DECISIONS NEEDED

1. **Multi-tenancy:** Schema-per-tenant or RLS? → **Recommend: Schema-per-tenant**

2. **Trial Period:** 14 days or 30 days? → **Suggest: 14 days**

3. **Onboarding:** Self-service or sales-assisted? → **Suggest: Both**

4. **Module Tiers:** Basic/Pro within modules? → **Suggest: Start simple, add later**

5. **White-labeling:** Allow resellers? → **Decide based on business model**

6. **API Access:** Public APIs for customers? → **Suggest: Yes, premium feature**

7. **Minimum Module Set:** What's MVP for launch? → **Suggest: OMS + Inventory + Finance**

---

## NEXT ACTIONS

✅ **Step 1:** Review this proposal with stakeholders

✅ **Step 2:** Answer key decision questions above

✅ **Step 3:** Prioritize which modules are most important for first customers

✅ **Step 4:** Approve architecture approach (schema-per-tenant)

✅ **Step 5:** Begin Phase 1 implementation

✅ **Step 6:** Set up project timeline and milestones

---

**Quick Summary:**
- **14 independent modules** that can be sold separately
- **Multi-tenant SaaS** with schema-per-tenant isolation
- **Flexible pricing**: Bundles (₹9,999 - ₹50,000/month) or à la carte (₹1,999 - ₹7,999/module)
- **3-month implementation** timeline
- **Scalable architecture** supporting unlimited tenants

Ready to transform your ERP into a multi-tenant SaaS platform! 🚀
