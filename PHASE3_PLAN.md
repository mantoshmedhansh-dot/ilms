# PHASE 3: Tenant Onboarding & Management
**Status:** Planning
**Date:** 2026-02-01

---

## OVERVIEW

Phase 3 implements the tenant lifecycle management system, building on the multi-tenant infrastructure from Phase 1 and module-based access control from Phase 2.

**Goal:** Allow new customers to sign up, select modules, and get instant access to their ERP system.

---

## SCOPE

### Core Features

1. **Tenant Registration**
   - Public signup API (no auth required)
   - Company details collection
   - Subdomain validation and reservation
   - Initial admin user creation

2. **Module Selection & Subscription**
   - Display available modules with pricing
   - Allow module selection during signup
   - Create tenant_subscriptions records
   - Calculate total subscription cost

3. **Database Schema Creation**
   - Create `tenant_{subdomain}` schema per tenant
   - Run migrations on tenant schema
   - Create default data (roles, permissions, settings)
   - Seed initial admin user in tenant schema

4. **Startup Function Optimization**
   - Make `auto_seed_admin()` tenant-aware
   - Optimize `init_db()` for production
   - Handle tenant schema switching

5. **Tenant Management API**
   - List all tenants (super admin only)
   - View tenant details
   - Update tenant settings
   - Enable/disable modules
   - Suspend/reactivate tenants

---

## PHASE 3 SUB-TASKS

### Phase 3A: Tenant Registration API ✅ TO DO
**Goal:** Allow new customers to sign up and create their tenant account

**Endpoints:**
```python
POST /api/v1/onboarding/register
  - Input: company name, subdomain, admin email, admin password, selected modules
  - Output: tenant_id, access tokens, tenant details

POST /api/v1/onboarding/check-subdomain
  - Input: subdomain
  - Output: {available: true/false}

GET /api/v1/onboarding/modules
  - Output: List of available modules with pricing
```

**Tasks:**
1. Create `app/schemas/onboarding.py` - Pydantic schemas
2. Create `app/services/tenant_onboarding_service.py` - Business logic
3. Create `app/api/v1/endpoints/onboarding.py` - API endpoints
4. Add validation for subdomain (alphanumeric, no special chars, not reserved)
5. Check for duplicate subdomains
6. Calculate subscription total
7. Create tenant record
8. Create initial admin user
9. Return JWT tokens for immediate login

---

### Phase 3B: Tenant Schema Creation ✅ TO DO
**Goal:** Automatically create database schema for each new tenant

**Flow:**
```
1. Tenant registers → tenant record created in public.tenants
2. Trigger schema creation → CREATE SCHEMA tenant_{subdomain}
3. Run migrations on tenant schema → Create all ERP tables
4. Seed default data → Roles, permissions, settings
5. Seed admin user → First user in tenant schema
6. Mark tenant as active
```

**Tasks:**
1. Create `scripts/create_tenant_schema.py` - Schema creation script
2. Implement `app/services/tenant_schema_service.py`
3. Add `create_tenant_schema()` function
4. Add `seed_tenant_defaults()` function
5. Add `seed_tenant_admin()` function
6. Integrate with onboarding flow
7. Handle errors (rollback on failure)
8. Add schema migration tracking

**Database Operations:**
```sql
-- Create schema
CREATE SCHEMA tenant_companyabc;

-- Run migrations (all tables from app/models)
-- This will create users, roles, products, orders, etc. in tenant schema

-- Seed defaults
INSERT INTO tenant_companyabc.roles (name, code, level, is_system)
VALUES ('Super Admin', 'SUPER_ADMIN', 'SUPER_ADMIN', true);

-- Seed admin user
INSERT INTO tenant_companyabc.users (email, password_hash, first_name, ...)
VALUES ('admin@company.com', '$2b$...', 'Admin', ...);
```

---

### Phase 3C: Module Management API ✅ TO DO
**Goal:** Allow tenants to upgrade/downgrade module subscriptions

**Endpoints:**
```python
GET /api/v1/modules/available
  - List all available modules (authenticated user)

GET /api/v1/modules/enabled
  - List enabled modules for current tenant

POST /api/v1/modules/subscribe
  - Subscribe to new module
  - Input: module_code, billing_cycle
  - Creates tenant_subscription record

POST /api/v1/modules/unsubscribe
  - Cancel module subscription
  - Input: module_code
  - Marks subscription as inactive

GET /api/v1/modules/pricing
  - Get pricing for all modules and plans
```

**Tasks:**
1. Create `app/api/v1/endpoints/modules.py`
2. Implement subscription logic
3. Handle billing cycle (monthly/yearly)
4. Calculate prorated charges
5. Update module access cache
6. Send confirmation emails

---

### Phase 3D: Tenant Admin Dashboard API ✅ TO DO
**Goal:** Super admin endpoints to manage all tenants

**Endpoints:**
```python
GET /api/v1/admin/tenants
  - List all tenants (super admin only)
  - Filter by status, plan, created date

GET /api/v1/admin/tenants/{tenant_id}
  - Get tenant details

PUT /api/v1/admin/tenants/{tenant_id}
  - Update tenant settings

POST /api/v1/admin/tenants/{tenant_id}/suspend
  - Suspend tenant account

POST /api/v1/admin/tenants/{tenant_id}/reactivate
  - Reactivate suspended tenant

GET /api/v1/admin/stats
  - Platform statistics (total tenants, MRR, module usage)
```

**Tasks:**
1. Create `app/api/v1/endpoints/admin/tenants.py`
2. Add super admin role check
3. Implement CRUD operations
4. Add tenant search/filter
5. Add billing dashboard
6. Add usage analytics

---

### Phase 3E: Startup Function Fixes ✅ TO DO
**Goal:** Re-enable and optimize startup functions disabled in Phase 2

**Current State:**
```python
# app/main.py - TEMPORARILY DISABLED
# await auto_seed_admin()
# await auto_link_vendors_to_supplier_codes()
# await init_db()
```

**Fixes Needed:**

1. **`auto_seed_admin()` - Make Tenant-Aware**
   ```python
   async def auto_seed_admin():
       # OLD: Check if ANY users exist in database
       # NEW: Check if admin exists in PUBLIC schema for super admin
       #      OR run per-tenant during schema creation

       # Option 1: Only create super admin in public schema
       # Option 2: Skip this function (admin created during onboarding)
   ```

2. **`init_db()` - Optimize for Production**
   ```python
   async def init_db():
       # OLD: Create ALL tables (slow with 200+ tables)
       # NEW: Skip if tables exist (they do in production)

       # Option 1: Check if tables exist first
       # Option 2: Only create multi-tenant tables (public.tenants, etc.)
       # Option 3: Skip entirely in production (use migrations)
   ```

3. **`auto_link_vendors_to_supplier_codes()` - Tenant-Aware**
   ```python
   async def auto_link_vendors_to_supplier_codes():
       # OLD: Links vendors in default schema
       # NEW: Should run per-tenant or be removed

       # Recommendation: Remove or make tenant-specific
   ```

**Decision:**
- `auto_seed_admin()` → Create super admin ONLY in public schema (for platform admin)
- `init_db()` → Skip in production (tables already exist)
- `auto_link_vendors_to_supplier_codes()` → Remove (tenant-specific, not global)

---

## ARCHITECTURE

### Multi-Tenant Database Schema

```
PostgreSQL Database (Supabase)
│
├── public (schema)
│   ├── tenants                    ← All tenant records
│   ├── modules                    ← Available ERP modules
│   ├── plans                      ← Pricing plans
│   ├── tenant_subscriptions       ← Module subscriptions
│   ├── feature_flags              ← Feature toggles
│   ├── billing_history            ← Invoices
│   ├── usage_metrics              ← Analytics
│   └── platform_admins            ← Super admin users (NEW)
│
├── tenant_testcompany (schema)
│   ├── users
│   ├── roles
│   ├── products
│   ├── orders
│   ├── customers
│   └── ... (all ERP tables)
│
├── tenant_companyabc (schema)
│   ├── users
│   ├── roles
│   └── ... (all ERP tables)
│
└── tenant_xyz (schema)
    └── ... (all ERP tables)
```

---

## DATA FLOW

