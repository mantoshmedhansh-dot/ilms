"""
Tenant-Aware Job Runner for Multi-Tenant SaaS

This module provides the infrastructure to run background jobs
across all active tenants safely. Each job executes within the
correct tenant schema context.

Architecture:
- Jobs are registered with the TenantJobRunner
- Runner iterates through all active tenants
- Each job runs with proper schema isolation
- Failures in one tenant don't affect others
- Comprehensive logging for debugging

Usage:
    @tenant_job("sync_inventory")
    async def sync_inventory(session, tenant):
        # This runs within tenant's schema context
        result = await session.execute(text("SELECT * FROM inventory"))
        ...
"""

import logging
import asyncio
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime, timezone
from functools import wraps

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Registry of tenant-aware jobs
_tenant_jobs: Dict[str, Callable] = {}


def tenant_job(name: str):
    """
    Decorator to register a tenant-aware background job.

    The decorated function receives:
    - session: AsyncSession configured for the tenant's schema
    - tenant: Tenant object with id, subdomain, schema name, etc.

    Example:
        @tenant_job("sync_inventory")
        async def sync_inventory(session: AsyncSession, tenant: dict):
            result = await session.execute(
                text("SELECT COUNT(*) FROM inventory")
            )
            count = result.scalar()
            logger.info(f"Tenant {tenant['subdomain']}: {count} inventory items")
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(session: AsyncSession, tenant: dict):
            return await func(session, tenant)

        _tenant_jobs[name] = wrapper
        logger.debug(f"Registered tenant job: {name}")
        return wrapper
    return decorator


class TenantJobRunner:
    """
    Executes background jobs across all active tenants.

    Features:
    - Automatic tenant iteration
    - Schema isolation per tenant
    - Error isolation (one tenant failure doesn't affect others)
    - Execution metrics and logging
    - Configurable concurrency
    """

    def __init__(self, max_concurrent: int = 5):
        """
        Initialize the job runner.

        Args:
            max_concurrent: Max tenants to process concurrently
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def get_active_tenants(self) -> List[dict]:
        """
        Fetch all active tenants from the database.

        Returns:
            List of tenant dictionaries with id, subdomain, database_schema
        """
        from app.database import async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        name,
                        subdomain,
                        database_schema,
                        status,
                        settings
                    FROM public.tenants
                    WHERE status = 'active'
                    ORDER BY created_at
                """)
            )
            rows = result.fetchall()

            return [
                {
                    "id": str(row.id),
                    "name": row.name,
                    "subdomain": row.subdomain,
                    "database_schema": row.database_schema,
                    "status": row.status,
                    "settings": row.settings or {}
                }
                for row in rows
            ]

    async def run_job_for_tenant(
        self,
        job_name: str,
        job_func: Callable,
        tenant: dict
    ) -> dict:
        """
        Execute a job for a single tenant.

        Args:
            job_name: Name of the job
            job_func: The job function to execute
            tenant: Tenant dictionary

        Returns:
            Result dictionary with status and metrics
        """
        from app.database import engine

        schema = tenant["database_schema"]
        subdomain = tenant["subdomain"]
        start_time = datetime.now(timezone.utc)

        result = {
            "tenant_id": tenant["id"],
            "subdomain": subdomain,
            "job": job_name,
            "status": "pending",
            "started_at": start_time.isoformat(),
            "error": None,
            "duration_ms": 0
        }

        try:
            async with self._semaphore:
                # Create connection with tenant schema
                async with engine.connect() as conn:
                    # Set search path to tenant schema
                    await conn.execute(text(f'SET search_path TO "{schema}"'))

                    # Create session from connection
                    session = AsyncSession(bind=conn, expire_on_commit=False)

                    try:
                        # Execute the job
                        await job_func(session, tenant)
                        await session.commit()
                        result["status"] = "success"

                    except Exception as e:
                        await session.rollback()
                        raise
                    finally:
                        await session.close()

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(
                f"Job '{job_name}' failed for tenant '{subdomain}': {e}"
            )

        end_time = datetime.now(timezone.utc)
        result["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
        result["completed_at"] = end_time.isoformat()

        return result

    async def run_job(self, job_name: str) -> dict:
        """
        Run a job across all active tenants.

        Args:
            job_name: Name of the registered job

        Returns:
            Summary dictionary with results per tenant
        """
        if job_name not in _tenant_jobs:
            raise ValueError(f"Unknown job: {job_name}. Registered: {list(_tenant_jobs.keys())}")

        job_func = _tenant_jobs[job_name]
        start_time = datetime.now(timezone.utc)

        logger.info(f"Starting tenant job: {job_name}")

        # Get all active tenants
        tenants = await self.get_active_tenants()

        if not tenants:
            logger.info(f"No active tenants found. Job '{job_name}' skipped.")
            return {
                "job": job_name,
                "status": "skipped",
                "reason": "no_active_tenants",
                "tenant_count": 0
            }

        logger.info(f"Running '{job_name}' for {len(tenants)} tenants")

        # Run job for all tenants concurrently (with semaphore limiting)
        tasks = [
            self.run_job_for_tenant(job_name, job_func, tenant)
            for tenant in tenants
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
        failed = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "failed")

        end_time = datetime.now(timezone.utc)
        total_duration = int((end_time - start_time).total_seconds() * 1000)

        summary = {
            "job": job_name,
            "status": "completed",
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_ms": total_duration,
            "tenant_count": len(tenants),
            "successful": successful,
            "failed": failed,
            "results": [r for r in results if isinstance(r, dict)]
        }

        logger.info(
            f"Job '{job_name}' completed: {successful}/{len(tenants)} successful "
            f"in {total_duration}ms"
        )

        return summary


# Global runner instance
_runner: Optional[TenantJobRunner] = None


def get_tenant_job_runner() -> TenantJobRunner:
    """Get or create the global tenant job runner."""
    global _runner
    if _runner is None:
        _runner = TenantJobRunner()
    return _runner


async def run_tenant_job(job_name: str) -> dict:
    """
    Convenience function to run a tenant job.

    Args:
        job_name: Name of the registered job

    Returns:
        Job execution summary
    """
    runner = get_tenant_job_runner()
    return await runner.run_job(job_name)


# ============================================================
# TENANT-AWARE JOB IMPLEMENTATIONS
# ============================================================

@tenant_job("sync_inventory_cache")
async def sync_inventory_cache_job(session: AsyncSession, tenant: dict):
    """
    Sync inventory levels to cache for a tenant.

    This replaces the old single-tenant sync_inventory_cache function.
    """
    from sqlalchemy.exc import ProgrammingError

    try:
        result = await session.execute(
            text("""
                SELECT
                    product_id::text,
                    sku,
                    quantity_available,
                    reserved_quantity,
                    warehouse_id::text
                FROM inventory
                WHERE is_active = true
            """)
        )
        rows = result.fetchall()

        # TODO: Update Redis/in-memory cache for this tenant
        # For now, just log the count
        logger.info(
            f"Tenant '{tenant['subdomain']}': Found {len(rows)} inventory items"
        )

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': inventory table not yet created"
            )
        else:
            raise


@tenant_job("check_pending_payments")
async def check_pending_payments_job(session: AsyncSession, tenant: dict):
    """
    Check pending payments for a tenant.

    This replaces the old single-tenant check_pending_payments function.
    """
    from sqlalchemy.exc import ProgrammingError
    from datetime import timedelta

    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        result = await session.execute(
            text("""
                SELECT COUNT(*)
                FROM orders
                WHERE payment_status = 'PENDING'
                AND created_at < :cutoff_time
            """),
            {"cutoff_time": cutoff_time}
        )
        pending_count = result.scalar() or 0

        if pending_count > 0:
            logger.info(
                f"Tenant '{tenant['subdomain']}': {pending_count} pending payments to check"
            )
            # TODO: Implement actual Razorpay check logic here

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': orders table not yet created"
            )
        else:
            raise


@tenant_job("process_abandoned_carts")
async def process_abandoned_carts_job(session: AsyncSession, tenant: dict):
    """
    Process abandoned carts for a tenant.
    """
    from sqlalchemy.exc import ProgrammingError
    from datetime import timedelta

    try:
        abandoned_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        result = await session.execute(
            text("""
                SELECT COUNT(*)
                FROM carts
                WHERE updated_at < :cutoff
                AND is_active = true
            """),
            {"cutoff": abandoned_cutoff}
        )
        abandoned_count = result.scalar() or 0

        if abandoned_count > 0:
            logger.info(
                f"Tenant '{tenant['subdomain']}': {abandoned_count} abandoned carts"
            )
            # TODO: Implement cart reminder logic

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': carts table not yet created"
            )
        else:
            raise


@tenant_job("refresh_serviceability_cache")
async def refresh_serviceability_cache_job(session: AsyncSession, tenant: dict):
    """
    Refresh serviceability cache for a tenant.
    """
    from sqlalchemy.exc import ProgrammingError

    try:
        result = await session.execute(
            text("""
                SELECT COUNT(*)
                FROM warehouse_serviceability
                WHERE is_active = true
            """)
        )
        count = result.scalar() or 0

        logger.info(
            f"Tenant '{tenant['subdomain']}': {count} serviceable pincodes"
        )
        # TODO: Update cache

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': warehouse_serviceability not yet created"
            )
        else:
            raise
