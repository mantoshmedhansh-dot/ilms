"""Service for tenant onboarding and registration."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, ErpModule, Plan, TenantSubscription
from app.core.security import get_password_hash, create_access_token
from app.config import settings
from app.services.tenant_schema_service import TenantSchemaService


class TenantOnboardingService:
    """Service for handling tenant registration and onboarding."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_subdomain_available(self, subdomain: str) -> Tuple[bool, Optional[str]]:
        """
        Check if subdomain is available.

        Returns:
            (is_available, message)
        """
        # Check if subdomain already exists
        stmt = select(Tenant).where(Tenant.subdomain == subdomain)
        result = await self.db.execute(stmt)
        existing_tenant = result.scalar_one_or_none()

        if existing_tenant:
            return False, f"Subdomain '{subdomain}' is already taken."

        return True, None

    async def get_available_modules(self) -> List[ErpModule]:
        """Get all available ERP modules."""
        stmt = select(ErpModule).where(ErpModule.is_active == True).order_by(ErpModule.display_order)
        result = await self.db.execute(stmt)
        modules = result.scalars().all()
        return list(modules)

    async def validate_module_codes(self, module_codes: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate that all provided module codes exist and are active.

        Returns:
            (is_valid, error_message)
        """
        # Get all active modules
        stmt = select(ErpModule).where(
            ErpModule.code.in_(module_codes),
            ErpModule.is_active == True
        )
        result = await self.db.execute(stmt)
        existing_modules = result.scalars().all()
        existing_codes = {m.code for m in existing_modules}

        # Check for invalid modules
        invalid_modules = set(module_codes) - existing_codes
        if invalid_modules:
            return False, f"Invalid module codes: {', '.join(invalid_modules)}"

        # Check dependencies
        for module in existing_modules:
            if module.dependencies:
                missing_deps = set(module.dependencies) - set(module_codes)
                if missing_deps:
                    return False, f"Module '{module.code}' requires: {', '.join(missing_deps)}"

        return True, None

    async def calculate_subscription_cost(
        self,
        module_codes: List[str],
        billing_cycle: str = "monthly"
    ) -> float:
        """
        Calculate total subscription cost for selected modules.

        Args:
            module_codes: List of module codes to subscribe to
            billing_cycle: "monthly" or "yearly"

        Returns:
            Total cost
        """
        stmt = select(ErpModule).where(
            ErpModule.code.in_(module_codes),
            ErpModule.is_active == True
        )
        result = await self.db.execute(stmt)
        modules = result.scalars().all()

        total_cost = sum(m.price_monthly or 0 for m in modules)

        # Apply yearly discount (e.g., 20% off)
        if billing_cycle == "yearly":
            total_cost = total_cost * 12 * 0.8  # 20% discount

        return total_cost

    async def create_tenant(
        self,
        company_name: str,
        subdomain: str,
        industry: Optional[str] = None,
        company_size: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Tenant:
        """
        Create a new tenant record.

        Args:
            company_name: Company/organization name
            subdomain: Unique subdomain for tenant
            industry: Industry/vertical
            company_size: Company size category
            country: Country code

        Returns:
            Created Tenant object
        """
        tenant = Tenant(
            id=uuid.uuid4(),
            name=company_name,
            subdomain=subdomain,
            database_schema=f"tenant_{subdomain}",
            status="pending",  # Will be activated after schema creation
            settings={
                "industry": industry,
                "company_size": company_size,
                "country": country,
            },
            tenant_metadata={}
        )

        self.db.add(tenant)
        await self.db.flush()  # Get tenant ID without committing

        return tenant

    async def create_subscriptions(
        self,
        tenant_id: uuid.UUID,
        module_codes: List[str],
        billing_cycle: str = "monthly"
    ) -> List[TenantSubscription]:
        """
        Create module subscriptions for a tenant.

        Args:
            tenant_id: Tenant UUID
            module_codes: List of module codes to subscribe to
            billing_cycle: "monthly" or "yearly"

        Returns:
            List of created TenantSubscription objects
        """
        # Get modules
        stmt = select(ErpModule).where(
            ErpModule.code.in_(module_codes),
            ErpModule.is_active == True
        )
        result = await self.db.execute(stmt)
        modules = result.scalars().all()

        # Create subscriptions
        subscriptions = []
        starts_at = datetime.now(timezone.utc)

        for module in modules:
            subscription = TenantSubscription(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                module_id=module.id,
                starts_at=starts_at,
                expires_at=None,  # No expiration for active subscriptions
                status="active",
                billing_cycle=billing_cycle,
                price_paid=float(module.price_monthly or 0)
            )
            subscriptions.append(subscription)
            self.db.add(subscription)

        await self.db.flush()

        return subscriptions

    async def generate_tokens(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        email: str
    ) -> Tuple[str, str, int]:
        """
        Generate JWT access and refresh tokens.

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            email: User email

        Returns:
            (access_token, refresh_token, expires_in)
        """
        # Additional claims for tokens
        access_claims = {
            "email": email,
            "tenant_id": str(tenant_id),
            "type": "access"
        }

        refresh_claims = {
            "email": email,
            "tenant_id": str(tenant_id),
            "type": "refresh"
        }

        # Generate tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user_id,
            expires_delta=access_token_expires,
            additional_claims=access_claims
        )

        refresh_token_expires = timedelta(days=7)  # 7 days for refresh token
        refresh_token = create_access_token(
            subject=user_id,
            expires_delta=refresh_token_expires,
            additional_claims=refresh_claims
        )

        return access_token, refresh_token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    async def register_tenant(
        self,
        company_name: str,
        subdomain: str,
        admin_email: str,
        admin_password: str,
        admin_first_name: str,
        admin_last_name: str,
        admin_phone: Optional[str],
        selected_modules: List[str],
        industry: Optional[str] = None,
        company_size: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Tuple[Tenant, uuid.UUID, str, str, int]:
        """
        Complete tenant registration flow (Phase 3A + 3B).

        This creates:
        1. Tenant record in public.tenants
        2. Module subscriptions
        3. Tenant database schema
        4. All ERP tables in tenant schema
        5. Default roles
        6. Admin user
        7. JWT tokens for immediate login

        Args:
            company_name: Company name
            subdomain: Unique subdomain
            admin_email: Admin user email
            admin_password: Admin user password
            admin_first_name: Admin first name
            admin_last_name: Admin last name
            admin_phone: Admin phone (optional)
            selected_modules: List of module codes
            industry: Industry (optional)
            company_size: Company size (optional)
            country: Country (optional)

        Returns:
            (tenant, admin_user_id, access_token, refresh_token, expires_in)
        """
        # 1. Check subdomain availability
        is_available, message = await self.check_subdomain_available(subdomain)
        if not is_available:
            raise ValueError(message)

        # 2. Validate modules
        is_valid, error_message = await self.validate_module_codes(selected_modules)
        if not is_valid:
            raise ValueError(error_message)

        # 3. Create tenant
        tenant = await self.create_tenant(
            company_name=company_name,
            subdomain=subdomain,
            industry=industry,
            company_size=company_size,
            country=country
        )

        # 4. Create subscriptions
        await self.create_subscriptions(
            tenant_id=tenant.id,
            module_codes=selected_modules,
            billing_cycle="monthly"
        )

        # 5. Commit tenant and subscriptions
        await self.db.commit()

        # 6. Create tenant schema and admin user (Phase 3B)
        schema_service = TenantSchemaService(self.db)
        admin_user_id = uuid.uuid4()
        admin_password_hash = get_password_hash(admin_password)

        try:
            await schema_service.complete_tenant_setup(
                tenant_id=tenant.id,
                schema_name=tenant.database_schema,
                admin_email=admin_email,
                admin_password_hash=admin_password_hash,
                admin_first_name=admin_first_name,
                admin_last_name=admin_last_name,
                admin_phone=admin_phone,
                admin_user_id=admin_user_id
            )
        except Exception as e:
            # If schema creation fails, mark tenant as failed and re-raise
            tenant.status = "failed"
            tenant.settings["setup_error"] = str(e)
            await self.db.commit()
            raise ValueError(f"Tenant setup failed: {e}")

        # 7. Generate tokens (using actual admin user ID)
        access_token, refresh_token, expires_in = await self.generate_tokens(
            tenant_id=tenant.id,
            user_id=admin_user_id,
            email=admin_email
        )

        return tenant, admin_user_id, access_token, refresh_token, expires_in
