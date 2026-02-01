# Coding Standards Audit Report - Aquapurite ERP

**Date:** 2026-01-22
**Scope:** Full ERP Panel (Backend + Frontend) and D2C Storefront
**Source of Truth:** Supabase Production Database + CLAUDE.md Coding Standards
**Status:** FIXES APPLIED

---

## Fixes Applied (2026-01-22)

| Issue | File | Fix Applied |
|-------|------|-------------|
| ProductBase validators | `app/schemas/product.py` | Moved to ProductCreate/ProductUpdate |
| FinancialPeriodBase validator | `app/schemas/accounting.py` | Moved to FinancialPeriodCreate |
| Lowercase status "paid" | `app/jobs/order_jobs.py` | Changed to "PAID" |
| Lowercase status "failed" | `app/jobs/order_jobs.py` | Changed to "FAILED" |
| Lowercase status "completed" | `app/services/service_request_service.py` | Changed to "COMPLETED" |
| Lowercase status "paid" | `app/api/v1/endpoints/amc.py` | Changed to "PAID" |
| Lowercase status "active"/"expired" | `app/api/v1/endpoints/serialization.py` | Changed to "ACTIVE"/"EXPIRED" |

---

## Executive Summary

| Category | Critical | High | Medium | Total |
|----------|----------|------|--------|-------|
| Validators on Base Schemas | 6 | - | - | 6 |
| Status/Enum Case Issues | 4 | 27+ | - | 31+ |
| Schema-Service Field Mismatch | 2 | - | - | 2 |
| Frontend-Backend Field Names | - | 4 | - | 4 |
| **TOTAL** | **12** | **31+** | **0** | **43+** |

---

## Category 1: Validators on Base Schemas (CRITICAL - Rule 2 Violations)

**Impact:** 500 errors on GET requests when existing database data doesn't match validation rules.

### Issue 1.1: ProductBase - selling_price validator
**File:** `app/schemas/product.py:179-186`
```python
# VIOLATION: Validator on Base schema
class ProductBase(BaseModel):
    @field_validator('selling_price')
    def validate_selling_price(cls, v, info):
        mrp = info.data.get('mrp')
        if mrp and v and v > mrp:
            raise ValueError('Selling price cannot exceed MRP')
        return v
```
**Fix:** Move to `ProductCreate` and `ProductUpdate` only.

---

### Issue 1.2: ProductBase - model_code validator
**File:** `app/schemas/product.py:188-194`
```python
# VIOLATION: Validator on Base schema
class ProductBase(BaseModel):
    @field_validator('model_code')
    def validate_model_code(cls, v):
        if v and len(v) != 3:
            raise ValueError('Model code must be exactly 3 characters')
        return v
```
**Fix:** Move to `ProductCreate` and `ProductUpdate` only.

---

### Issue 1.3: FinancialPeriodBase - end_date validator
**File:** `app/schemas/accounting.py:125-130`
```python
# VIOLATION: Validator on Base schema
class FinancialPeriodBase(BaseModel):
    @field_validator('end_date')
    def validate_end_date(cls, v, info):
        start_date = info.data.get('start_date')
        if start_date and v and v <= start_date:
            raise ValueError('End date must be after start date')
        return v
```
**Fix:** Move to `FinancialPeriodCreate` only.

---

### Issue 1.4: JournalEntryCreate - lines balance validator
**File:** `app/schemas/accounting.py:263-276`
```python
# LESS CRITICAL: On Create schema but overly strict
class JournalEntryCreate(BaseModel):
    @model_validator(mode='after')
    def validate_lines_balance(self):
        # May break if lines don't balance due to rounding
```
**Review:** Ensure rounding tolerance is acceptable.

---

### Issue 1.5: RoleBase - level validator
**File:** `app/schemas/role.py:21-29`
```python
# VIOLATION: Field(..., ge=0) constraint on Base schema
class RoleBase(BaseModel):
    level: int = Field(..., ge=0, description="Role hierarchy level")
```
**Fix:** Move `ge=0` to `RoleCreate` only. Use plain `int` in Base.

---

### Issue 1.6: Commission schemas - gt=0 constraints
**File:** `app/schemas/commission.py` (multiple locations)
```python
# VIOLATION: Field constraints on Base schemas
class CommissionSlabBase(BaseModel):
    min_amount: Decimal = Field(..., gt=0)  # Breaks if DB has 0
    max_amount: Decimal = Field(..., gt=0)  # Breaks if DB has 0
    rate: Decimal = Field(..., gt=0, le=100)
```
**Fix:** Remove `gt=0` from Base, add to Create schemas.

---

## Category 2: Status/Enum Case Issues (CRITICAL - Rule 4 Violations)

**Impact:** Logic failures, wrong counts, silent comparison failures.

### Issue 2.1: AMC Schema - lowercase default
**File:** `app/schemas/amc.py:74`
```python
# VIOLATION: lowercase status default
payment_status: str = Field(default="pending", ...)  # Should be "PENDING"
```

### Issue 2.2: AMC Service - lowercase assignment
**File:** `app/services/amc_service.py:555`
```python
# VIOLATION: lowercase status assignment
amc.payment_status = "paid"  # Should be "PAID"
```

### Issue 2.3: Service Request Service - lowercase status
**File:** `app/services/service_request_service.py:323`
```python
# VIOLATION: lowercase status
service_request.status = "completed"  # Should be "COMPLETED"
```

### Issue 2.4: Order Jobs - lowercase comparisons
**File:** `app/jobs/order_jobs.py:84-98`
```python
# VIOLATION: lowercase status comparisons
if order.status == "pending":  # DB has "PENDING"
    ...
if order.payment_status == "paid":  # DB has "PAID"
    ...
```

### Additional Status Issues (27+ occurrences)
Run this command to find all:
```bash
grep -rn "= [\"']\\(pending\\|paid\\|completed\\|active\\|inactive\\)[\"']" app/
```

---

## Category 3: Schema-Service Field Mismatch (CRITICAL - Rule 1 & 6 Violations)

**Impact:** Fields returned by services silently dropped in API responses.

### Issue 3.1: OrderSummary - type mismatch
**File:** `app/schemas/order.py:226-241`
```python
class OrderSummary(BaseModel):
    # Service returns float for percentage changes
    orders_change: float = 0  # OK
    revenue_change: float = 0  # OK
    customers_change: float = 0  # OK

    # BUT service may return Decimal for revenue
    total_revenue: Decimal  # Mismatch if service returns float
```
**Status:** Partially fixed. Verify service return types match.

### Issue 3.2: CustomerResponse - missing region_id
**File:** `app/schemas/customer.py`
```python
# Service returns region_id but schema doesn't include it
class CustomerResponse(BaseModel):
    # Missing: region_id: Optional[UUID] = None
```
**Fix:** Add `region_id` field to CustomerResponse.

---

## Category 4: Frontend-Backend Field Name Mismatches (HIGH - Rule 3 Violations)

**Impact:** Frontend shows wrong/null values due to field name differences.

### Issue 4.1: GST Number inconsistency
**Backend:** Some schemas use `gstin`, others use `gst_number`
**Frontend:** Expects `gst_number` in some places, `gstin` in others
```typescript
// Multiple workarounds in frontend
const gstNumber = data.gstin || data.gst_number || '';
```
**Fix:** Standardize on `gstin` everywhere with alias for backwards compatibility.

### Issue 4.2: Missing Invoice type in frontend
**File:** `frontend/src/types/index.ts`
```typescript
// Invoice type not defined - frontend may be missing fields
export interface Invoice {
  // Need to verify matches InvoiceResponse schema
}
```

### Issue 4.3: Dashboard API multiple fallback pattern
**File:** `frontend/src/lib/api/dashboard.ts`
```typescript
// BAD: Multiple fallbacks indicate field name uncertainty
return {
  total_orders: ordersData.total || ordersData.total_orders || 0,
  total_customers: ordersData.customers || ordersData.total_customers || 0,
};
```
**Fix:** Use exact backend field names only.

### Issue 4.4: Product computed field aliases
**Files:** `app/schemas/product.py`
```python
# ProductDocument and ProductSpecification may be missing computed aliases
# that frontend expects
```

---

## Action Plan

### Phase 1: Critical Fixes (Immediate)

| # | Issue | File | Action |
|---|-------|------|--------|
| 1 | ProductBase validators | `app/schemas/product.py` | Move to Create/Update |
| 2 | FinancialPeriodBase validator | `app/schemas/accounting.py` | Move to Create only |
| 3 | RoleBase level constraint | `app/schemas/role.py` | Remove ge=0 from Base |
| 4 | CommissionSlabBase constraints | `app/schemas/commission.py` | Remove gt=0 from Base |
| 5 | AMC lowercase statuses | `app/schemas/amc.py`, `app/services/amc_service.py` | Change to UPPERCASE |
| 6 | Service request lowercase | `app/services/service_request_service.py` | Change to UPPERCASE |
| 7 | Order jobs lowercase | `app/jobs/order_jobs.py` | Change to UPPERCASE |

### Phase 2: High Priority Fixes

| # | Issue | File | Action |
|---|-------|------|--------|
| 8 | CustomerResponse region_id | `app/schemas/customer.py` | Add field |
| 9 | Dashboard API fallbacks | `frontend/src/lib/api/dashboard.ts` | Remove workarounds |
| 10 | GST field standardization | Multiple files | Standardize on `gstin` |

### Phase 3: Verification

| # | Check | Command |
|---|-------|---------|
| 1 | Find all lowercase status assignments | `grep -rn "= [\"']\\(pending\\|paid\\)[\"']" app/` |
| 2 | Find all validators on Base schemas | `grep -rn "@field_validator" app/schemas/ \| grep -A5 "Base"` |
| 3 | Verify build passes | `cd frontend && pnpm build` |
| 4 | Test locally | `uvicorn app.main:app --port 8000` |

---

## Files to Modify

### Backend
1. `app/schemas/product.py` - Move validators
2. `app/schemas/accounting.py` - Move validator
3. `app/schemas/role.py` - Remove constraint
4. `app/schemas/commission.py` - Remove constraints
5. `app/schemas/amc.py` - Fix status default
6. `app/schemas/customer.py` - Add region_id
7. `app/services/amc_service.py` - Fix status assignment
8. `app/services/service_request_service.py` - Fix status
9. `app/jobs/order_jobs.py` - Fix status comparisons

### Frontend
1. `frontend/src/lib/api/dashboard.ts` - Remove fallback pattern
2. `frontend/src/types/index.ts` - Add/verify Invoice type

---

## Deployment Checklist (Post-Fix)

- [ ] Run `pnpm build` in frontend - must pass
- [ ] Start local backend: `uvicorn app.main:app --port 8000`
- [ ] Start local frontend: `cd frontend && pnpm dev`
- [ ] Test dashboard page loads
- [ ] Test order listing page
- [ ] Test customer listing page
- [ ] Push to production
- [ ] Verify production health endpoint
- [ ] Verify production dashboard

---

*Report generated by Claude Code audit on 2026-01-22*
