# PHASE 2: Endpoint to Module Mapping

This document maps each API endpoint file to its corresponding ERP module for `@require_module()` decorator implementation.

---

## Module Codes Reference

| Code | Name |
|------|------|
| `system_admin` | System Administration |
| `oms_fulfillment` | OMS, WMS & Fulfillment |
| `procurement` | Procurement (P2P) |
| `finance` | Finance & Accounting |
| `crm_service` | CRM & Service Management |
| `sales_distribution` | Multi-Channel Sales & Distribution |
| `hrms` | HRMS |
| `d2c_storefront` | D2C E-Commerce Storefront |
| `scm_ai` | Supply Chain & AI Insights |
| `marketing` | Marketing & Promotions |

---

## Endpoint File Mapping (78 files)

### Module: system_admin (10 files)
- `auth.py` - Authentication (login, register, tokens)
- `users.py` - User management
- `roles.py` - Role management
- `permissions.py` - Permission management
- `access_control.py` - Access control rules
- `audit_logs.py` - System audit logs
- `notifications.py` - System notifications
- `uploads.py` - File upload management
- `address.py` - Address lookup (shared utility)
- `credentials.py` - Encrypted credentials management

### Module: oms_fulfillment (18 files)
- `orders.py` - Order management
- `inventory.py` - Inventory tracking
- `warehouses.py` - Warehouse management
- `wms.py` - WMS (zones, bins, putaway)
- `picklists.py` - Pick list management
- `shipments.py` - Shipment creation & tracking
- `manifests.py` - Manifest management
- `transporters.py` - Transporter management
- `serviceability.py` - Pincode serviceability
- `rate_cards.py` - Rate card management
- `transfers.py` - Stock transfers
- `stock_adjustments.py` - Stock adjustments & audits
- `serialization.py` - Barcode & serial number tracking
- `shipping.py` - Shiprocket integration
- `order_tracking.py` - Customer order tracking
- `returns.py` - Returns & refunds
- `sales_returns.py` - Sales Return Notes (SRN)
- `portal.py` - Customer self-service portal

### Module: procurement (6 files)
- `vendors.py` - Vendor management
- `purchase.py` - Purchase orders
- `grn.py` - Goods Receipt Notes
- `vendor_invoices.py` - Vendor invoice & 3-way matching
- `vendor_proformas.py` - Vendor proformas/quotations
- `vendor_payments.py` - Vendor payment processing

### Module: finance (10 files)
- `accounting.py` - General ledger & journal entries
- `billing.py` - E-invoice & billing
- `banking.py` - Bank reconciliation
- `tds.py` - TDS certificate generation
- `gst_filing.py` - GST e-filing & ITC management
- `auto_journal.py` - Auto journal entry generation
- `approvals.py` - Multi-level approval workflow
- `payments.py` - Razorpay payment integration
- `commissions.py` - Commission & incentives
- `fixed_assets.py` - Fixed asset management

### Module: crm_service (8 files)
- `customers.py` - Customer management
- `leads.py` - Lead management
- `call_center.py` - Call center CRM
- `service_requests.py` - Service request management
- `technicians.py` - Technician management
- `installations.py` - Installation & warranty
- `amc.py` - AMC/warranty management
- `escalations.py` - Escalation management

### Module: sales_distribution (8 files)
- `channels.py` - Sales channel management
- `marketplaces.py` - Marketplace integration
- `channel_reports.py` - Channel P&L & reports
- `reports.py` - Sales reports
- `partners.py` - Community partners (Meesho-style)
- `franchisees.py` - Franchisee CRM
- `dealers.py` - Dealer/distributor management
- `abandoned_cart.py` - Abandoned cart recovery

### Module: hrms (1 file)
- `hr.py` - HR, payroll, attendance, leave

### Module: d2c_storefront (7 files)
- `storefront.py` - Public storefront APIs
- `cms.py` - CMS content management
- `d2c_auth.py` - D2C customer authentication
- `reviews.py` - Product reviews
- `questions.py` - Product Q&A
- `coupons.py` - Coupon management
- `company.py` - Company/business entity info

### Module: scm_ai (3 files)
- `insights.py` - AI insights
- `ai.py` - Advanced AI services
- `snop.py` - S&OP planning

### Module: marketing (2 files)
- `campaigns.py` - Campaign management
- `promotions.py` - Promotions & loyalty

### Special Cases (5 files)

#### Multi-Module (Shared Resources)
- `products.py` - **Multiple modules** (oms_fulfillment, d2c_storefront, sales_distribution)
- `categories.py` - **Multiple modules** (oms_fulfillment, d2c_storefront)
- `brands.py` - **Multiple modules** (oms_fulfillment, d2c_storefront)
- `dashboard_charts.py` - **Multiple modules** (system_admin for viewing)

#### Public/No Auth Required
- `test_modules.py` - **No decorator** (testing only)

---

## Implementation Strategy

### Phase 2A: Single-Module Endpoints (73 files)
Add `@require_module("module_code")` to all endpoints in each file.

**Example:**
```python
from app.core.module_decorators import require_module

@router.get("/vendors")
@require_module("procurement")
async def list_vendors(...):
    ...
```

### Phase 2B: Multi-Module Endpoints (4 files)
For endpoints used by multiple modules, use logical OR approach.

**Option 1: Module-specific endpoints**
```python
# Different endpoints for different modules
@router.get("/products")
@require_module("oms_fulfillment")
async def list_products_oms(...):
    ...

@router.get("/storefront/products")  # Public, no decorator
async def list_products_storefront(...):
    ...
```

**Option 2: Check any module (less restrictive)**
```python
# Allow if tenant has ANY of these modules
@router.get("/products")
async def list_products(request: Request, ...):
    # Custom check: allow if tenant has oms_fulfillment OR d2c_storefront
    ...
```

### Phase 2C: Public Endpoints
Some endpoints should remain public (no tenant/module check):
- `/api/v1/storefront/*` - D2C public APIs
- `/api/auth/login` - Authentication
- `/api/auth/register` - Registration
- `/health` - Health check

---

## Decorator Placement

### ✅ Correct Placement
```python
@router.get("/endpoint")
@require_module("module_code")  # ← After route decorator
async def handler(request: Request, ...):
    ...
```

### ❌ Incorrect Placement
```python
@require_module("module_code")  # ← Wrong! Must come after @router
@router.get("/endpoint")
async def handler(...):
    ...
```

---

## Testing After Implementation

After adding decorators, test each module:

```bash
# Test with tenant that HAS the module (should succeed)
curl -H "X-Tenant-ID: <tenant-id>" http://localhost:8000/api/v1/orders

# Test with tenant that DOESN'T have the module (should fail 403)
curl -H "X-Tenant-ID: <tenant-id>" http://localhost:8000/api/v1/accounting
```

---

## Progress Tracking

- [ ] system_admin (10 files)
- [ ] oms_fulfillment (18 files)
- [ ] procurement (6 files)
- [ ] finance (10 files)
- [ ] crm_service (8 files)
- [ ] sales_distribution (8 files)
- [ ] hrms (1 file)
- [ ] d2c_storefront (7 files)
- [ ] scm_ai (3 files)
- [ ] marketing (2 files)
- [ ] Multi-module endpoints (4 files)

**Total: 77 files** (excluding test_modules.py)

---

## Estimated Effort

- Single-module files: ~2 minutes each = 146 minutes (2.4 hours)
- Multi-module files: ~10 minutes each = 40 minutes
- Testing: ~30 minutes
- **Total: ~3.5 hours**

---

Ready to implement Phase 2!
