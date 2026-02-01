# Aquapurite ERP - Comprehensive System Audit Report

**Date:** January 25, 2026
**Scope:** Backend API, ERP Frontend, D2C Storefront, Supabase Database
**Objective:** Reliability, Sustainability, and Scalability Assessment

---

## Executive Summary

This audit examined 204 database tables, 76 API endpoint files, 182+ frontend pages, and comprehensive security configurations. The system demonstrates **strong architectural foundations** with excellent naming conventions and proper relationship definitions. However, critical issues were identified requiring immediate attention.

### Overall Assessment

| Area | Grade | Critical Issues | High Issues | Medium Issues |
|------|-------|-----------------|-------------|---------------|
| **Backend API** | B+ | 5 | 11 | 17 |
| **ERP Frontend** | B | 8 | 6 | 12 |
| **D2C Storefront** | B | 3 | 7 | 15 |
| **Database Schema** | A- | 0 | 3 | 8 |
| **Security** | C+ | 2 | 8 | 8 |
| **Overall** | **B** | **18** | **35** | **60** |

---

## PART 1: PRODUCTION DATABASE ANALYSIS

### Database Statistics

| Metric | Value |
|--------|-------|
| Total Tables | 204 |
| Total Indexes | 433 |
| Total Foreign Keys | 500+ |
| Tables with Primary Keys | 100% |

### Data Type Issues

| Issue Type | Count | Impact |
|------------|-------|--------|
| JSON columns (should be JSONB) | 105 | Query performance degraded |
| JSONB columns (correct) | 31 | Good |
| Timestamps WITHOUT timezone | 485 | Timezone bugs possible |
| Timestamps WITH timezone | 84 | Correct |
| PostgreSQL ENUMs | 0 | Good - all converted to VARCHAR |

### Top Tables by Row Count

| Table | Rows | Notes |
|-------|------|-------|
| po_serials | 28,700 | Barcode generation |
| audit_logs | 367 | Activity tracking |
| role_permissions | 210 | RBAC |
| permissions | 137 | Access control |
| products | 39 | Product catalog |

### Tables with Many Columns (Potential Normalization Issues)

| Table | Columns | Recommendation |
|-------|---------|----------------|
| tax_invoices | 81 | Review for denormalization |
| dealers | 81 | Consider splitting into profiles/address/banking |
| community_partners | 78 | Good - comprehensive partner data |
| vendors | 75 | Consider address/contact tables |
| leads | 66 | Good for CRM use case |

### Missing Audit Timestamps

Tables lacking proper audit trail:
- `affiliate_referrals` - missing updated_at
- `amc_contracts` - missing created_at, updated_at
- `amc_plans` - missing created_at, updated_at
- `customer_referrals` - missing both timestamps
- 16+ additional tables

### Recommended Index Additions

```sql
-- High-traffic query patterns needing indexes
CREATE INDEX ix_product_category_active_status ON products(category_id, is_active, status);
CREATE INDEX ix_order_status_created ON orders(status, created_at);
CREATE INDEX ix_order_customer_created ON orders(customer_id, created_at);
CREATE INDEX ix_gl_period_account_date ON general_ledger(period_id, account_id, posting_date);
CREATE INDEX ix_dealer_type_status_tier ON dealers(dealer_type, status, tier);
```

---

## PART 2: BACKEND API AUDIT

### CRITICAL Issues (5)

#### 1. Missing Error Handling in Transaction-Critical Services
**File:** `app/services/order_service.py`
**Impact:** Partial orders created if exceptions occur after some items inserted
**Fix:** Add comprehensive try-except with transaction rollback

#### 2. Missing Flush Before Referencing Auto-Generated IDs
**File:** `app/services/shipment_service.py`
**Impact:** Intermittent 500 errors in concurrent scenarios
**Fix:** Ensure `await db.flush()` before creating child records

#### 3. Foreign Key CASCADE Violates Audit Trail
**Files:** `app/models/channel.py`, 40+ occurrences
**Impact:** Deleting a channel silently deletes all pricing history
**Fix:** Change CASCADE to RESTRICT for business-critical entities

#### 4. N+1 Query Problem in Product List
**File:** `app/api/v1/endpoints/products.py`
**Impact:** 20 products = 40+ queries instead of 1-2
**Fix:** Add eager loading for images, variants in service query

#### 5. Missing Audit Timestamps on Critical Models
**Files:** ChannelPricing, StockItem, ServiceRequest
**Impact:** Cannot track who changed pricing or inventory
**Fix:** Add updated_at and updated_by fields

