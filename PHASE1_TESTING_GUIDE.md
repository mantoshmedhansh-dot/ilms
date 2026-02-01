# PHASE 1 TESTING GUIDE
**Multi-Tenant Infrastructure Testing with Supabase**

Date: 2026-02-01
Status: Ready for testing

---

## OVERVIEW

This guide walks you through testing Phase 1 locally with your Supabase database.

**What we're testing:**
- Multi-tenant schema creation in Supabase public schema
- 10 modules and 4 pricing plans seeded
- Test tenant creation and subscription management
- Tenant middleware (extracts tenant from request)
- Module access control decorator (@require_module)

---

## PREREQUISITES

- [ ] Supabase account with database access
- [ ] Supabase connection string ready
- [ ] Python virtual environment activated
- [ ] Backend dependencies installed

---

## STEP 1: Run SQL Scripts in Supabase

### 1.1 Open Supabase SQL Editor

1. Go to https://supabase.com/dashboard
2. Select your project
3. Click "SQL Editor" in left sidebar
4. Click "New query"

### 1.2 Run Phase 1 Setup Script

1. Open file: `scripts/phase1_setup_supabase.sql`
2. Copy entire contents
3. Paste into Supabase SQL Editor
4. Click "Run" button

**Expected output:**
```
SUCCESS
Query returned successfully
```

**What this creates:**
- 7 tables in public schema: tenants, modules, plans, tenant_subscriptions, feature_flags, billing_history, usage_metrics
- 10 module records
- 4 pricing plan records

### 1.3 Run Test Tenant Creation Script

1. Open file: `scripts/phase1_test_tenant.sql`
2. Copy entire contents
3. Paste into Supabase SQL Editor
4. Click "Run" button

**Expected output:**
```
status: Test Tenant Created
id: <UUID>
name: Test Company
subdomain: testcompany
database_schema: tenant_testcompany
plan_name: Starter
```

**What this creates:**
- 1 test tenant: "Test Company" (subdomain: testcompany)
- 3 active subscriptions: system_admin, oms_fulfillment, d2c_storefront

### 1.4 Copy Tenant ID for Testing

From the last query result, copy the `tenant_id` (UUID). You'll need this for API testing.

Example:
```
tenant_id: 550e8400-e29b-41d4-a716-446655440000
```

**Save this ID - you'll use it in the next steps!**

---

## STEP 2: Verify Database Structure

### 2.1 Check Tables Created

In Supabase SQL Editor, run:

```sql
\dt public.*;
```

**Expected output:**
```
public | tenants
public | modules
public | plans
public | tenant_subscriptions
public | feature_flags
public | billing_history
public | usage_metrics
```

### 2.2 Check Modules Seeded

```sql
SELECT code, name, price_monthly
FROM public.modules
ORDER BY display_order;
```

**Expected: 10 rows**
```
oms_fulfillment     | OMS, WMS & Fulfillment           | 12999
procurement         | Procurement (P2P)                | 6999
finance             | Finance & Accounting             | 9999
crm_service         | CRM & Service Management         | 6999
sales_distribution  | Multi-Channel Sales & Distribution | 7999
hrms                | HRMS                             | 4999
d2c_storefront      | D2C E-Commerce Storefront        | 3999
scm_ai              | Supply Chain & AI Insights       | 8999
marketing           | Marketing & Promotions           | 3999
system_admin        | System Administration            | 2999
```

### 2.3 Check Plans Seeded

```sql
SELECT slug, name, price_inr
FROM public.plans
ORDER BY display_order;
```

**Expected: 4 rows**
```
starter       | Starter       | 19999
growth        | Growth        | 39999
professional  | Professional  | 59999
enterprise    | Enterprise    | 79999
```

### 2.4 Check Test Tenant Subscriptions

