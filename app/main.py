from contextlib import asynccontextmanager
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.database import init_db, async_session_factory
from app.jobs.scheduler import start_scheduler, shutdown_scheduler


async def auto_seed_admin():
    """
    DEPRECATED: This function is for single-tenant mode only.

    In multi-tenant mode, admin users are created per-tenant during
    the onboarding process (see TenantSchemaService.create_admin_user).

    This function is kept for backwards compatibility but skips execution
    in multi-tenant deployments (when tenants table exists).
    """
    from sqlalchemy import select, func, text
    from sqlalchemy.exc import ProgrammingError

    try:
        async with async_session_factory() as session:
            # Check if this is a multi-tenant deployment
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM public.tenants")
                )
                tenant_count = result.scalar() or 0

                if tenant_count > 0:
                    print(f"Multi-tenant mode detected ({tenant_count} tenants). "
                          f"Skipping auto-seed - admins created during onboarding.")
                    return
            except ProgrammingError:
                # tenants table doesn't exist - this is single-tenant mode
                pass

            # Single-tenant mode: check if users table exists and seed admin
            try:
                from app.models.user import User, UserRole
                from app.models.role import Role, RoleLevel
                from app.core.security import get_password_hash

                result = await session.execute(select(func.count(User.id)))
                user_count = result.scalar()

                if user_count == 0:
                    print("No users found. Creating admin user...")

                    # First, ensure super_admin role exists
                    role_result = await session.execute(
                        select(Role).where(Role.code == "super_admin")
                    )
                    role = role_result.scalar_one_or_none()

                    if not role:
                        role = Role(
                            name="Super Admin",
                            code="super_admin",
                            description="Full system access",
                            level=RoleLevel.SUPER_ADMIN,
                            is_system=True,
                        )
                        session.add(role)
                        await session.flush()
                        print("  Created super_admin role")

                    # Create admin user
                    admin = User(
                        email="admin@ilms.ai",
                        phone="+919999999999",
                        password_hash=get_password_hash("Admin@123"),
                        first_name="Super",
                        last_name="Admin",
                        employee_code="EMP001",
                        department="Administration",
                        designation="System Administrator",
                        is_active=True,
                        is_verified=True,
                    )
                    session.add(admin)
                    await session.flush()

                    # Assign role
                    user_role = UserRole(user_id=admin.id, role_id=role.id)
                    session.add(user_role)

                    await session.commit()
                    print(f"  Created admin user: admin@ilms.ai / Admin@123")
                else:
                    print(f"Found {user_count} existing users. Skipping auto-seed.")

            except ProgrammingError as e:
                if "does not exist" in str(e):
                    print("Users table not found (multi-tenant setup). Skipping auto-seed.")
                else:
                    raise

    except Exception as e:
        import traceback
        print(f"Auto-seed error: {e}")
        traceback.print_exc()


