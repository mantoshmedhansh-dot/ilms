# CLAUDE-D2C.md - D2C Storefront Project Instructions

## Project Overview

**Aquapurite D2C Storefront** - Consumer-facing e-commerce website for water purifiers.

- **Frontend**: Next.js 14+ with TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Shared FastAPI backend (same as ERP)
- **Database**: PostgreSQL (Supabase)
- **Deployment**: Vercel (separate project from ERP)

---

## Domain Configuration

| Project | Domain | Purpose |
|---------|--------|---------|
| **D2C Storefront** | www.aquapurite.com | Customer-facing store |
| **ERP Dashboard** | www.aquapurite.org | Admin panel |

Both projects deploy from the same repository but are separate Vercel projects with domain-based routing via Next.js middleware (`src/middleware.ts`).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    www.aquapurite.com                       │
│                    (D2C Storefront)                         │
├─────────────────────────────────────────────────────────────┤
│  Next.js Frontend (Vercel - D2C Project)                    │
│  ├── Public pages (no auth)                                 │
│  ├── Customer portal (OTP auth) - TODO                      │
│  └── Cart/Checkout (guest + logged in)                      │
├─────────────────────────────────────────────────────────────┤
│                    ↓ API Calls ↓                            │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Render)                                   │
│  ├── /api/v1/storefront/* (public)        ← D2C APIs        │
│  ├── /api/v1/customer/*   (customer auth) ← TODO            │
│  └── /api/v1/*            (admin auth)    ← ERP Dashboard   │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL (Supabase) - Shared but scoped                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Separation from ERP Dashboard - ACHIEVED

| Aspect | Implementation | Status |
|--------|----------------|--------|
| API Routes | /api/v1/storefront/* (public) vs /api/v1/* (admin) | ✅ |
| Authentication | Storefront: None required, Dashboard: JWT + RBAC | ✅ |
| Frontend Routes | / → Storefront, /dashboard → Admin | ✅ |
| API Client | Separate axios instance without auth headers | ✅ |
| Domain Routing | Middleware separates .com and .org traffic | ✅ |

---

## What's Built (Backend)

### Storefront API Endpoints

```
GET  /api/v1/storefront/products         # Product listing with filters
GET  /api/v1/storefront/products/{slug}  # Product detail
GET  /api/v1/storefront/categories       # Categories
GET  /api/v1/storefront/brands           # Brands
GET  /api/v1/storefront/company          # Public company info
POST /api/v1/orders/d2c                  # Create D2C order (guest)
GET  /api/v1/serviceability/check/{pincode}  # PIN serviceability
```

### Database Models

- `WarehouseServiceability` - PIN code matrix with SLA
- `AllocationRule` - Channel-specific allocation (D2C, Amazon, etc.)
- `AllocationLog` - Audit trail

---

## What's Built (Frontend)

| Page | Route | Status |
|------|-------|--------|
| Homepage | / | ✅ Hero, Categories, Products |
| Product Listing | /products | ✅ Filters, Pagination |
| Product Detail | /products/[slug] | ✅ Images, Specs, PIN check |
| Category | /category/[slug] | ✅ Category products |
| Cart | /cart | ✅ Zustand state |
| Checkout | /checkout | ✅ 3-step (Shipping → Payment → Review) |
| Order Success | /order-success | ✅ Confirmation |
| About | /about | ✅ Company info |
| Contact | /contact | ✅ Contact form |

---

## PIN Code Serviceability - IMPLEMENTED

### Backend (Complete)

```
✅ WarehouseServiceability table with:
   - pincode, warehouse_id
   - estimated_days (SLA)
   - cod_available, prepaid_available
   - shipping_cost, zone

✅ API endpoint: GET /serviceability/check/{pincode}
   Returns: is_serviceable, estimated_days, cod_available
```

### Frontend (Complete)

```
✅ PinCodeChecker component on Product Detail Page
✅ Real-time SLA display ("Delivery by Jan 20")
✅ COD availability badge
✅ Free delivery threshold indicator
✅ localStorage persistence for saved pincode
✅ Auto-check on page load if pincode saved
```

**UI Pattern (Amazon/Flipkart Style):**
```
┌─────────────────────────────────────────┐
│ Deliver to: [110001] [Check]            │
│                                         │
│ ✓ Delivery by Monday, Jan 20            │
│ ✓ Cash on Delivery available            │
│ ✓ Free delivery on orders above ₹999    │
└─────────────────────────────────────────┘
```

---

## Gap Analysis

### Critical Gaps (P0 - Must Have)

| Feature | Status | Notes |
|---------|--------|-------|
| Customer Login/Registration | ❌ Missing | OTP-based recommended |
| Payment Webhook (Razorpay) | ❌ Missing | Required for order confirmation |
| Order Confirmation Email/SMS | ❌ Missing | Required |
| Real-time Inventory Reservation | ❌ Missing | Required for stock accuracy |

### High Priority Gaps (P1)

| Feature | Status | Notes |
|---------|--------|-------|
| Order History for Customers | ❌ Missing | Required with login |
| Product Reviews & Ratings | ❌ Missing | Standard for D2C |
| Coupon/Promo Codes | ❌ Missing | Standard |
| Order Tracking Updates | ❌ Missing | Required |
| Return/Exchange Flow | ❌ Missing | Required |

### Medium Priority Gaps (P2)

| Feature | Status | Notes |
|---------|--------|-------|
| Wishlist | ❌ Missing | Common |
| Recently Viewed | ❌ Missing | Common |
| Product Recommendations | ❌ Missing | Common |
| CMS for Banners | ❌ Missing | Common |
| Abandoned Cart Recovery | ❌ Missing | Common |

---

## Recommended Roadmap

### Phase 1: Critical (1-2 weeks)

1. **Payment webhook handling**
   - Razorpay webhook endpoint
   - Update order payment status

2. **Order notifications**
   - Email confirmation (SendGrid/AWS SES)
   - SMS via API (MSG91/Twilio)

3. **PIN code validation in checkout**
   - Block checkout if unserviceable
   - Show delivery SLA before payment

### Phase 2: Customer Experience (2-3 weeks)

1. Customer registration/login (OTP-based)
2. Order history dashboard
3. Product reviews & ratings
4. Coupon code system

### Phase 3: Operations (2-3 weeks)

1. Real-time inventory sync
2. Order tracking integration
3. Return/RMA workflow
4. Abandoned cart recovery

---

## Key Files

### Frontend (D2C Specific)

| File | Purpose |
|------|---------|
| `src/middleware.ts` | Domain-based routing |
| `src/app/(storefront)/` | All storefront pages |
| `src/components/storefront/` | Storefront-specific components |
| `src/lib/storefront/api.ts` | Public API client (no auth) |
| `src/lib/storefront/cart-store.ts` | Zustand cart state |

### Backend (Storefront APIs)

| File | Purpose |
|------|---------|
| `app/api/v1/endpoints/storefront.py` | Product/category endpoints |
| `app/api/v1/endpoints/orders_storefront.py` | D2C order creation |
| `app/api/v1/endpoints/serviceability.py` | PIN code checking |

---

## Deployment

### D2C Project (Vercel)

- **Project Name**: D2C
- **Production URL**: d2c-lovat.vercel.app
- **Custom Domain**: www.aquapurite.com
- **Repository**: Same as ERP (aquapurite/ERP)
- **Root Directory**: frontend
- **Framework**: Next.js

### Environment Variables

```env
NEXT_PUBLIC_API_URL=https://aquapurite-erp-api.onrender.com
NEXT_PUBLIC_SITE_URL=https://www.aquapurite.com
```

---

## Score Summary

| Category | Score | Notes |
|----------|-------|-------|
| Separation from ERP | ⭐⭐⭐⭐⭐ | Excellent |
| Product Catalog | ⭐⭐⭐⭐ | Good, needs reviews |
| PIN Serviceability (Backend) | ⭐⭐⭐⭐ | Good, well-designed |
| PIN Serviceability (Frontend) | ⭐⭐⭐⭐ | Integrated on product page |
| Checkout Flow | ⭐⭐⭐ | Works, needs payment webhook |
| Customer Experience | ⭐⭐ | No login, no history |
| Post-Order Experience | ⭐ | No tracking, no notifications |

---

## Local Development

```bash
cd frontend

# Install dependencies
pnpm install

# Run development server (D2C on localhost:3000)
pnpm dev

# Build for production
pnpm build
```

**Note**: localhost:3000 routes to storefront, localhost:3001 would route to dashboard (per middleware config).