```sql
SELECT
    t.name as tenant,
    m.code as module,
    ts.status
FROM public.tenant_subscriptions ts
JOIN public.tenants t ON ts.tenant_id = t.id
JOIN public.modules m ON ts.module_id = m.id
WHERE t.subdomain = 'testcompany';
```

**Expected: 3 rows**
```
Test Company | system_admin      | active
Test Company | oms_fulfillment   | active
Test Company | d2c_storefront    | active
```

---

## STEP 3: Update Backend Configuration

### 3.1 Ensure .env is Using Supabase

Check file: `/Users/mantosh/Desktop/ilms.ai/.env`

Ensure it has:
```env
DATABASE_URL=postgresql+psycopg://postgres:Aquapurite2026@db.aavjhutqzwusgdwrczds.supabase.co:6543/postgres
```

### 3.2 Register Tenant Middleware

Check if middleware is registered in `app/main.py`:

```python
from app.middleware.tenant import tenant_middleware

# Add tenant middleware (should be near other middleware)
app.middleware("http")(tenant_middleware)
```

**If not present, add it after CORS middleware.**

---

## STEP 4: Test Backend Locally

### 4.1 Start Backend Server

```bash
cd "/Users/mantosh/Desktop/ilms.ai"
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 4.2 Test Health Endpoint

In a new terminal:

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{"status": "healthy"}
```

---

## STEP 5: Create Test Endpoints

Create a test file to verify module access control:

**File:** `app/api/v1/endpoints/test_modules.py`

```python
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.module_decorators import require_module, get_tenant_enabled_modules
from app.database import get_public_session

router = APIRouter()

@router.get("/test/modules/enabled")
async def get_enabled_modules(
    request: Request,
    db: AsyncSession = Depends(get_public_session)
):
    """Get list of enabled modules for current tenant"""
    tenant_id = request.state.tenant_id
    modules = await get_tenant_enabled_modules(db, tenant_id)
    return {
        "tenant": request.state.tenant.name,
        "tenant_id": tenant_id,
        "enabled_modules": modules
    }

@router.get("/test/modules/oms-allowed")
@require_module("oms_fulfillment")
async def test_oms_module(request: Request):
    """Test endpoint - requires oms_fulfillment module (should succeed)"""
    return {
        "message": "✅ You have access to OMS module!",
        "tenant": request.state.tenant.name
    }

@router.get("/test/modules/finance-blocked")
@require_module("finance")
async def test_finance_module(request: Request):
    """Test endpoint - requires finance module (should fail for Starter plan)"""
    return {
        "message": "✅ You have access to Finance module!",
        "tenant": request.state.tenant.name
    }
```

**Register the router in `app/api/v1/router.py`:**

```python
from app.api.v1.endpoints import test_modules

# Add to api_router
api_router.include_router(test_modules.router, tags=["Testing"])
```

Restart the backend server after adding this.

---

## STEP 6: Test Module Access Control

Use the `tenant_id` you copied from Step 1.4.

### Test 1: Get Enabled Modules (Should succeed)

```bash
curl -X GET http://localhost:8000/api/test/modules/enabled \
  -H "X-Tenant-ID: <YOUR_TENANT_ID_HERE>"
```

**Expected response:**
```json
{
  "tenant": "Test Company",
  "tenant_id": "<YOUR_TENANT_ID>",
  "enabled_modules": ["system_admin", "oms_fulfillment", "d2c_storefront"]
}
```

### Test 2: Access OMS Module (Should succeed)

```bash
curl -X GET http://localhost:8000/api/test/modules/oms-allowed \
  -H "X-Tenant-ID: <YOUR_TENANT_ID_HERE>"
```

**Expected response:**
```json
{
  "message": "✅ You have access to OMS module!",
  "tenant": "Test Company"
}
```

### Test 3: Access Finance Module (Should fail with 403)

```bash
curl -X GET http://localhost:8000/api/test/modules/finance-blocked \
  -H "X-Tenant-ID: <YOUR_TENANT_ID_HERE>"
```

