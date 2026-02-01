"""Seed initial data for testing."""
import asyncio
import sys
sys.path.insert(0, '/Users/mantosh/Consumer durable')

from datetime import datetime
import uuid

from app.database import async_session_factory
from app.core.security import get_password_hash
from app.models import (
    User, Role, RoleLevel, Permission, Module, Region, RegionType,
    Category, Brand, Product, ProductStatus, Warehouse, WarehouseType,
)


async def seed():
    """Seed initial data."""
    async with async_session_factory() as db:
        try:
            print("Seeding data...")

            # 1. Create Modules
            print("Creating modules...")
            modules_data = [
                {"name": "Dashboard", "code": "DASHBOARD"},
                {"name": "User Management", "code": "USER_MGMT"},
                {"name": "Role Management", "code": "ROLE_MGMT"},
                {"name": "Product Catalog", "code": "PRODUCTS"},
                {"name": "Orders", "code": "ORDERS"},
                {"name": "Inventory", "code": "INVENTORY"},
                {"name": "Service Management", "code": "SERVICE"},
                {"name": "Customer Management", "code": "CUSTOMERS"},
                {"name": "Reports", "code": "REPORTS"},
                {"name": "Settings", "code": "SETTINGS"},
            ]

            modules = {}
            for m in modules_data:
                module = Module(id=uuid.uuid4(), **m, is_active=True)
                db.add(module)
                modules[m["code"]] = module

            # 2. Create Regions
            print("Creating regions...")
            national = Region(
                id=uuid.uuid4(),
                name="India",
                code="IN",
                type=RegionType.COUNTRY,
                is_active=True
            )
            db.add(national)

            north = Region(
                id=uuid.uuid4(),
                name="North Region",
                code="NORTH",
                type=RegionType.ZONE,
                parent_id=national.id,
                is_active=True
            )
            db.add(north)

            delhi = Region(
                id=uuid.uuid4(),
                name="Delhi",
                code="DL",
                type=RegionType.STATE,
                parent_id=north.id,
                is_active=True
            )
            db.add(delhi)

            # 3. Create Permissions
            print("Creating permissions...")
            permissions = []
            permission_actions = ["view", "create", "update", "delete"]

            for module_code, module in modules.items():
                for action in permission_actions:
                    perm = Permission(
                        id=uuid.uuid4(),
                        code=f"{module_code}_{action.upper()}",
                        name=f"{action.title()} {module.name}",
                        module_id=module.id,
                        action=action,  # Required field
                        is_active=True
                    )
                    db.add(perm)
                    permissions.append(perm)

            # 4. Create Roles
            print("Creating roles...")
            super_admin = Role(
                id=uuid.uuid4(),
                name="Super Admin",
                code="SUPER_ADMIN",
                level=RoleLevel.SUPER_ADMIN,
                description="Full system access",
                is_system=True,
                is_active=True
            )
            db.add(super_admin)

            director = Role(
                id=uuid.uuid4(),
                name="Director",
                code="DIRECTOR",
                level=RoleLevel.DIRECTOR,
                description="Director level access",
                is_system=True,
                is_active=True
            )
            db.add(director)

            manager = Role(
                id=uuid.uuid4(),
                name="Manager",
                code="MANAGER",
                level=RoleLevel.MANAGER,
                description="Management access",
                is_active=True
            )
            db.add(manager)

            # 5. Create Admin User
            print("Creating admin user...")
            # Hash password using app's security module
            password = "Admin@123"
            password_hash = get_password_hash(password)

            admin_user = User(
                id=uuid.uuid4(),
                email="admin@consumer.com",
                password_hash=password_hash,
                first_name="Admin",
                last_name="User",
                phone="+919999000001",
                is_active=True,
                is_verified=True,
                department="Administration",
                designation="System Administrator",
                region_id=national.id
            )
            db.add(admin_user)

            # 6. Assign Role to Admin User
            from app.models.user import UserRole
            user_role = UserRole(
                id=uuid.uuid4(),
                user_id=admin_user.id,
                role_id=super_admin.id,
                assigned_at=datetime.utcnow()
            )
            db.add(user_role)

            # 7. Create Categories
            print("Creating categories...")
            water_purifiers = Category(
                id=uuid.uuid4(),
                name="Water Purifiers",
                slug="water-purifiers",
                is_active=True,
                sort_order=1
            )
            db.add(water_purifiers)

            air_purifiers = Category(
                id=uuid.uuid4(),
                name="Air Purifiers",
                slug="air-purifiers",
                is_active=True,
                sort_order=2
            )
            db.add(air_purifiers)

            # Sub-categories
            ro_systems = Category(
                id=uuid.uuid4(),
                name="RO Systems",
                slug="ro-systems",
                parent_id=water_purifiers.id,
                is_active=True,
                sort_order=1
            )
            db.add(ro_systems)

            uv_systems = Category(
                id=uuid.uuid4(),
                name="UV Systems",
                slug="uv-systems",
                parent_id=water_purifiers.id,
                is_active=True,
                sort_order=2
            )
            db.add(uv_systems)

            # 8. Create Brand
            print("Creating brand...")
            brand = Brand(
                id=uuid.uuid4(),
                name="AquaPure",
                slug="aquapure",
                is_active=True
            )
            db.add(brand)

            # 9. Create Products
            print("Creating products...")
            from decimal import Decimal

            product1 = Product(
                id=uuid.uuid4(),
                name="AquaPure RO Premium",
                slug="aquapure-ro-premium",
                sku="AP-RO-001",
                model_number="AP-RO-PREM-7L",
                short_description="7-stage RO water purifier with TDS controller",
                category_id=ro_systems.id,
                brand_id=brand.id,
                mrp=Decimal("19999.00"),
                selling_price=Decimal("14999.00"),
                warranty_months=24,
                status=ProductStatus.ACTIVE,
                is_active=True,
                is_featured=True
            )
            db.add(product1)

            product2 = Product(
                id=uuid.uuid4(),
                name="AquaPure UV Compact",
                slug="aquapure-uv-compact",
                sku="AP-UV-001",
                model_number="AP-UV-COMP-5L",
                short_description="Compact UV water purifier for municipal water",
                category_id=uv_systems.id,
                brand_id=brand.id,
                mrp=Decimal("9999.00"),
                selling_price=Decimal("7999.00"),
                warranty_months=12,
                status=ProductStatus.ACTIVE,
                is_active=True
            )
            db.add(product2)

            # 10. Create Warehouses
            print("Creating warehouses...")
            warehouse1 = Warehouse(
                id=uuid.uuid4(),
                name="Central Warehouse Delhi",
                code="WH-DEL-001",
                warehouse_type=WarehouseType.MAIN,
                address_line1="Industrial Area, Phase 1",
                city="Delhi",
                state="Delhi",
                pincode="110001",
                country="India",
                region_id=delhi.id,
                is_active=True
            )
            db.add(warehouse1)

            warehouse2 = Warehouse(
                id=uuid.uuid4(),
                name="Service Center Delhi",
                code="SC-DEL-001",
                warehouse_type=WarehouseType.SERVICE_CENTER,
                address_line1="Service Hub, Connaught Place",
                city="Delhi",
                state="Delhi",
                pincode="110001",
                country="India",
                region_id=delhi.id,
                is_active=True
            )
            db.add(warehouse2)

            await db.commit()
            print("Seed data created successfully!")
            print("\n=== Admin Credentials ===")
            print("Email: admin@consumer.com")
            print("Password: Admin@123")

        except Exception as e:
            await db.rollback()
            print(f"Error seeding data: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed())
