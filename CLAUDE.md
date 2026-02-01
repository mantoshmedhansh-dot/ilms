# CLAUDE.md - Aquapurite ERP System Reference

> **Purpose**: This document is the single source of truth for understanding the Aquapurite ERP codebase structure, architecture standards, and development guidelines.

---

## Project Overview

**Aquapurite ERP** - A full-stack Consumer Durable ERP system for water purifier manufacturing and distribution.

| Layer | Technology | Description |
|-------|------------|-------------|
| **Backend** | FastAPI + SQLAlchemy + psycopg3 | Async Python API with PostgreSQL |
| **Frontend** | Next.js 14+ TypeScript | React framework with App Router |
| **UI Components** | Tailwind CSS + shadcn/ui | Modern component library |
| **Database** | PostgreSQL (Supabase) | Production database with Row Level Security |
| **Backend Hosting** | Render.com | Auto-deploy from main branch |
| **Frontend Hosting** | Vercel | Auto-deploy from main branch |

### Production URLs

| Service | URL |
|---------|-----|
| ERP Admin Panel | https://www.aquapurite.org |
| D2C Storefront | https://www.aquapurite.com |
| Backend API | https://aquapurite-erp-api.onrender.com |
| API Documentation | https://aquapurite-erp-api.onrender.com/docs |
| Health Check | https://aquapurite-erp-api.onrender.com/health |

---

## Project Structure

```
/Users/mantosh/Desktop/Consumer durable 2/
├── app/                          # FastAPI Backend
│   ├── api/v1/
│   │   ├── endpoints/            # 76 API route files
│   │   └── router.py             # Main router registration
│   ├── models/                   # 58 SQLAlchemy ORM models
│   ├── schemas/                  # 65 Pydantic request/response schemas
│   ├── services/                 # 53 Business logic services
│   ├── core/                     # Security, config, utilities
│   │   ├── config.py             # Settings from environment
│   │   ├── security.py           # JWT & password hashing
│   │   └── enum_utils.py         # Status/enum helpers
│   └── database.py               # Async database session
├── frontend/                     # Next.js Frontend
│   └── src/
│       ├── app/
│       │   ├── dashboard/        # 26 ERP admin sections
│       │   └── (storefront)/     # 15 D2C customer pages
│       ├── components/           # Reusable UI components
│       ├── lib/api/              # 71 API client modules
│       ├── config/navigation.ts  # Menu structure with permissions
│       └── types/                # TypeScript interfaces
├── alembic/                      # Database migrations
├── scripts/                      # Utility scripts
└── CLAUDE.md                     # This file
```

---

## Backend Architecture

### Layer Responsibilities

```
┌─────────────────────────────────────────────────────────────┐
│                     API ENDPOINTS                           │
│  app/api/v1/endpoints/*.py                                  │
│  - HTTP request handling                                    │
│  - Input validation via Pydantic schemas                    │
│  - Authorization checks                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     SERVICES                                │
│  app/services/*.py                                          │
│  - Business logic                                           │
│  - Cross-entity operations                                  │
│  - External integrations (Razorpay, Shiprocket, GST)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     MODELS                                  │
│  app/models/*.py                                            │
│  - SQLAlchemy ORM definitions                               │
│  - Database table mappings                                  │
│  - Relationships and constraints                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE                                │
│  PostgreSQL (Supabase)                                      │
│  - 200+ tables                                              │
│  - JSONB for flexible data                                  │
│  - TIMESTAMPTZ for all timestamps                           │
└─────────────────────────────────────────────────────────────┘
```

### API Modules (76 endpoint files)

| Category | Endpoints |
|----------|-----------|
| **Auth & Access** | auth, users, roles, permissions, access_control |
| **Product Catalog** | products, categories, brands, serialization |
| **Orders & CRM** | orders, customers, leads, call_center |
| **Inventory** | inventory, warehouses, transfers, stock_adjustments |
| **Procurement** | vendors, purchase, grn, vendor_invoices, vendor_proformas |
| **Finance** | accounting, billing, banking, tds, auto_journal |
| **Logistics** | shipments, manifests, transporters, serviceability, rate_cards |
| **Service** | service_requests, technicians, installations, amc |
| **Channels** | channels, marketplaces, channel_reports |
| **CMS** | cms, storefront |
| **HR** | hr (employees, attendance, payroll, leave) |
| **Analytics** | insights, ai, dashboard_charts, reports |

### Models (58 model files)

Key domain models:
- `product.py` - Product catalog with variants, specs, images
- `order.py` - Orders, order items, order history
- `customer.py` - Customer profiles, addresses
- `inventory.py` - Stock items, movements, reservations
- `vendor.py` - Vendor management, ledger
- `accounting.py` - GL accounts, journal entries, periods
- `channel.py` - Sales channels, pricing, inventory