### HIGH Issues (11)

1. **Inconsistent Response Schemas** - InvoiceResponse missing `qr_code_data`, `irn`, `irn_date`
2. **Missing Input Validation** - ChannelPricing accepts negative discounts
3. **Authorization Bypass on Stats Endpoints** - `/channels/stats` missing permission check
4. **Transaction Isolation Issues** - Race condition in inventory updates
5. **Missing Database Connection Pooling** - No pool configuration for production
6. **Circular Dependency Risk** - Services importing each other
7. **Status Field Comparison Issues** - Enum vs VARCHAR mismatches
8. **Missing Pagination** - Some endpoints default to 100+ results
9. **Logging Issues** - No context in exception handlers
10. **Validators on Base Schemas** - Can break GET responses
11. **Missing Health Check with DB Validation**

---

## PART 3: ERP FRONTEND AUDIT

### CRITICAL Issues (8)

#### 1. Missing Error States in Dashboard
**File:** `frontend/src/app/dashboard/page.tsx`
**Impact:** Silent failures, users don't know if data failed to load

#### 2. Type Mismatches with Backend
**File:** `frontend/src/types/index.ts`
| Field | Backend | Frontend | Issue |
|-------|---------|----------|-------|
| Permission.module | object | string \| object | Confusing |
| Vendor.gstin | gstin | gst_number (alias) | Inconsistent |
| Order.total_amount | total_amount | grand_total | Two names |

#### 3. Missing Cache Invalidation
**Files:** Multiple pages
**Impact:** Refetches all data, resets pagination and filters

#### 4. Broken Navigation Links
- `/dashboard/orders?status=PENDING` - Page doesn't parse URL params
- `/dashboard/finance/fixed-assets` - Links to list, not create form

### HIGH Issues (6)

1. **No Global Error Handler** - Each component implements own error handling
2. **Missing Loading States** - 5+ pages missing skeleton loaders
3. **No Optimistic Updates** - Delete operations cause UI flicker
4. **Missing Stale-While-Revalidate** - All queries use default staleTime: 0
5. **No Retry Logic** - Transient network errors cause immediate failure
6. **Incomplete CRUD Operations** - Edit/delete missing on catalog pages

---

## PART 4: D2C STOREFRONT AUDIT

### CRITICAL Issues (3)

#### 1. Razorpay Test Key Fallback
**File:** `frontend/src/app/(storefront)/checkout/page.tsx`
```typescript
key: paymentOrder.key_id || process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || 'rzp_test_xxx',
// Can expose test mode in production!
```
**Fix:** Remove fallback, throw error if not configured

#### 2. No Cart Validation on Restore
**File:** `frontend/src/lib/storefront/cart-store.ts`
**Impact:** Customers can add out-of-stock items, stale pricing
**Fix:** Validate products on localStorage restore

#### 3. Missing Error Boundaries
**Files:** 8+ pages lack error.tsx
**Impact:** Network failures show raw error messages

### HIGH Issues (7)

1. **7 pages lack metadata/SEO** - Login, Addresses, Wishlist, Cart, etc.
2. **5 pages missing loading skeletons** - Addresses, Wishlist, Partner Products
3. **Broken links** - `/contact` doesn't exist, tracking uses wrong URL pattern
4. **Missing ARIA labels** - Cart drawer, product detail, star ratings
5. **Phone number immutable** - Profile page can't update phone
6. **No password change** - Security risk if compromised
7. **Missing pages** - Contact, FAQ, proper tracking page

### Missing Pages for Complete User Journey

| Page | Path | Priority |
|------|------|----------|
| Contact/Support | `/contact` | HIGH |
| FAQ/Help | `/faq` | MEDIUM |
| Order Tracking | `/track/[orderNumber]` | HIGH |
| Return Initiation | Exists but needs validation | MEDIUM |

---

## PART 5: SECURITY AUDIT

### CRITICAL Issues (2)

#### 1. JWT Tokens in localStorage (XSS Vulnerable)
**File:** `frontend/src/lib/api/client.ts`
**CVSS:** 8.1
**Impact:** Any XSS vulnerability leads to full account compromise
**Fix:** Move to httpOnly cookies

#### 2. Exposed OIDC Token in .env.local
**File:** `frontend/.env.local`
**CVSS:** 9.1
**Impact:** Vercel infrastructure access if committed
**Fix:** Rotate token immediately, use Vercel dashboard secrets

### HIGH Issues (8)

