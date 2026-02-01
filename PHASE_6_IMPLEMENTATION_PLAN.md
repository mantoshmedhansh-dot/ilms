# Phase 6: Operational Tables & Full ERP Functionality

## Overview

Implement operational ERP tables in tenant schemas to enable full application functionality. This phase creates the template schema and ensures all ERP features work within the multi-tenant structure.

---

## Objectives

1. Create template schema with all operational tables
2. Update tenant provisioning to copy template schema
3. Implement data seeding for demo tenants
4. Validate all ERP modules work with multi-tenant structure
5. Test end-to-end workflows

---

## 6.1 Template Schema Creation

### Goal
Create a template schema containing the structure of ALL operational tables (products, orders, customers, inventory, etc.) that will be copied when provisioning new tenants.

### Approach

**Option A: Use SQLAlchemy Models (Recommended)**
```python
# Use existing SQLAlchemy models to create tables
from app.models import Base
from sqlalchemy import create_engine

# Create all tables in template_tenant schema
engine = create_engine(DATABASE_URL, connect_args={"options": "-c search_path=template_tenant"})
Base.metadata.create_all(engine)
```

**Option B: Extract from Existing Database**
```sql
-- If operational tables exist elsewhere, copy structure
CREATE SCHEMA template_tenant;

-- Copy table structure (not data)
CREATE TABLE template_tenant.products (LIKE public.products INCLUDING ALL);
CREATE TABLE template_tenant.orders (LIKE public.orders INCLUDING ALL);
-- ... for all tables
```

### Tables to Include

Based on app/models/ directory (58 model files):

**Core Tables:**
- products, categories, brands
- orders, order_items
- customers, customer_addresses
- inventory, stock_items, movements
- warehouses, bins, zones

**Procurement:**
- vendors, purchase_orders, grn
- vendor_invoices, vendor_payments

**Finance:**
- chart_of_accounts, journal_entries, general_ledger
- tax_invoices, credit_notes, payment_receipts
- banking, bank_reconciliation

**Sales Channels:**
- channels, dealers, franchisees
- community_partners, commissions

**Service:**
- service_requests, technicians
- amc_contracts, warranty_claims

**HR:**
- employees, attendance, payroll, leaves

**CMS:**
- cms_pages, banners, testimonials, faqs

**AI/Analytics:**
- forecasts, demand_plans, scenarios

---

## 6.2 Update Tenant Provisioning Service

### Current Flow
```python
# app/services/tenant_schema_service.py (Phase 3B)
1. Create tenant schema
2. Create auth tables (users, roles, user_roles)
3. Seed default roles
4. Create admin user
```

### Enhanced Flow
```python
# Updated tenant provisioning
1. Create tenant schema
2. Copy template schema structure
3. Create auth tables (if not in template)
4. Seed default roles
5. Create admin user
6. Seed demo data (optional)
```

### Implementation

**File:** `app/services/tenant_schema_service.py`

```python
async def complete_tenant_setup(
    self,
    tenant_id: UUID,
    schema_name: str,
    admin_email: str,
    admin_password_hash: str,
    seed_demo_data: bool = False
):
    # 1. Create schema
    await self.db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

    # 2. Copy all tables from template_tenant
    await self._copy_template_schema(schema_name)

    # 3. Create auth tables (users, roles, user_roles)
    await self.create_tenant_tables(schema_name)

    # 4. Seed default roles
    await self.seed_default_roles(schema_name)

    # 5. Create admin user
    await self.create_admin_user(schema_name, admin_email, admin_password_hash)

    # 6. Optional: Seed demo data
    if seed_demo_data:
        await self._seed_demo_data(schema_name, tenant_id)
```

---

## 6.3 Demo Data Seeding

### Purpose
Provide sample data for each subscription tier so tenants can immediately explore features.

### Data Sets by Tier

**Starter Tier (3 modules):**
- 10 products with variants
- 5 sample orders
- 3 customers
- Basic inventory records

**Growth Tier (6 modules):**
- 25 products
- 15 orders
- 10 customers
- 2 vendors
- 5 purchase orders
- Sample invoices

**Professional Tier (9 modules):**
- 50 products
- 30 orders
- 20 customers
- 5 vendors
- Multi-channel setup (2 dealers)
- Sales analytics data

**Enterprise Tier (10 modules):**
- 100+ products
- 50+ orders
- 30+ customers
- 10 vendors
- 5 dealers
- 3 employees
- Complete sample dataset

### Implementation

**File:** `app/services/demo_data_service.py`

```python
class DemoDataService:
    async def seed_starter_data(self, schema_name: str):
        """Seed basic demo data for Starter tier"""
        # Products
        await self._create_sample_products(schema_name, count=10)

        # Customers
        await self._create_sample_customers(schema_name, count=3)

        # Orders
        await self._create_sample_orders(schema_name, count=5)

    async def seed_growth_data(self, schema_name: str):
        """Seed demo data for Growth tier"""
        await self.seed_starter_data(schema_name)

        # Additional for Growth
        await self._create_sample_vendors(schema_name, count=2)
        await self._create_sample_purchase_orders(schema_name, count=5)

    async def seed_professional_data(self, schema_name: str):
        """Seed demo data for Professional tier"""
        await self.seed_growth_data(schema_name)

        # Additional for Professional
        await self._create_sample_dealers(schema_name, count=2)
        await self._create_sample_analytics_data(schema_name)

    async def seed_enterprise_data(self, schema_name: str):
        """Seed complete demo data for Enterprise tier"""
        await self.seed_professional_data(schema_name)

        # Additional for Enterprise
        await self._create_sample_employees(schema_name, count=3)
        await self._create_sample_hr_data(schema_name)
```

---

## 6.4 Migration Strategy

### Create Template Schema Migration

**File:** `alembic/versions/003_create_template_schema.py`

```python
"""Create template schema with all operational tables"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create template schema
    op.execute('CREATE SCHEMA IF NOT EXISTS template_tenant')

    # Set search path to template schema
    op.execute('SET search_path TO template_tenant')

    # Create all tables using SQLAlchemy metadata
    # This will use the existing model definitions
    # to create tables in template_tenant schema

    # Products
    op.create_table(
        'products',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100), unique=True),
        # ... all product columns
        schema='template_tenant'
    )

    # Categories
    op.create_table(
        'categories',
        # ... all category columns
        schema='template_tenant'
    )

    # Continue for all tables...

def downgrade():
    op.execute('DROP SCHEMA IF EXISTS template_tenant CASCADE')
```

---

## 6.5 Validation & Testing

### Test Cases

**1. Template Schema Validation**
- [ ] Template schema exists
- [ ] All tables created correctly
- [ ] Indexes and constraints present
- [ ] No data in template tables

**2. Tenant Provisioning**
- [ ] New tenant gets all tables from template
- [ ] Auth tables created correctly
- [ ] Admin user can log in
- [ ] Demo data seeded (if requested)

**3. Module Functionality**
- [ ] Products module works (CRUD operations)
- [ ] Orders module works (create, list, update)
- [ ] Inventory module works (stock tracking)
- [ ] Finance module works (invoicing)
- [ ] All 10 modules functional

**4. Data Isolation**
- [ ] Tenant A cannot see Tenant B's products
- [ ] Tenant A cannot see Tenant B's orders
- [ ] Middleware routes queries correctly
- [ ] No data leakage between tenants

---

## 6.6 Implementation Checklist

### Backend

- [ ] Create `alembic/versions/003_create_template_schema.py`
- [ ] Run migration to create template schema
- [ ] Update `TenantSchemaService.complete_tenant_setup()`
- [ ] Create `DemoDataService` with seeding methods
- [ ] Update onboarding endpoint to support `seed_demo_data` flag
- [ ] Test template schema copy process
- [ ] Test demo data seeding

### Testing

- [ ] Create new test tenant with demo data
- [ ] Verify all tables exist in tenant schema
- [ ] Test CRUD operations on each module
- [ ] Verify data isolation between tenants
- [ ] Performance test with multiple tenants
- [ ] Document any issues found

### Documentation

- [ ] Update API docs with new onboarding parameters
- [ ] Document demo data structure
- [ ] Create tenant provisioning guide
- [ ] Update troubleshooting guide

---

## Timeline

**Week 1:**
- Create template schema migration
- Test schema creation
- Update tenant provisioning service

**Week 2:**
- Implement demo data service
- Seed data for each tier
- Test with new tenant creation

**Week 3:**
- Comprehensive testing
- Fix bugs and issues
- Performance optimization

**Week 4:**
- Documentation
- Final validation
- Prepare for production

---

## Success Criteria

✅ Template schema contains all 200+ operational tables
✅ New tenants receive complete table structure
✅ Demo data available for all tiers
✅ All 10 ERP modules functional in multi-tenant setup
✅ Data isolation verified
✅ Performance acceptable (< 500ms query time)
✅ Documentation complete

---

## Next Steps After Phase 6

1. **Production Deployment**
   - Deploy template schema to production
   - Update tenant onboarding process
   - Monitor first real customer onboarding

2. **Performance Optimization**
   - Index optimization
   - Query performance tuning
   - Caching strategy

3. **Feature Enhancements**
   - Advanced analytics
   - Custom reports
   - API integrations