**Expected response:**
```json
{
  "detail": "Module 'finance' is not enabled for your account. Please upgrade your subscription."
}
```

**HTTP Status:** 403 Forbidden

### Test 4: Access Without Tenant Header (Should fail with 404)

```bash
curl -X GET http://localhost:8000/api/test/modules/enabled
```

**Expected response:**
```json
{
  "detail": "Tenant not found. Please check your subdomain or login credentials."
}
```

**HTTP Status:** 404 Not Found

---

## STEP 7: Test Subdomain-Based Tenant Resolution

If you want to test subdomain-based tenant identification, you can modify your `/etc/hosts` file:

```bash
# Add this line to /etc/hosts
127.0.0.1 testcompany.localhost
```

Then access:
```bash
curl http://testcompany.localhost:8000/api/test/modules/enabled
```

**Expected:** Should work without X-Tenant-ID header

---

## PHASE 1 TESTING CHECKLIST

Mark each item as you complete it:

### Database Setup
- [ ] Ran `phase1_setup_supabase.sql` in Supabase SQL Editor
- [ ] Verified 7 tables created in public schema
- [ ] Verified 10 modules seeded
- [ ] Verified 4 plans seeded
- [ ] Ran `phase1_test_tenant.sql`
- [ ] Verified test tenant created
- [ ] Copied tenant_id for testing

### Backend Configuration
- [ ] `.env` points to Supabase database
- [ ] Tenant middleware registered in `app/main.py`
- [ ] Test endpoints created in `test_modules.py`
- [ ] Test router registered in `router.py`

### Local Testing
- [ ] Backend starts without errors
- [ ] Health endpoint responds
- [ ] Test 1: Get enabled modules (succeeds)
- [ ] Test 2: Access OMS module (succeeds)
- [ ] Test 3: Access Finance module (403 blocked)
- [ ] Test 4: Access without tenant header (404)

### Code Verification
- [ ] Models in `app/models/tenant.py` match Supabase schema
- [ ] Middleware extracts tenant correctly
- [ ] Module decorator blocks unauthorized access
- [ ] Module access cache working (check logs for "cache hit" after 2nd request)

---

## TROUBLESHOOTING

### Issue: "Table already exists" error

**Solution:** Tables already created. Skip to Step 1.3 (create test tenant).

### Issue: "Tenant not found" error

**Solution:**
1. Verify tenant exists: `SELECT * FROM public.tenants WHERE subdomain = 'testcompany';`
2. Check X-Tenant-ID header is correct UUID format
3. Check tenant status is 'active'

### Issue: Backend won't start - import errors

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check if all models import correctly
python -c "from app.models import tenant"
```

### Issue: Module access always fails

**Solution:**
1. Check subscriptions: `SELECT * FROM public.tenant_subscriptions WHERE tenant_id = '<YOUR_ID>';`
2. Verify module status is 'active'
3. Check middleware is setting `request.state.tenant`

---

## SUCCESS CRITERIA

**Phase 1 is successfully tested when:**

1. ✅ All 7 tables exist in Supabase public schema
2. ✅ 10 modules and 4 plans are seeded
3. ✅ Test tenant created with 3 active subscriptions
4. ✅ Backend starts without errors
5. ✅ Tenant middleware extracts tenant from X-Tenant-ID header
6. ✅ Module access control allows access to subscribed modules
7. ✅ Module access control blocks access to non-subscribed modules
8. ✅ All 4 API tests pass

---

## NEXT STEPS AFTER SUCCESSFUL TESTING

Once all tests pass:

1. Document test results
2. Get user approval
3. Commit Phase 1 code to git
4. Move to Phase 2: Add @require_module decorators to existing endpoints

---

**Ready to proceed?** Start with Step 1 and work through each step sequentially.

**Questions?** Check the troubleshooting section or review PHASE1_COMPLETED.md for architecture details.