### Services (53 service files)

Key business logic:
- `order_service.py` - Order creation, status management
- `inventory_service.py` - Stock management, allocations
- `pricing_service.py` - Channel pricing, rules engine
- `invoice_service.py` - Invoice generation, GST calculation
- `serialization.py` - Barcode generation, serial tracking

---

## Frontend Architecture

### Dashboard Sections (26 modules)

| Section | Path | Description |
|---------|------|-------------|
| **Dashboard** | `/dashboard` | Overview, KPIs, charts |
| **Sales** | `/dashboard/orders` | Orders, channels, distribution |
| **CRM** | `/dashboard/crm` | Customers, leads, call center |
| **Inventory** | `/dashboard/inventory` | Stock, movements, transfers |
| **Procurement** | `/dashboard/procurement` | Vendors, POs, GRN |
| **Finance** | `/dashboard/finance` | GL, invoices, banking, tax |
| **Logistics** | `/dashboard/logistics` | Shipments, manifests, tracking |
| **Service** | `/dashboard/service` | Service requests, warranty, AMC |
| **HR** | `/dashboard/hr` | Employees, payroll, attendance |
| **Master Data** | `/dashboard/catalog` | Products, categories, brands |
| **CMS** | `/dashboard/cms` | D2C content management |

### Storefront Pages (15 pages)

| Page | Path | Description |
|------|------|-------------|
| Products | `/products` | Product catalog with filters |
| Product Detail | `/products/[slug]` | Product page with reviews |
| Cart | `/cart` | Shopping cart |
| Checkout | `/checkout` | Payment flow |
| Account | `/account` | Customer profile, orders |
| Track Order | `/track/order/[orderNumber]` | Public order tracking |

### API Client Structure

```typescript
// frontend/src/lib/api/index.ts

// 71 API modules organized by domain
export const authApi = { login, logout, refreshToken, ... };
export const productsApi = { list, get, create, update, ... };
export const ordersApi = { list, create, updateStatus, ... };
export const customersApi = { list, get, create, ... };
export const inventoryApi = { getStock, getMovements, ... };
export const channelsApi = { list, getPricing, updatePricing, ... };
// ... 65 more API modules
```

### Navigation Configuration

```typescript
// frontend/src/config/navigation.ts

// Menu structure with permission-based access
const navigation = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'Sales',
    icon: ShoppingCart,
    permissions: ['ORDERS_VIEW'],
    children: [
      { title: 'Orders', href: '/dashboard/orders' },
      { title: 'Channels', href: '/dashboard/channels' },
      // ...
    ],
  },
  // ... more sections
];
```

---

## Database Standards

### Data Types

| Use Case | Type | Example |
|----------|------|---------|
| Primary Keys | `UUID` | Most tables |
| Primary Keys (legacy) | `VARCHAR(36)` | franchisees, po_serials |
| Status Fields | `VARCHAR(50)` | NEVER use PostgreSQL ENUM |
| JSON Data | `JSONB` | NEVER use JSON |
| Timestamps | `TIMESTAMPTZ` | NEVER use TIMESTAMP |
| Money | `NUMERIC(18,2)` | Exact decimal precision |
| Percentages | `NUMERIC(5,2)` | e.g., 99.99% |

### Status Values

All status fields use UPPERCASE VARCHAR strings:

| Status Type | Values |
|-------------|--------|
| Order Status | NEW, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED |
| Payment Status | PENDING, PAID, PARTIALLY_PAID, REFUNDED, FAILED |
| Invoice Status | DRAFT, APPROVED, GENERATED, PAID, CANCELLED |

### SQLAlchemy Patterns

```python
# Model definition
from sqlalchemy import String, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid

class Order(Base):
    __tablename__ = "orders"

    # UUID primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Status as VARCHAR (not ENUM)
    status: Mapped[str] = mapped_column(String(50), default="NEW")

    # Timestamps with timezone
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # JSON data as JSONB
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
```

### Pydantic Schema Patterns

```python
# Response schema - inherit from BaseResponseSchema
from app.schemas.base import BaseResponseSchema
from uuid import UUID

class OrderResponse(BaseResponseSchema):
    """Response schema - inherits UUID serialization."""
    id: UUID
    status: str
    total_amount: Decimal

# Create/Update schema - add validators here
class OrderCreate(BaseModel):
    customer_id: UUID
    items: List[OrderItemCreate]

    @field_validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Order must have at least one item')
        return v
```

---

## Coding Standards

### Rule 1: Response Schema Completeness

Every field returned by a service MUST be defined in the response schema.

```python
# ❌ BAD - Field silently dropped
# Service returns: {"total_orders": 38, "total_customers": 20}
# Schema only has: total_orders: int
# Result: total_customers is lost!

# ✅ GOOD - All fields defined
class OrderSummary(BaseModel):
    total_orders: int
    total_customers: int  # Include ALL fields
```