async def auto_link_vendors_to_supplier_codes():
    """Auto-link vendors to supplier codes if not already linked."""
    from sqlalchemy import select
    from app.models.vendor import Vendor
    from app.models.serialization import SupplierCode
    import uuid

    print("AUTO-LINK: Starting vendor-supplier code linking...")

    try:
        async with async_session_factory() as db:
            # Find vendors that match known supplier codes but aren't linked
            vendor_mappings = [
                ("STOS", "ST"),  # STOS Industrial -> ST supplier code
            ]

            for vendor_pattern, supplier_code in vendor_mappings:
                print(f"AUTO-LINK: Checking {vendor_pattern} -> {supplier_code}")

                # Check if supplier code exists and is linked
                sc_result = await db.execute(
                    select(SupplierCode).where(SupplierCode.code == supplier_code)
                )
                sc = sc_result.scalar_one_or_none()
                print(f"AUTO-LINK: Supplier code '{supplier_code}' exists: {sc is not None}, vendor_id: {sc.vendor_id if sc else 'N/A'}")

                if sc and sc.vendor_id:
                    print(f"AUTO-LINK: '{supplier_code}' already linked to vendor_id={sc.vendor_id}")
                    continue

                # Find vendor
                vendor_result = await db.execute(
                    select(Vendor).where(Vendor.name.ilike(f"%{vendor_pattern}%"))
                )
                vendor = vendor_result.scalar_one_or_none()
                print(f"AUTO-LINK: Vendor matching '{vendor_pattern}': {vendor.name if vendor else 'NOT FOUND'}")

                if not vendor:
                    print(f"AUTO-LINK: No vendor found matching '{vendor_pattern}', skipping")
                    continue

                # Check if vendor already linked to another code
                existing_link = await db.execute(
                    select(SupplierCode).where(SupplierCode.vendor_id == vendor.id)
                )
                existing_sc = existing_link.scalar_one_or_none()
                if existing_sc:
                    print(f"AUTO-LINK: Vendor already linked to code '{existing_sc.code}', skipping")
                    continue

                if sc:
                    # Link existing supplier code to vendor
                    sc.vendor_id = vendor.id
                    print(f"AUTO-LINK: SUCCESS - Linked vendor '{vendor.name}' to supplier code '{supplier_code}'")
                else:
                    # Create new supplier code
                    new_sc = SupplierCode(
                        id=uuid.uuid4(),
                        code=supplier_code,
                        name=vendor.name,
                        vendor_id=vendor.id,
                        description=f"Auto-linked to {vendor.name}",
                        is_active=True,
                    )
                    db.add(new_sc)
                    print(f"AUTO-LINK: SUCCESS - Created supplier code '{supplier_code}' for vendor '{vendor.name}'")

            await db.commit()
            print("AUTO-LINK: Completed successfully")
    except Exception as e:
        import traceback
        print(f"AUTO-LINK ERROR: {type(e).__name__}: {e}")
        print(f"AUTO-LINK TRACEBACK: {traceback.format_exc()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for multi-tenant SaaS.

    Startup:
    - Initialize PUBLIC schema (tenants, modules, plans)
    - Seed default modules
    - Start background scheduler

    Note: Tenant schemas are created dynamically during onboarding (Phase 3B)
    """
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Phase 3E: Optimized multi-tenant startup
    from app.database_init import startup_initialization
    await startup_initialization()

    # Start background job scheduler
    start_scheduler()
    print("Background scheduler started")

    yield

    # Shutdown
    shutdown_scheduler()
    print("Shutting down...")


# OpenAPI Tags with detailed descriptions
OPENAPI_TAGS = [
    {"name": "Authentication", "description": "JWT-based authentication with access/refresh tokens"},
    {"name": "Users", "description": "User management with role assignments"},
    {"name": "Roles", "description": "Role-based access control (RBAC) management"},
    {"name": "Permissions", "description": "Granular permission management"},
    {"name": "Products", "description": "Product catalog with variants, specifications, and images"},
    {"name": "Categories", "description": "Hierarchical product categories"},
    {"name": "Brands", "description": "Brand management"},
    {"name": "Orders", "description": "Order management, status tracking, and fulfillment"},
    {"name": "Customers", "description": "Customer profiles, addresses, and communication"},
    {"name": "Inventory", "description": "Stock management, movements, and reservations"},
    {"name": "Warehouses", "description": "Warehouse and storage location management"},
    {"name": "Stock Transfers", "description": "Inter-warehouse stock transfers"},
    {"name": "Vendors/Suppliers", "description": "Vendor management and ledger"},
    {"name": "Purchase/Procurement", "description": "Purchase orders and procurement workflow"},
    {"name": "Goods Receipt Notes", "description": "GRN processing and quality checks"},
    {"name": "Billing/E-Invoice", "description": "GST-compliant invoicing with e-invoice and e-way bill"},
    {"name": "GST e-Filing & ITC", "description": "GSTR-1, GSTR-3B filing and ITC management"},
    {"name": "Banking/Reconciliation", "description": "Bank statement import and ML-powered reconciliation"},
    {"name": "Accounting", "description": "General ledger, journal entries, and financial reports"},
    {"name": "Service Requests", "description": "Service and warranty management"},
    {"name": "Technicians", "description": "Technician assignment and scheduling"},
    {"name": "Shipments", "description": "Shipment creation, tracking, and E-Way Bill integration"},
    {"name": "AI Services", "description": "AI-powered forecasting and analytics"},
    {"name": "S&OP (Sales & Operations Planning)", "description": "Demand forecasting and scenario planning"},
]

FULL_API_DESCRIPTION = """
## ILMS.AI ERP API v2.0

A comprehensive **Consumer Durable ERP System** with full GST compliance for water purifier manufacturing and distribution.

### Core Modules

| Module | Description |
|--------|-------------|
| **Authentication** | JWT-based auth with access/refresh tokens |
| **RBAC** | Hierarchical roles with granular permissions |
| **Product Catalog** | Products, variants, categories, brands |
| **Orders** | Multi-channel order management |
| **Inventory** | Real-time stock tracking with serialization |
| **Procurement** | P2P cycle with 3-way matching |
| **Finance** | GL, invoicing, banking, GST compliance |
| **Logistics** | Shipments, manifests, E-Way Bill |
| **Service** | Service requests, warranty, AMC |

### GST Compliance Features

- **E-Invoice**: IRN generation via NIC portal
- **E-Way Bill**: Automatic generation for goods > ₹50,000
- **GSTR-1**: Outward supplies auto-filing
- **GSTR-3B**: Summary return filing
- **ITC Management**: GSTR-2A/2B reconciliation

### AI & Analytics

- **Demand Forecasting**: Holt-Winters, ensemble methods
- **External Factors**: Weather, promotions, festivals
- **Bank Reconciliation**: ML-powered auto-matching

### Authentication

All endpoints (except `/storefront/*`) require JWT authentication.
Include token in Authorization header: `Bearer <token>`

### Rate Limiting

- Standard: 100 requests/minute
- Bulk operations: 10 requests/minute

### Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Validation failed |
| 401 | Unauthorized - Invalid/expired token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Duplicate resource |
| 422 | Unprocessable Entity - Business rule violation |
| 500 | Internal Server Error |

### Support

- **API Docs**: /docs (Swagger UI)
- **ReDoc**: /redoc (Alternative docs)
- **Health Check**: /health
"""

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=FULL_API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters={
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add tenant middleware for multi-tenant support
from app.middleware.tenant import tenant_middleware
app.middleware("http")(tenant_middleware)

# Include API router
app.include_router(api_router)


# Global exception handler to return detailed error for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return detailed error information for debugging."""
    from fastapi import HTTPException

    # Preserve HTTP status code for HTTPException, default to 500 for others
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        error_message = exc.detail
    else:
        status_code = 500
        error_message = str(exc)

    error_detail = {
        "error": error_message,
        "type": type(exc).__name__,
        "path": str(request.url.path),
        "method": request.method,
        "traceback": traceback.format_exc()
    }
    # Get origin from request
    origin = request.headers.get("origin", "")

    # Build response with CORS headers for error responses
    response = JSONResponse(
        status_code=status_code,
        content=error_detail
    )

    # Add CORS headers if origin is allowed
    if origin in settings.cors_origins_list or "*" in settings.cors_origins_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint with database validation."""
    from sqlalchemy import text
    from datetime import datetime, timezone

    health_status = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": "unknown"
        }
    }

    # Check database connectivity
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"

    # Return 503 if unhealthy
    if health_status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health_status)

    return health_status


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }
