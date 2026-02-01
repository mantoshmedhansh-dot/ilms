# PHASE 2C: Multi-Module Endpoint Handling

**Status:** Planning
**Date:** 2026-02-01

---

## OVERVIEW

Four endpoint files serve multiple modules and need special handling for `@require_module()` decorators:

| File | Modules | Why Multi-Module? |
|------|---------|-------------------|
| `products.py` | oms_fulfillment, d2c_storefront, sales_distribution | Product catalog shared across inventory, storefront, and sales channels |
| `categories.py` | oms_fulfillment, d2c_storefront | Category hierarchy used in both warehouse and customer-facing apps |
| `brands.py` | oms_fulfillment, d2c_storefront | Brand management for both internal and public-facing systems |
| `dashboard_charts.py` | system_admin (view all modules) | Dashboard shows data from all enabled modules |

---

## APPROACH OPTIONS

### Option 1: Use Primary Module Only (RECOMMENDED)
**Simplest approach - assign each file to its primary module.**

```python
# products.py
@router.get("/products")
@require_module("oms_fulfillment")  # Primary module
async def list_products(...):
    # All users with oms_fulfillment can access
    pass
```

**Pros:**
- Simple implementation
- No code changes needed (already done in Phase 2A)
- Clear ownership of resources

**Cons:**
- D2C storefront users can't access products without oms_fulfillment
- Sales channel users can't access products without oms_fulfillment

**Mitigation:**
- Storefront has public product endpoints at `/api/v1/storefront/products` (no auth)
- For authenticated access, users need the primary module

---

### Option 2: Remove Decorators (Public Access)
**Make these endpoints accessible to all authenticated users.**

```python
# products.py
@router.get("/products")
# No @require_module decorator
async def list_products(current_user: CurrentUser, ...):
    # Any authenticated user can access
    # But still requires valid tenant
    pass
```

**Pros:**
- Maximum flexibility
- No module restrictions

**Cons:**
- Defeats purpose of module-based access control
- All tenants can access product endpoints even if they don't have any related modules

---

### Option 3: Custom Multi-Module Decorator
**Create new decorator that checks if tenant has ANY of the specified modules.**

```python
# app/core/module_decorators.py
def require_any_module(*module_codes: str):
    """Require tenant to have ANY of the specified modules."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get tenant from request
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            tenant = request.state.tenant

            # Check if tenant has ANY of the modules
            for module_code in module_codes:
                has_access = await check_module_access(db, tenant.id, module_code)
                if has_access:
                    return await func(*args, **kwargs)

            # None of the modules are enabled
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. This endpoint requires one of: {', '.join(module_codes)}"
            )
        return wrapper
    return decorator

# products.py
@router.get("/products")
@require_any_module("oms_fulfillment", "d2c_storefront", "sales_distribution")
async def list_products(...):
    # User needs ANY of these modules
    pass
```

**Pros:**
- Most flexible
- Allows logical OR access control
- Matches business reality (products used by multiple modules)

**Cons:**
- Additional code to write and test
- More complex to understand
- Need to maintain module lists for each endpoint

---

### Option 4: Endpoint Duplication
**Create separate endpoints for each module.**

```python
# products.py - OMS endpoints
@router.get("/products")
@require_module("oms_fulfillment")
async def list_products_oms(...):
    # OMS users
    pass

# products.py - D2C endpoints
@router.get("/d2c/products")
@require_module("d2c_storefront")
async def list_products_d2c(...):
    # D2C users (internal implementation can call same service)
    pass

# products.py - Sales endpoints
@router.get("/sales/products")
@require_module("sales_distribution")
async def list_products_sales(...):
    # Sales users
    pass
```

**Pros:**
- Clear module separation
- Can customize response for each module
- Granular permissions

**Cons:**
- Code duplication
- Maintenance overhead
- API becomes more complex

---

## RECOMMENDATION: Option 1 (Primary Module)

**Use the existing Phase 2A implementation with primary modules.**

### Rationale:

1. **Already Implemented** - Phase 2A assigned primary modules:
   - products.py → oms_fulfillment
   - categories.py → oms_fulfillment
   - brands.py → oms_fulfillment
   - dashboard_charts.py → system_admin

2. **Storefront Has Public Endpoints** - D2C customers access products via:
   - `/api/v1/storefront/products` (public, no auth)
   - No module decorator needed

3. **Subscription Model Makes Sense** - If a tenant subscribes to:
   - OMS/Fulfillment → They manage inventory, so they get product access
   - D2C Storefront → They get public storefront, admin access requires OMS
   - Sales/Distribution → Requires OMS as a dependency (can't sell without inventory)

4. **Module Dependencies** - Can enforce logical dependencies:
   ```
   OMS/Fulfillment (base)
     ├── D2C Storefront (requires OMS)
     ├── Sales/Distribution (requires OMS)
     └── Procurement (requires OMS)
   ```

### Implementation:

**NO CHANGES NEEDED** - Phase 2A implementation is correct!

Files already have:
```python
# products.py, categories.py, brands.py
@require_module("oms_fulfillment")

# dashboard_charts.py
@require_module("system_admin")
```

---

## ALTERNATIVE: Option 3 for Future Enhancement

If business requirements change and multi-module access is needed:

### Phase 3 Task: Implement `@require_any_module()` decorator

**When to use:**
- Product endpoints need to be accessible from D2C, OMS, AND Sales
- Dashboard charts need to show data from any enabled module
- Reports need cross-module access

**Example Use Case:**
```python
# dashboard_charts.py
@router.get("/charts/sales")
@require_any_module("oms_fulfillment", "sales_distribution", "finance")
async def get_sales_chart(...):
    # Show sales data if tenant has any of these modules
    tenant = request.state.tenant

    # Customize response based on enabled modules
    modules = await get_enabled_modules(tenant.id)
    if "finance" in modules:
        # Include financial metrics
        pass
    if "oms_fulfillment" in modules:
        # Include fulfillment metrics
        pass
```

---

## DECISION

**✅ PROCEED WITH OPTION 1 (Primary Module)**

**No changes needed for Phase 2C.**

- products.py, categories.py, brands.py → Require "oms_fulfillment"
- dashboard_charts.py → Require "system_admin"

**Rationale:**
- Simplest approach
- Already implemented in Phase 2A
- Matches logical module dependencies
- Storefront has separate public endpoints

**Future Enhancement:**
- If multi-module access is needed, implement `@require_any_module()` in Phase 3+

---

## PHASE 2C STATUS: ✅ COMPLETE (No Action Required)

**Multi-module endpoints are correctly handled using primary module approach.**

**Proceed to Phase 2D: Public Endpoints**

---

*Generated: 2026-02-01*