### Rule 2: Validator Placement

NEVER put validators on Base schemas. Only on Create/Update schemas.

```python
# ❌ BAD - Breaks GET responses
class CompanyBase(BaseModel):
    @field_validator('logo_url')
    def validate_url(cls, v): ...  # Runs on responses too!

# ✅ GOOD - Only validates inputs
class CompanyCreate(CompanyBase):
    @field_validator('logo_url')
    def validate_url(cls, v): ...
```

### Rule 3: Timezone-Aware Datetime

ALWAYS use `datetime.now(timezone.utc)`, NEVER `datetime.utcnow()`.

```python
from datetime import datetime, timezone

# ❌ BAD - Timezone-naive
created_at = datetime.utcnow()

# ✅ GOOD - Timezone-aware
created_at = datetime.now(timezone.utc)
```

### Rule 4: Field Naming Consistency

Use EXACT same field names across backend and frontend.

```
Backend Service → Pydantic Schema → Frontend Type
total_orders      total_orders       total_orders   ✓ SAME
```

### Rule 5: NO Mock Data in Production Code (CRITICAL)

**NEVER use hardcoded mock/placeholder data as fallback values in frontend.**

```typescript
// ❌ BAD - Shows fake data when API returns empty
const stats = apiData || {
  total_sales: 1245000,    // FAKE! Will show even if no real sales
  customers: 150,          // FAKE! Misleading to users
};

// ✅ GOOD - Shows zeros/empty when no real data
const stats = apiData || {
  total_sales: 0,
  customers: 0,
};

// ✅ GOOD - Show "No data" message instead
if (!apiData) return <EmptyState message="No data available" />;
```

**This rule exists because:** Mock data in fallback values causes users to see fake financial figures, compliance rates, or inventory counts that don't reflect actual system state.

### Rule 6: Category Hierarchy

Products are assigned to LEAF categories (subcategories), not parent categories.

```
✅ CORRECT: Product → "RO+UV Water Purifiers" (subcategory)
❌ WRONG:   Product → "Water Purifiers" (parent)
```

Implement cascading dropdowns: Parent Category → Subcategory → Products

### Rule 7: Database Structure Verification (CRITICAL)

**Before implementing any new feature or modification, ALWAYS verify the database structure in Supabase:**

1. **Check if required tables exist** in production database
2. **Check if required columns exist** with correct data types
3. **Supabase is the SINGLE SOURCE OF TRUTH** - SQLAlchemy models must match

```bash
# Verify database structure using Python script:
python3 -c "
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host='db.aavjhutqzwusgdwrczds.supabase.co',
        port=6543,
        user='postgres',
        password='Aquapurite2026',
        database='postgres',
        statement_cache_size=0
    )

    # Check table columns
    cols = await conn.fetch('''
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'YOUR_TABLE_NAME'
        ORDER BY ordinal_position
    ''')
    for c in cols:
        print(f'{c[\"column_name\"]}: {c[\"data_type\"]}')

    await conn.close()

asyncio.run(main())
"
```

**If table/column doesn't exist:**
- Create migration in Supabase SQL Editor first
- Then update SQLAlchemy model to match
- NEVER assume database schema matches model

**Common checks:**
| Change Type | Verify |
|------------|--------|
| New model field | Column exists in table |
| Foreign key | Referenced table/column exists |
| New table | Table created in Supabase |
| Data type change | Column type matches |

---

## Development Guide

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (for local PostgreSQL)

### Local Development

```bash
# 1. Start local PostgreSQL
cd "/Users/mantosh/Desktop/Consumer durable 2"
docker-compose up -d

# 2. Run backend
uvicorn app.main:app --reload --port 8000

# 3. Run frontend (separate terminal)
cd frontend
pnpm dev
```

### Environment Variables

Create `.env` file in project root:

```env
# Database (local Docker)
DATABASE_URL=postgresql+psycopg://aquapurite:aquapurite@localhost:5432/aquapurite_erp

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Supabase (for storage)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_STORAGE_BUCKET=uploads
```

### Supabase Production Database

```
Host: db.aavjhutqzwusgdwrczds.supabase.co
Port: 6543
Database: postgres
User: postgres
Password: Aquapurite2026

Connection String:
postgresql://postgres:Aquapurite2026@db.aavjhutqzwusgdwrczds.supabase.co:6543/postgres
```

### Pre-Deployment Checklist

Before pushing any code:

1. **Build frontend**: `cd frontend && pnpm build`
2. **Test locally**: Start both servers and verify changes
3. **Verify API health**: `curl http://localhost:8000/health`
4. **Check for TypeScript errors**: Build must pass
5. **Commit and push**: `git push origin main`

---

## Rules of Engagement (Development Workflow)

Follow these practices for efficient and safe deployments:

### MANDATORY PRE-DEPLOYMENT CHECKLIST

**NEVER push to production without completing ALL steps:**

| Step | Action | Command/Location |
|------|--------|------------------|
| 1 | **Build Frontend** | `cd frontend && pnpm build` |
| 2 | **Start Local Backend** | `uvicorn app.main:app --reload --port 8000` |
| 3 | **Start Local Frontend** | `cd frontend && pnpm dev` |
| 4 | **Test Affected Pages** | Open browser, test the specific feature |
| 5 | **Test API Endpoints** | Use real data, check request/response |
| 6 | **Verify Database Schema** | Check Supabase matches model (SINGLE SOURCE OF TRUTH) |
| 7 | **Push to Production** | `git push origin main` |
| 8 | **Verify Production** | Test on live site after deploy completes |

```bash
# Complete workflow example:
cd "/Users/mantosh/Desktop/Consumer durable 2"

# Step 1: Build frontend
cd frontend && pnpm build
cd ..

# Step 2-3: Start local servers (in separate terminals)
# Terminal 1:
uvicorn app.main:app --reload --port 8000

# Terminal 2:
cd frontend && pnpm dev

# Step 4-5: Test in browser at http://localhost:3000
# - Navigate to affected pages
# - Test with real data
# - Check browser console for errors
# - Check backend terminal for errors

# Step 6: If database changes needed, verify Supabase schema first

# Step 7: Only after ALL tests pass
git add -A && git commit -m "message" && git push origin main

# Step 8: Wait for deploy, then verify on production
```

### Why This Matters

- **Step 1 (Build)**: Catches TypeScript errors before deploy
- **Step 4-5 (Test Locally)**: Catches 90% of bugs
- **Step 6 (Schema)**: Supabase is the source of truth - models must match
- **Step 8 (Verify Production)**: Confirms deploy worked correctly

### 2. Use Smart Deployments

Configuration is already set up to skip unnecessary deployments:

**Vercel** (`vercel.json`):
- Skips deployment if only backend files changed
- Deploys only when `frontend/` directory has changes

**Render** (configure in dashboard):
- Go to Render Dashboard → aquapurite-api service
- Settings → Build & Deploy → Auto-Deploy
- Add to "Ignored Paths": `frontend/**`
- This skips backend rebuild when only frontend files change

### 3. Batch Related Changes

Instead of pushing after every small fix:

```bash
# ❌ BAD - 5 separate deployments
git commit -m "Fix typo"
git push
# wait 5 mins...
git commit -m "Fix another thing"
git push
# wait 5 mins...

# ✅ GOOD - 1 deployment with all fixes
git commit -m "Fix typo in orders"
git commit -m "Fix validation in products"
git commit -m "Update category tree view"
git push  # Single deployment with all changes
```

### 4. Use Feature Branches (Best Practice)

For larger changes, use feature branches:

```bash
# Create feature branch
git checkout -b feature/new-category-tree

# Make multiple commits
git commit -m "Add tree structure"
git commit -m "Add expand/collapse"
git commit -m "Style improvements"

# When ready, merge to main and push
git checkout main
git merge feature/new-category-tree
git push  # Single deployment
```

### 5. Separate Backend and Frontend Commits

Group changes by deployment target:

```bash
# ✅ GOOD - Isolated deployments
git commit -m "Backend: Fix product API response"
git commit -m "Frontend: Update category page"
git push

# Smart deployment will:
# - Deploy backend only if app/ changed
# - Deploy frontend only if frontend/ changed
```

### Summary

| Practice | Benefit |
|----------|---------|
| Test locally first | Catch issues before deployment |
| Smart deployments | Skip unnecessary rebuilds |
| Batch changes | Fewer deployment cycles |
| Feature branches | Keep main stable |
| Separate commits | Isolated deployments |

---

## Deployment

> **CRITICAL**: Always deploy from the PROJECT ROOT directory, NOT from frontend/

### Git Repository

```
Repository: git@github.com:aquapurite/ERP.git
Branch: main
Remote: origin
```

### Vercel Configuration (Frontend)

**IMPORTANT: There are 3 Vercel projects - use the CORRECT one!**

| Project Name | Domain | Purpose | Deploy From |
|--------------|--------|---------|-------------|
| `erp` | **www.aquapurite.org** | ERP Admin Panel | Project Root |
| `d2c` | www.aquapurite.com | D2C Storefront | Project Root |
| `frontend` | ❌ DO NOT USE | Old/test project | - |

**Vercel Account Details:**
- Team/Scope: `anupam-singhs-projects-ffea0ac8`
- Account: Run `npx vercel whoami` to verify

### Deploy ERP Frontend (www.aquapurite.org)

