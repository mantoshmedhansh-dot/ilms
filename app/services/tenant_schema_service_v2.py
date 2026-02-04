"""
Tenant Schema Service V2 - Structural Solution

This service manages tenant database schemas using the centralized
schema definition. All schema creation, validation, and repair
operations use the single source of truth.
"""

import uuid
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_schema_definition import (
    TENANT_SCHEMA_TABLES,
    Table,
    get_table_by_name,
    get_all_table_names,
)
from app.services.tenant_schema_validator import (
    TenantSchemaValidator,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class TenantSchemaServiceV2:
    """
    Enhanced tenant schema service with structural validation.

    Key improvements over V1:
    1. Uses centralized schema definition (single source of truth)
    2. Validates schema after creation
    3. Can auto-repair schema issues
    4. Comprehensive error handling
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.validator = TenantSchemaValidator(db)

    async def create_tenant_schema(
        self,
        schema_name: str,
        validate_after: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new tenant schema with all required tables.

        Args:
            schema_name: Name of schema (must start with 'tenant_')
            validate_after: Whether to validate schema after creation

        Returns:
            Dictionary with creation results
        """
        # Validate schema name
        if not schema_name.startswith('tenant_'):
            raise ValueError("Schema name must start with 'tenant_'")

        if not schema_name.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Schema name contains invalid characters")

        result = {
            "schema_name": schema_name,
            "tables_created": [],
            "tables_failed": [],
            "indexes_created": [],
            "validation": None,
            "success": False
        }

        try:
            # Step 1: Create schema
            await self.db.execute(
                text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
            )
            logger.info(f"Created schema: {schema_name}")

            # Step 2: Create all tables in order
            for table_def in TENANT_SCHEMA_TABLES:
                try:
                    create_sql = table_def.to_create_sql(schema_name)
                    await self.db.execute(text(create_sql))
                    result["tables_created"].append(table_def.name)
                    logger.info(f"Created table: {schema_name}.{table_def.name}")

                    # Create indexes
                    for idx_sql in table_def.get_index_sql(schema_name):
                        try:
                            await self.db.execute(text(idx_sql))
                            result["indexes_created"].append(idx_sql.split(" ")[-1])
                        except Exception as idx_err:
                            logger.warning(f"Index creation failed: {idx_err}")

                except Exception as table_err:
                    logger.error(f"Failed to create {table_def.name}: {table_err}")
                    result["tables_failed"].append({
                        "table": table_def.name,
                        "error": str(table_err)
                    })

            await self.db.commit()

            # Step 3: Validate schema if requested
            if validate_after:
                validation = await self.validator.validate_schema(schema_name)
                result["validation"] = validation.to_dict()

                # Auto-fix any issues found
                if not validation.is_valid:
                    logger.warning(
                        f"Schema {schema_name} has issues after creation, auto-fixing..."
                    )
                    fix_result = await self.validator.fix_schema(schema_name)
                    result["auto_fix"] = fix_result

            result["success"] = len(result["tables_failed"]) == 0
            return result

        except Exception as e:
            logger.error(f"Schema creation failed for {schema_name}: {e}")
            await self.db.rollback()
            raise

    async def seed_default_roles(self, schema_name: str) -> List[str]:
        """
        Seed default roles in tenant schema.

        Returns:
            List of role codes created
        """
        roles_created = []

        default_roles = [
            {
                'name': 'Super Admin',
                'code': 'SUPER_ADMIN',
                'description': 'Full system access',
                'level': 'SUPER_ADMIN',
                'is_system': True
            },
            {
                'name': 'Admin',
                'code': 'ADMIN',
                'description': 'Administrative access',
                'level': 'ADMIN',
                'is_system': True
            },
            {
                'name': 'Manager',
                'code': 'MANAGER',
                'description': 'Managerial access',
                'level': 'MANAGER',
                'is_system': True
            },
            {
                'name': 'User',
                'code': 'USER',
                'description': 'Standard user access',
                'level': 'USER',
                'is_system': True
            },
        ]

        for role in default_roles:
            try:
                await self.db.execute(text(f"""
                    INSERT INTO "{schema_name}".roles
                    (id, name, code, description, level, is_system, created_at, updated_at)
                    VALUES
                    (gen_random_uuid(), :name, :code, :description, :level, :is_system, NOW(), NOW())
                    ON CONFLICT (code) DO NOTHING
                """), role)
                roles_created.append(role['code'])
            except Exception as e:
                logger.error(f"Failed to create role {role['code']}: {e}")

        await self.db.commit()
        logger.info(f"Seeded {len(roles_created)} roles in {schema_name}")
        return roles_created

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

        Returns:
            True if user was created successfully
        """
        try:
            # Create user
            await self.db.execute(text(f"""
                INSERT INTO "{schema_name}".users
                (id, email, password_hash, first_name, last_name, phone,
                 employee_code, department, designation, is_active, is_verified,
                 created_at, updated_at)
                VALUES
                (:id, :email, :password_hash, :first_name, :last_name, :phone,
                 'EMP001', 'Administration', 'System Administrator', TRUE, TRUE,
                 NOW(), NOW())
                ON CONFLICT (email) DO NOTHING
            """), {
                'id': str(user_id),
                'email': email,
                'password_hash': password_hash,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone
            })

            # Get Super Admin role
            role_result = await self.db.execute(text(f"""
                SELECT id FROM "{schema_name}".roles WHERE code = 'SUPER_ADMIN' LIMIT 1
            """))
            role_row = role_result.fetchone()

            if role_row:
                # Assign role
                await self.db.execute(text(f"""
                    INSERT INTO "{schema_name}".user_roles
                    (id, user_id, role_id, created_at)
                    VALUES (gen_random_uuid(), :user_id, :role_id, NOW())
                    ON CONFLICT DO NOTHING
                """), {'user_id': str(user_id), 'role_id': str(role_row[0])})

            await self.db.commit()
            logger.info(f"Created admin user {email} in {schema_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
            await self.db.rollback()
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
    ) -> Dict[str, Any]:
        """
        Complete tenant setup with validation.

        This is the main orchestration method that:
        1. Creates schema with all tables
        2. Validates schema structure
        3. Seeds default roles
        4. Creates admin user
        5. Updates tenant status

        Returns:
            Dictionary with setup results
        """
        result = {
            "tenant_id": str(tenant_id),
            "schema_name": schema_name,
            "steps_completed": [],
            "success": False
        }

        try:
            logger.info(f"Starting tenant setup for {schema_name}...")

            # Step 1: Create schema with tables
            schema_result = await self.create_tenant_schema(
                schema_name, validate_after=True
            )
            result["schema_creation"] = schema_result
            result["steps_completed"].append("schema_created")

            # Step 2: Seed default roles
            roles = await self.seed_default_roles(schema_name)
            result["roles_created"] = roles
            result["steps_completed"].append("roles_seeded")

            # Step 3: Create admin user
            await self.create_admin_user(
                schema_name=schema_name,
                user_id=admin_user_id,
                email=admin_email,
                password_hash=admin_password_hash,
                first_name=admin_first_name,
                last_name=admin_last_name,
                phone=admin_phone
            )
            result["steps_completed"].append("admin_created")

            # Step 4: Final validation
            final_validation = await self.validator.validate_schema(schema_name)
            result["final_validation"] = final_validation.to_dict()

            if not final_validation.is_valid:
                logger.warning(f"Final validation failed, attempting auto-fix...")
                fix_result = await self.validator.fix_schema(schema_name)
                result["auto_fix"] = fix_result

            # Step 5: Update tenant status
            await self.db.execute(text("""
                UPDATE public.tenants
                SET status = 'active', updated_at = NOW()
                WHERE id = :tenant_id
            """), {'tenant_id': str(tenant_id)})
            await self.db.commit()
            result["steps_completed"].append("tenant_activated")

            result["success"] = True
            logger.info(f"Tenant setup completed for {schema_name}")

        except Exception as e:
            logger.error(f"Tenant setup failed for {schema_name}: {e}")
            await self.db.rollback()
            result["error"] = str(e)
            raise

        return result

    async def validate_and_repair(
        self, schema_name: str, auto_fix: bool = True
    ) -> Dict[str, Any]:
        """
        Validate tenant schema and optionally repair issues.

        Args:
            schema_name: Tenant schema name
            auto_fix: Whether to automatically fix issues

        Returns:
            Validation and repair results
        """
        validation = await self.validator.validate_schema(schema_name)
        result = {
            "validation": validation.to_dict(),
            "repairs": None
        }

        if not validation.is_valid and auto_fix:
            repair_result = await self.validator.fix_schema(schema_name)
            result["repairs"] = repair_result

            # Re-validate after repairs
            post_repair = await self.validator.validate_schema(schema_name)
            result["post_repair_validation"] = post_repair.to_dict()

        return result