1. **Token Refresh Race Condition** - No timeout, memory leak
2. **No Token Expiration Handling** - Relies only on 401 response
3. **Missing Auth on /api/revalidate** - Hardcoded secret visible in code
4. **Missing Security Headers** - No CSP, X-Frame-Options, HSTS
5. **No Rate Limiting on Login** - Brute force possible
6. **Sensitive Data in Error Messages** - Account enumeration
7. **Weak Cookie Settings** - httpOnly: false on referral cookie
8. **No CAPTCHA on Public Forms** - SMS bombing vector

### Recommended Security Headers

```typescript
// next.config.ts
headers: [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-XSS-Protection', value: '1; mode=block' },
  { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
  { key: 'Content-Security-Policy', value: "default-src 'self'; ..." },
]
```

---

## PART 6: PRIORITIZED ACTION ITEMS

### Week 1 (Critical - Do Immediately)

| Priority | Issue | File | Effort |
|----------|-------|------|--------|
| P0 | Rotate OIDC token | Vercel Dashboard | 10 min |
| P0 | Remove Razorpay test fallback | checkout/page.tsx | 5 min |
| P0 | Move JWT to httpOnly cookies | client.ts | 4 hours |
| P1 | Add security headers | next.config.ts | 30 min |
| P1 | Add transaction rollback | order_service.py | 2 hours |
| P1 | Fix FK CASCADE to RESTRICT | channel.py + migration | 2 hours |

### Week 2 (High Priority)

| Priority | Issue | File | Effort |
|----------|-------|------|--------|
| P1 | Add composite indexes | product.py, order.py | 2 hours |
| P1 | Add missing audit timestamps | 20+ models | 4 hours |
| P1 | Fix N+1 queries | product_service.py | 2 hours |
| P1 | Add rate limiting to login | login/page.tsx | 2 hours |
| P2 | Add error boundaries | All storefront pages | 3 hours |
| P2 | Add global error handler | query-provider.tsx | 1 hour |

### Week 3-4 (Medium Priority)

| Priority | Issue | Scope | Effort |
|----------|-------|-------|--------|
| P2 | Convert JSON to JSONB | 105 columns | 4 hours |
| P2 | Fix timestamps to TIMESTAMPTZ | 485 columns | 4 hours |
| P2 | Add missing metadata/SEO | 7 pages | 2 hours |
| P2 | Add loading skeletons | 5 pages | 2 hours |
| P2 | Create Contact/FAQ pages | New pages | 4 hours |
| P2 | Add CAPTCHA to auth forms | 3 forms | 2 hours |

### Ongoing Maintenance

- Audit all new endpoints for permission checks
- Add missing back_populates to relationships
- Remove console.log from production
- Monitor unused indexes for cleanup
- Review pricing data source of truth

---

## PART 7: DATABASE MIGRATION SCRIPTS

### Convert JSON to JSONB

```sql
-- High-impact columns first
ALTER TABLE orders ALTER COLUMN billing_address TYPE JSONB USING billing_address::JSONB;
ALTER TABLE orders ALTER COLUMN shipping_address TYPE JSONB USING shipping_address::JSONB;
ALTER TABLE promotions ALTER COLUMN applicable_products TYPE JSONB USING applicable_products::JSONB;
-- ... (105 total columns)
```

### Convert Timestamps to TIMESTAMPTZ

```sql
-- Create migration for all 485 columns
ALTER TABLE allocation_rules ALTER COLUMN created_at TYPE TIMESTAMPTZ;
ALTER TABLE allocation_rules ALTER COLUMN updated_at TYPE TIMESTAMPTZ;
-- ... (485 total columns)
```

### Add Missing Audit Columns

```sql
ALTER TABLE amc_contracts ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE amc_contracts ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE amc_plans ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE amc_plans ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
-- ... (20+ tables)
```

---

## Conclusion

The Aquapurite ERP system has a **solid architectural foundation** with 204 well-structured tables, proper relationship definitions, and consistent naming conventions. The main areas requiring immediate attention are:

1. **Security** - JWT storage, security headers, rate limiting
2. **Data Types** - JSON→JSONB, Timestamp→TIMESTAMPTZ migrations
3. **Error Handling** - Transaction rollbacks, error boundaries
4. **Performance** - Composite indexes, N+1 query fixes

Addressing the critical issues first will significantly improve system reliability and security. The medium-priority items will enhance maintainability and user experience over time.

**Estimated Total Effort:** 80-100 hours for all identified issues
**Recommended Timeline:** 4 weeks with dedicated resources

---

*Report generated by Claude Code Comprehensive Audit System*