```bash
# ALWAYS run from project root, NOT from frontend/
cd "/Users/mantosh/Desktop/Consumer durable 2"

# Step 1: Link to the correct project (erp, NOT frontend)
npx vercel link --project=erp --yes

# Step 2: Deploy to production
npx vercel --prod

# Expected output should show:
# Aliased: https://www.aquapurite.org
```

### Deploy D2C Storefront (www.aquapurite.com)

```bash
cd "/Users/mantosh/Desktop/Consumer durable 2"
npx vercel link --project=d2c --yes
npx vercel --prod
```

### Backend (Render.com)

**Service Details:**
- Service Name: `aquapurite-erp-api`
- URL: https://aquapurite-erp-api.onrender.com
- Health Check: https://aquapurite-erp-api.onrender.com/health
- API Docs: https://aquapurite-erp-api.onrender.com/docs

**Deployment:**
- Render auto-deploys when code is pushed to `main` branch on GitHub
- If auto-deploy is not working, manually trigger from Render Dashboard:
  1. Go to https://dashboard.render.com
  2. Select `aquapurite-erp-api` service
  3. Click "Manual Deploy" → "Deploy latest commit"

### Complete Deployment Checklist

```bash
# 1. Commit and push changes
cd "/Users/mantosh/Desktop/Consumer durable 2"
git add .
git commit -m "your message"
git push origin main

# 2. Deploy frontend to Vercel (ERP)
npx vercel link --project=erp --yes
npx vercel --prod
# Verify: https://www.aquapurite.org

# 3. Backend auto-deploys to Render
# Verify: curl https://aquapurite-erp-api.onrender.com/health
```

### Troubleshooting Deployment Issues

**Wrong Vercel project?**
```bash
# Check current linked project
cat .vercel/project.json

# Re-link to correct project
npx vercel link --project=erp --yes
```

**Render not auto-deploying?**
1. Check GitHub connection in Render Dashboard
2. Verify branch is set to `main`
3. Use Manual Deploy as fallback

---

## Key Business Flows

### Order-to-Cash Flow

```
CREATE ORDER → PAY → ALLOCATE → PICK → PACK → SHIP → DELIVER → INVOICE → GL
```

### Procurement Flow (P2P)

```
REQUISITION → PO → APPROVE → RECEIVE (GRN) → 3-WAY MATCH → VENDOR INVOICE → PAYMENT
```

### Serialization Flow

```
PO APPROVED → SERIALS GENERATED → GRN ACCEPT → STOCK ITEMS CREATED → BARCODE TRACKING
```

### Barcode Format

`APFSZAIEL00000001` (17 characters for FG)
- `AP`: Brand prefix (Aquapurite)
- `FS`: Supplier code (2 letters)
- `Z`: Year code (A=2000, Z=2025)
- `A`: Month code (A=Jan, L=Dec)
- `IEL`: Model code (3 letters)
- `00000001`: Serial number (8 digits)

---

## Governance Rules

### Rule 1: No Autonomous Decisions

Claude will NOT make decisions without explicit user approval. Always present options and wait for "proceed" or "go ahead".

### Rule 2: Gap Analysis First

Before implementing, audit what exists:
1. Check backend APIs
2. Check frontend pages
3. Check database tables
4. Present findings for review

### Rule 3: End-to-End Verification

Every feature must be traced: Database → Model → Schema → API → Frontend Page → Component

### Rule 4: Backward Compatibility

Always check:
- Will existing data work with new validation?
- Will existing API consumers break?
- Are response schemas compatible?

### Rule 5: Full-Stack Completion (CRITICAL)

**NEVER deploy backend-only changes. Every backend feature MUST have corresponding frontend integration.**

### Rule 6: Phase-by-Phase Testing with Supabase (CRITICAL)

**When implementing multi-phase projects, EACH phase MUST be tested locally with Supabase before proceeding to the next phase.**

#### Testing Requirements

1. **Complete Phase Implementation** - Finish all code for current phase
2. **Run Migrations** - Execute Alembic migrations against local Supabase connection
3. **Verify Database Structure** - Confirm tables/columns match expected schema in Supabase
4. **Local Integration Testing** - Test full stack locally (backend + frontend) with Supabase database
5. **Document Test Results** - Record what was tested and verification steps
6. **User Approval** - Get explicit approval before moving to next phase

#### Supabase as Single Source of Truth

- **Production Database**: Supabase is the authoritative schema
- **Code Must Match Database**: Backend models must match actual Supabase structure
- **No Assumptions**: Always verify table/column existence before using in code
- **Migration Verification**: After running migrations, manually verify in Supabase SQL Editor

#### Phase Transition Checklist

**DO NOT proceed to next phase until:**