### New Tenant Onboarding

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER SIGNUP                                              │
│    POST /api/v1/onboarding/register                         │
│    {                                                         │
│      company: "ABC Corp",                                   │
│      subdomain: "abccorp",                                  │
│      admin_email: "admin@abc.com",                          │
│      password: "SecurePass123",                             │
│      modules: ["system_admin", "oms_fulfillment"]           │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. VALIDATE & CREATE TENANT                                 │
│    - Check subdomain availability                           │
│    - Validate email format                                  │
│    - Check module codes exist                               │
│    - Create tenant record in public.tenants                 │
│    - Create subscriptions in public.tenant_subscriptions    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CREATE TENANT SCHEMA                                     │
│    - CREATE SCHEMA tenant_abccorp                           │
│    - Run migrations (create all tables)                     │
│    - Seed default roles (Super Admin, Admin, etc.)          │
│    - Seed default permissions                               │
│    - Create admin user in tenant schema                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. GENERATE TOKENS & RETURN                                 │
│    - Generate JWT access token                              │
│    - Generate refresh token                                 │
│    - Return tenant details                                  │
│    {                                                         │
│      tenant_id: "uuid",                                     │
│      access_token: "jwt...",                                │
│      refresh_token: "jwt...",                               │
│      message: "Welcome to your ERP!"                        │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. USER LOGS IN                                             │
│    - Frontend stores tokens                                 │
│    - Redirects to dashboard                                 │
│    - Middleware extracts tenant from JWT                    │
│    - All queries use tenant_abccorp schema                  │
└─────────────────────────────────────────────────────────────┘
```

---

## SECURITY CONSIDERATIONS

### 1. Subdomain Validation
- Allow only alphanumeric + hyphens
- Minimum 3 characters, maximum 63 characters
- Reserved subdomains: admin, api, www, mail, etc.
- Check for profanity

### 2. Schema Isolation
- Each tenant has separate schema
- No cross-tenant data access
- Row-level security (RLS) in PostgreSQL
- Schema name validated to prevent injection

### 3. Admin User Creation
- Strong password requirements
- Email verification (optional)
- Default role: Super Admin (tenant level)
- Cannot access other tenants

### 4. Subscription Validation
- Module codes must exist in public.modules
- Cannot subscribe to same module twice
- Module dependencies checked (e.g., Sales requires OMS)

---

## TESTING PLAN

### Phase 3A Tests
- [ ] Test subdomain availability check
- [ ] Test duplicate subdomain rejection
- [ ] Test invalid subdomain formats
- [ ] Test reserved subdomain rejection
- [ ] Test module selection
- [ ] Test admin user creation
- [ ] Test JWT token generation

### Phase 3B Tests
- [ ] Test schema creation
- [ ] Test table migrations
- [ ] Test default data seeding
- [ ] Test admin user seeding
- [ ] Test rollback on failure
- [ ] Test schema name validation

### Phase 3C Tests
- [ ] Test module subscription
- [ ] Test module unsubscription
- [ ] Test module access after subscription
- [ ] Test module blocking after unsubscription
- [ ] Test billing calculations

### Phase 3D Tests
- [ ] Test super admin access
- [ ] Test tenant listing
- [ ] Test tenant suspension
- [ ] Test tenant reactivation
- [ ] Test statistics dashboard

### Phase 3E Tests
- [ ] Test server startup with fixed functions
- [ ] Test super admin creation
- [ ] Test init_db optimization
- [ ] Verify no tenant data conflicts

---

## SUCCESS CRITERIA

Phase 3 is complete when:

- [x] New tenants can sign up via API
- [x] Tenant schemas are created automatically
- [x] Module subscriptions work end-to-end
- [x] Tenant admin dashboard functional
- [x] Startup functions re-enabled and optimized
- [x] All tests passing (100% coverage)
- [x] Documentation updated

---

## DEPENDENCIES

**From Phase 1:**
- ✅ Multi-tenant database schema (public.tenants, modules, etc.)
- ✅ Tenant middleware
- ✅ @require_module decorator

**From Phase 2:**
- ✅ All endpoints decorated
- ✅ Module access control working
- ✅ Public endpoints identified

**New Dependencies:**
- PostgreSQL schema creation permissions
- Email service for notifications (optional)
- Billing integration (Phase 4)

---

## ESTIMATED EFFORT

| Task | Estimated Time |
|------|----------------|
| Phase 3A: Registration API | 2-3 hours |
| Phase 3B: Schema Creation | 3-4 hours |
| Phase 3C: Module Management | 2-3 hours |
| Phase 3D: Admin Dashboard | 3-4 hours |
| Phase 3E: Startup Functions | 1-2 hours |
| Testing | 2-3 hours |
| Documentation | 1 hour |
| **TOTAL** | **14-20 hours** |

---

## NEXT STEPS

1. Create Phase 3A schemas and services
2. Implement tenant registration endpoint
3. Test registration flow
4. Create schema creation script
5. Integrate with onboarding
6. Build module management API
7. Create admin dashboard
8. Fix startup functions
9. Run full test suite
10. Document and deploy

---

**Phase 3 Status: 📋 PLANNING COMPLETE**
**Ready to begin implementation: Phase 3A (Tenant Registration API)**

---

*Generated: 2026-02-01*
