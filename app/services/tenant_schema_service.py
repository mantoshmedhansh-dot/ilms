"""Service for tenant database schema creation and management."""

import uuid
import logging
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import ProgrammingError

from app.database import engine, Base
from app.models.tenant import Tenant
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)


class TenantSchemaService:
    """Service for managing tenant database schemas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant_schema(self, schema_name: str) -> bool:
        """
        Create a new database schema for a tenant.

        Args:
            schema_name: Name of the schema to create (e.g., 'tenant_companyabc')

        Returns:
            True if schema was created, False if it already exists

        Raises:
            Exception: If schema creation fails
        """
        try:
            # Validate schema name to prevent SQL injection
            if not schema_name.startswith('tenant_'):
                raise ValueError("Schema name must start with 'tenant_'")

            if not schema_name.replace('_', '').replace('-', '').isalnum():
                raise ValueError("Schema name contains invalid characters")

            # Create schema
            await self.db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            await self.db.commit()

            logger.info(f"Schema '{schema_name}' created successfully")
            return True

        except ProgrammingError as e:
            if "already exists" in str(e):
                logger.warning(f"Schema '{schema_name}' already exists")
                return False
            raise

    async def create_tenant_tables(self, schema_name: str) -> bool:
        """
        Create essential auth tables in the tenant schema.

        Creates: users, roles, user_roles
        These are minimum tables needed for role seeding and admin user creation.

        Args:
            schema_name: Name of the tenant schema

        Returns:
            True if tables were created successfully
        """
        try:
            # Set search path to tenant schema
            await self.db.execute(text(f'SET search_path TO "{schema_name}"'))

            # Create roles table
            await self.db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS "{schema_name}".roles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT,
                    level VARCHAR(50) NOT NULL,
                    is_system BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            # Create users table
            await self.db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS "{schema_name}".users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(20),
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100),
                    avatar_url VARCHAR(500),
                    employee_code VARCHAR(50) UNIQUE,
                    department VARCHAR(100),
                    designation VARCHAR(100),
                    region_id UUID,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    last_login_at TIMESTAMPTZ
                )
            """))

            # Create user_roles table
            await self.db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS "{schema_name}".user_roles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES "{schema_name}".users(id) ON DELETE CASCADE,
                    role_id UUID NOT NULL REFERENCES "{schema_name}".roles(id) ON DELETE CASCADE,
                    assigned_by UUID REFERENCES "{schema_name}".users(id) ON DELETE SET NULL,
                    assigned_at TIMESTAMPTZ DEFAULT NOW(),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))

            # Create indexes
            await self.db.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_users_email ON "{schema_name}".users(email);
                CREATE INDEX IF NOT EXISTS idx_users_phone ON "{schema_name}".users(phone);
                CREATE INDEX IF NOT EXISTS idx_roles_code ON "{schema_name}".roles(code);
                CREATE INDEX IF NOT EXISTS idx_user_roles_user ON "{schema_name}".user_roles(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_roles_role ON "{schema_name}".user_roles(role_id);
            """))

            await self.db.commit()
            logger.info(f"Essential auth tables created in schema '{schema_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create tables in schema '{schema_name}': {e}")
            await self.db.rollback()
            raise

    async def seed_default_roles(self, schema_name: str) -> bool:
        """
        Seed default roles in tenant schema.

        Creates standard roles: Super Admin, Admin, Manager, User

        Args:
            schema_name: Name of the tenant schema

        Returns:
            True if roles were seeded successfully
        """
        try:
            # Set search path to tenant schema
            await self.db.execute(text(f'SET search_path TO "{schema_name}"'))

            # Default roles to create
            default_roles = [
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Super Admin',
                    'code': 'SUPER_ADMIN',
                    'description': 'Full system access',
                    'level': 'SUPER_ADMIN',
                    'is_system': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Admin',
                    'code': 'ADMIN',
                    'description': 'Administrative access',
                    'level': 'ADMIN',
                    'is_system': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Manager',
                    'code': 'MANAGER',
                    'description': 'Managerial access',
                    'level': 'MANAGER',
                    'is_system': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'User',
                    'code': 'USER',
                    'description': 'Standard user access',
                    'level': 'USER',
                    'is_system': True
                },
            ]

            # Insert roles
            for role in default_roles:
                insert_query = text(f"""
                    INSERT INTO "{schema_name}".roles
                    (id, name, code, description, level, is_system, created_at, updated_at)
                    VALUES
                    (:id, :name, :code, :description, :level, :is_system, NOW(), NOW())
                    ON CONFLICT (code) DO NOTHING
                """)
                await self.db.execute(insert_query, role)

            await self.db.commit()
            logger.info(f"Default roles seeded in schema '{schema_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to seed roles in schema '{schema_name}': {e}")
            raise

    async def create_admin_user(
        self,
        schema_name: str,
        user_id: uuid.UUID,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None
    ) -> bool:
        """
        Create admin user in tenant schema.

        Args:
            schema_name: Name of the tenant schema
            user_id: UUID for the user
            email: User email
            password_hash: Hashed password
            first_name: User first name
            last_name: User last name
            phone: User phone (optional)

        Returns:
            True if user was created successfully
        """
        try:
            # Set search path to tenant schema
            await self.db.execute(text(f'SET search_path TO "{schema_name}"'))

            # Create user
            insert_user_query = text(f"""
                INSERT INTO "{schema_name}".users
                (id, email, password_hash, first_name, last_name, phone,
                 employee_code, department, designation, is_active, is_verified, created_at, updated_at)
                VALUES
                (:id, :email, :password_hash, :first_name, :last_name, :phone,
                 'EMP001', 'Administration', 'System Administrator', TRUE, TRUE, NOW(), NOW())
                ON CONFLICT (email) DO NOTHING
            """)

            await self.db.execute(insert_user_query, {
                'id': str(user_id),
                'email': email,
                'password_hash': password_hash,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone
            })

            # Get Super Admin role ID
            role_query = text(f"""
                SELECT id FROM "{schema_name}".roles WHERE code = 'SUPER_ADMIN' LIMIT 1
            """)
            role_result = await self.db.execute(role_query)
            role_row = role_result.fetchone()

            if role_row:
                role_id = role_row[0]

                # Assign Super Admin role to user
                insert_user_role_query = text(f"""
                    INSERT INTO "{schema_name}".user_roles
                    (id, user_id, role_id, created_at)
                    VALUES
                    (:id, :user_id, :role_id, NOW())
                    ON CONFLICT DO NOTHING
                """)

                await self.db.execute(insert_user_role_query, {
                    'id': str(uuid.uuid4()),
                    'user_id': str(user_id),
                    'role_id': str(role_id)
                })

            await self.db.commit()
            logger.info(f"Admin user created in schema '{schema_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create admin user in schema '{schema_name}': {e}")
            raise

    async def complete_tenant_setup(
        self,
        tenant_id: uuid.UUID,
        schema_name: str,
        admin_email: str,
        admin_password_hash: str,
        admin_first_name: str,
        admin_last_name: str,
        admin_phone: Optional[str],
        admin_user_id: uuid.UUID
    ) -> bool:
        """
        Complete tenant setup: create schema, tables, seed data, create admin.

        This is the main orchestration method for Phase 3B.

        Args:
            tenant_id: Tenant UUID
            schema_name: Name of schema to create
            admin_email: Admin user email
            admin_password_hash: Hashed admin password
            admin_first_name: Admin first name
            admin_last_name: Admin last name
            admin_phone: Admin phone (optional)
            admin_user_id: Admin user UUID

        Returns:
            True if setup completed successfully
        """
        try:
            logger.info(f"Starting tenant setup for '{schema_name}'...")

            # Step 1: Create schema
            await self.create_tenant_schema(schema_name)

            # Step 2: Create auth tables (users, roles, user_roles)
            await self.create_tenant_tables(schema_name)

            # Step 2.5 (Phase 6): Operational tables are created on-demand
            # Creating 237 tables at once times out on Supabase
            # Tables will be created via migrations or when modules are activated
            logger.info(f"Skipping bulk table creation - using on-demand approach")

            # Step 3: Seed default roles
            await self.seed_default_roles(schema_name)

            # Step 4: Create admin user
            await self.create_admin_user(
                schema_name=schema_name,
                user_id=admin_user_id,
                email=admin_email,
                password_hash=admin_password_hash,
                first_name=admin_first_name,
                last_name=admin_last_name,
                phone=admin_phone
            )

            # Step 5: Update tenant status to 'active'
            update_tenant_query = text("""
                UPDATE public.tenants
                SET status = 'active', updated_at = NOW()
                WHERE id = :tenant_id
            """)
            await self.db.execute(update_tenant_query, {'tenant_id': str(tenant_id)})
            await self.db.commit()

            logger.info(f"Tenant setup completed for '{schema_name}'")
            return True

        except Exception as e:
            logger.error(f"Tenant setup failed for '{schema_name}': {e}")
            # Rollback on failure
            await self.db.rollback()
            raise

    async def create_all_operational_tables(self, schema_name: str) -> bool:
        """
        Create ALL operational tables in the tenant schema using SQLAlchemy models.

        This creates all 237 tables defined in the application's SQLAlchemy models.
        Includes: products, orders, inventory, finance, HR, CMS, etc.

        Args:
            schema_name: Name of the tenant schema

        Returns:
            True if tables were created successfully
        """
        try:
            logger.info(f"Creating operational tables in schema '{schema_name}'...")

            # Import models to ensure they're registered with Base.metadata
            from app import models  # noqa: F401

            # Create a connection with schema-specific search path
            async with engine.begin() as conn:
                # Set search path to tenant schema
                await conn.execute(text(f'SET search_path TO "{schema_name}"'))

                # Create all tables from SQLAlchemy metadata
                await conn.run_sync(Base.metadata.create_all)

            table_count = len(Base.metadata.tables)
            logger.info(f"Created {table_count} operational tables in schema '{schema_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create operational tables in schema '{schema_name}': {e}")
            raise

    async def drop_tenant_schema(self, schema_name: str) -> bool:
        """
        Drop a tenant schema (DANGER: This deletes all tenant data!).

        Use with extreme caution - only for testing or tenant deletion.

        Args:
            schema_name: Name of the schema to drop

        Returns:
            True if schema was dropped
        """
        try:
            # Validate schema name
            if not schema_name.startswith('tenant_'):
                raise ValueError("Can only drop schemas starting with 'tenant_'")

            await self.db.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
            await self.db.commit()

            logger.warning(f"Schema '{schema_name}' DROPPED (all data deleted)")
            return True

        except Exception as e:
            logger.error(f"Failed to drop schema '{schema_name}': {e}")
            raise