- [ ] All migrations for current phase executed successfully
- [ ] Database tables verified in Supabase (using SQL queries or Table Editor)
- [ ] Backend models match Supabase schema exactly
- [ ] Local backend starts without errors (`uvicorn app.main:app --reload`)
- [ ] Local frontend builds successfully (`cd frontend && pnpm build`)
- [ ] End-to-end testing completed (manual testing of new features)
- [ ] Test results documented
- [ ] User approval received

#### Example Phase 1 Testing Commands

```bash
# 1. Run migrations
alembic upgrade head

# 2. Verify tables in Supabase
psql "postgresql://postgres:Aquapurite2026@db.aavjhutqzwusgdwrczds.supabase.co:6543/postgres"
\dt public.*

# 3. Start local backend
uvicorn app.main:app --reload --port 8000

# 4. Build frontend
cd frontend && pnpm build

# 5. Test API endpoints
curl http://localhost:8000/api/test/endpoint -H "X-Tenant-ID: test-id"

# 6. Document results and get approval before Phase 2
```

**Why This Rule Exists:**
- Prevents cascading errors across phases
- Ensures database and code stay synchronized
- Catches issues early when they're easier to fix
- Validates assumptions about schema structure
- Provides stable foundation for next phase

---

## Full-Stack Feature Development Checklist (MANDATORY)

> **CRITICAL**: This checklist MUST be completed for EVERY new feature before deployment. Backend-only deployments are FORBIDDEN.

### The Full-Stack Completion Rule

```
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND FEATURE WITHOUT FRONTEND = INCOMPLETE FEATURE          │
│  ============================================================   │
│  Every API endpoint MUST have:                                  │
│  1. Frontend API client method in frontend/src/lib/api/         │
│  2. UI component/page that uses the endpoint                    │
│  3. Navigation link (if new page)                               │
│  4. User-facing button/action (if new action)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Pre-Development Checklist

Before starting ANY feature:

| Step | Check | Action |
|------|-------|--------|
| 1 | **Identify all layers** | List: DB tables, Models, Schemas, APIs, Frontend pages, Components |
| 2 | **Plan full stack** | Document what needs to be created/modified at EACH layer |
| 3 | **Estimate scope** | If backend has 5 endpoints, frontend needs 5 API client methods + UI |

### Development Order (MANDATORY)

Always develop in this order to ensure completeness:

```
1. DATABASE     → Create/modify tables in Supabase
2. MODELS       → Update SQLAlchemy models to match
3. SCHEMAS      → Create Pydantic request/response schemas
4. SERVICES     → Implement business logic
5. ENDPOINTS    → Create API routes
6. API CLIENT   → Add methods to frontend/src/lib/api/index.ts
7. UI PAGE      → Create/update page component
8. NAVIGATION   → Add menu item if new page
9. TEST         → Verify full flow works
```

### Post-Development Verification Checklist

**BEFORE committing, verify ALL items:**

#### Backend Verification
- [ ] All new endpoints documented in Swagger (`/docs`)
- [ ] All endpoints return proper response schemas
- [ ] Error handling implemented
- [ ] Authorization checks in place

#### Frontend API Client Verification
- [ ] Every new backend endpoint has a corresponding method in `frontend/src/lib/api/index.ts`
- [ ] API client method names match endpoint purpose
- [ ] TypeScript types defined for request/response

#### Frontend UI Verification
- [ ] Page exists for viewing data (if applicable)
- [ ] Form exists for creating/editing (if applicable)
- [ ] Action buttons exist for operations (if applicable)
- [ ] Loading states implemented
- [ ] Error handling with user-friendly messages
- [ ] Success toast notifications

#### Navigation Verification
- [ ] New pages added to `frontend/src/config/navigation.ts`
- [ ] Permissions configured correctly
- [ ] Menu hierarchy is logical

### Feature Completion Matrix

Use this matrix to track feature completeness:

| Layer | File Location | Status |
|-------|---------------|--------|
| Database Table | Supabase | ☐ |
| SQLAlchemy Model | `app/models/*.py` | ☐ |
| Pydantic Schema | `app/schemas/*.py` | ☐ |
| Service Logic | `app/services/*.py` | ☐ |
| API Endpoint | `app/api/v1/endpoints/*.py` | ☐ |
| Router Registration | `app/api/v1/router.py` | ☐ |
| Frontend API Client | `frontend/src/lib/api/index.ts` | ☐ |
| Frontend Page | `frontend/src/app/dashboard/**/page.tsx` | ☐ |
| Navigation Menu | `frontend/src/config/navigation.ts` | ☐ |
| Local Testing | Browser + API | ☐ |

### Common Mistakes to AVOID

```
❌ WRONG: Create backend API → Deploy → "Frontend will come later"
✅ RIGHT: Create backend API → Create frontend integration → Test → Deploy

❌ WRONG: Add 5 new endpoints → Add 0 frontend methods
✅ RIGHT: Add 5 new endpoints → Add 5 frontend methods → Add UI to use them

❌ WRONG: Create service with new feature → No button to trigger it
✅ RIGHT: Create service → Create API → Create frontend method → Add button
```

### Example: Correct Full-Stack Development

**Feature: GST e-Filing**

| Layer | What to Create | File |
|-------|----------------|------|
| Model | `GSTFiling`, `ITCLedger` | `app/models/itc.py` |
| Schema | `GSTFilingCreate`, `GSTFilingResponse` | `app/schemas/gst_filing.py` |
| Service | `GSTFilingService` | `app/services/gst_filing_service.py` |
| Endpoint | `POST /gst/file/gstr1` | `app/api/v1/endpoints/gst_filing.py` |
| Router | Register in router | `app/api/v1/router.py` |
| API Client | `gstFilingApi.fileGSTR1()` | `frontend/src/lib/api/index.ts` |
| Page | GST Filing Dashboard | `frontend/src/app/dashboard/finance/gst-filing/page.tsx` |
| Button | "File GSTR-1" button | In the page component |
| Navigation | Add to Finance menu | `frontend/src/config/navigation.ts` |

### Deployment Gate

**DO NOT DEPLOY if any of these are true:**

1. ❌ Backend endpoint exists but no frontend API client method
2. ❌ Frontend API client method exists but no UI uses it
3. ❌ New page exists but not in navigation menu
4. ❌ Action endpoint exists but no button triggers it
5. ❌ Feature not tested end-to-end locally
6. ❌ **Duplicate navigation items exist** (same href in multiple places without intentional cross-reference)
7. ❌ **Duplicate page files exist** (same functionality in different directories)

### Quick Verification Commands

```bash
# Check backend endpoints
curl http://localhost:8000/docs | grep "POST\|GET\|PUT\|DELETE"

# Check frontend API methods (count)
grep -c "async\|export const" frontend/src/lib/api/index.ts

# Check navigation items
grep -c "href:" frontend/src/config/navigation.ts

# ========== DUPLICATION CHECKS (MANDATORY BEFORE DEPLOY) ==========

# Check for duplicate navigation hrefs (same URL appearing multiple times)
grep -o "href: '[^']*'" frontend/src/config/navigation.ts | sort | uniq -d
# If output is NOT empty, investigate duplicates!

# Check for duplicate page titles in navigation
grep -o "title: '[^']*'" frontend/src/config/navigation.ts | sort | uniq -d
# If output is NOT empty, verify if intentional cross-reference

# Find duplicate page.tsx files (same page name in different directories)
find frontend/src/app -name "page.tsx" | xargs -I {} dirname {} | xargs -I {} basename {} | sort | uniq -d
# If output shows duplicates, verify they serve different purposes

# Verify a specific endpoint has frontend integration
# Backend endpoint: /gst/file/gstr1
grep "gst/file/gstr1" frontend/src/lib/api/index.ts
# If no result → FRONTEND INTEGRATION MISSING!
```

### Duplication Prevention Rules (CRITICAL)

**Before EVERY deployment, check for duplications:**

#### 1. Navigation Duplication Check
```
ALLOWED DUPLICATIONS (Intentional Cross-References):
- Vendor Invoices: Can appear in both Procurement AND Finance > Payables
  (Same page accessible from different business contexts)

NOT ALLOWED DUPLICATIONS:
- Same feature appearing in multiple sections without clear purpose
- E.g., "E-Way Bills" should only be in Finance > Tax Compliance, NOT also in Logistics
```

#### 2. Types of Duplication to Check

| Check | Command | Action if Found |
|-------|---------|-----------------|
| **Duplicate hrefs** | `grep -o "href: '[^']*'" navigation.ts \| sort \| uniq -d` | Remove redundant entry or document why cross-reference is needed |
| **Duplicate titles** | `grep -o "title: '[^']*'" navigation.ts \| sort \| uniq -d` | Rename to clarify purpose or remove |
| **Duplicate pages** | `find frontend/src/app -name "page.tsx" \| ...` | Consolidate into single page |
| **Duplicate API methods** | Review `index.ts` for similar endpoints | Consolidate into single method |

#### 3. When Duplication IS Acceptable

Cross-referencing the same page in multiple navigation sections is OK when:
- The page serves multiple business functions (e.g., Vendor Invoices for both Procurement and Accounts Payable)
- Users from different departments need quick access
- **Document the reason** in a comment in navigation.ts

#### 4. When Duplication is NOT Acceptable

- Same functionality in different page files
- Same API endpoint wrapped in multiple methods
- Same menu item appearing without clear business justification
- Copy-pasted components that should be shared

### Coding Rules Compliance Check (MANDATORY BEFORE DEPLOY)

**Every new feature MUST be verified against these coding rules:**

#### Rule 1: Response Schema Completeness Check
```bash
# For each new backend endpoint, verify frontend interface includes ALL returned fields
# Backend returns: { total_orders, total_customers, pending_amount }
# Frontend interface MUST have: total_orders, total_customers, pending_amount
# Missing fields = Data silently dropped = BUG!

# How to check:
# 1. Read backend schema/response model
# 2. Read frontend TypeScript interface
# 3. Ensure EVERY backend field exists in frontend interface
```

#### Rule 2: Validator Placement Check
```bash
# Validators should ONLY be on Create/Update schemas, NEVER on Base schemas
# Check that no @field_validator decorators exist on Base schemas
grep -n "@field_validator" app/schemas/*.py | grep "Base"
# If output is NOT empty → VIOLATION! Move validators to Create/Update schemas
```

#### Rule 3: Timezone-Aware Datetime Check
```bash
# Search for deprecated datetime.utcnow() usage
grep -rn "datetime.utcnow()" app/
# If output is NOT empty → VIOLATION! Replace with datetime.now(timezone.utc)
```

#### Rule 4: Field Naming Consistency Check (CRITICAL)
```bash
# EXACT same field names must be used across:
# Backend Pydantic Schema ↔ Frontend TypeScript Interface

# Example of CORRECT naming:
# Backend: cgst_itc: float      → Frontend: cgst_itc: number     ✓ MATCH
# Backend: total_amount: Decimal → Frontend: total_amount: number ✓ MATCH

# Example of VIOLATION:
# Backend: cgst_itc: float      → Frontend: cgst: number         ✗ MISMATCH!
# Backend: invoice_value: Decimal → Frontend: amount: number     ✗ MISMATCH!

# How to verify:
# 1. Read backend response schema (app/schemas/*.py or inline in endpoints)
# 2. Read frontend interface (in page.tsx or types/)
# 3. Compare field names EXACTLY - they must match character-for-character
```

#### Rule 5: Category Hierarchy Check
```bash
# Products should be assigned to LEAF categories only
# Verify no direct parent category assignment in product creation
```

#### Rule 6: Database Structure Check
```bash
# Before using any new model field, verify column exists in Supabase
python3 -c "
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host='db.aavjhutqzwusgdwrczds.supabase.co',
        port=6543,
        user='postgres',
        password='Aquapurite2026',
        database='postgres',
        statement_cache_size=0
    )
    cols = await conn.fetch('''
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'YOUR_TABLE_NAME'
    ''')
    print([c['column_name'] for c in cols])
    await conn.close()

asyncio.run(main())
"
```

### Quick Compliance Verification Script
```bash
# Run this before EVERY deployment to catch common violations

echo "=== Rule 2: Checking for validators on Base schemas ==="
grep -rn "@field_validator" app/schemas/ | grep "Base" || echo "✓ No violations"

echo ""
echo "=== Rule 3: Checking for deprecated utcnow() ==="
grep -rn "datetime.utcnow()" app/ || echo "✓ No violations"

echo ""
echo "=== Rule 4: Field Naming - Manual Review Required ==="
echo "Compare backend schemas with frontend interfaces for new features"

echo ""
echo "=== Build Check ==="
cd frontend && pnpm build && echo "✓ Build passed" || echo "✗ Build FAILED"
```

### Post-Deployment Verification

After deployment, verify on production:

1. **Backend**: Check `/docs` shows new endpoints
2. **Frontend**: Navigate to new page, test all buttons
3. **Integration**: Perform full user flow from UI to database

---

## Quick Reference

### Common Commands

```bash
# Build frontend
cd frontend && pnpm build

# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Check API health
curl https://aquapurite-erp-api.onrender.com/health

# Connect to production database
psql "postgresql://postgres:Aquapurite2026@db.aavjhutqzwusgdwrczds.supabase.co:6543/postgres"
```

### File Locations

| What | Where |
|------|-------|
| API Endpoints | `app/api/v1/endpoints/` |
| SQLAlchemy Models | `app/models/` |
| Pydantic Schemas | `app/schemas/` |
| Business Services | `app/services/` |
| Dashboard Pages | `frontend/src/app/dashboard/` |
| Storefront Pages | `frontend/src/app/(storefront)/` |
| API Clients | `frontend/src/lib/api/` |
| Navigation Config | `frontend/src/config/navigation.ts` |
| Types/Interfaces | `frontend/src/types/` |

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Backend API Files | 76 |
| SQLAlchemy Models | 58 |
| Pydantic Schemas | 65 |
| Business Services | 53 |
| Dashboard Sections | 26 |
| Storefront Pages | 15 |
| Frontend API Clients | 71 |
| Database Tables | 200+ |

---

*Last Updated: 2026-01-28*
