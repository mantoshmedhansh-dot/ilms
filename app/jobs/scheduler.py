"""
APScheduler Configuration for Multi-Tenant SaaS

Background job scheduler with tenant-aware job execution.
All jobs run across all active tenants with proper schema isolation.

Architecture:
- Jobs are registered with @tenant_job decorator
- Scheduler triggers jobs at configured intervals
- TenantJobRunner iterates through all active tenants
- Each job runs in the correct tenant schema context
- Failures in one tenant don't affect others
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

logger = logging.getLogger(__name__)

# Job stores
jobstores = {
    'default': MemoryJobStore()
}

# Executors
executors = {
    'default': AsyncIOExecutor(),
}

# Job defaults
job_defaults = {
    'coalesce': True,  # Combine multiple pending executions into one
    'max_instances': 1,  # Only one instance of each job at a time
    'misfire_grace_time': 60,  # Allow 60 seconds grace time for misfires
}

# Create scheduler
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='Asia/Kolkata'
)


async def run_tenant_aware_job(job_name: str):
    """
    Wrapper to run a tenant-aware job from the scheduler.

    This function is called by APScheduler and delegates to the
    TenantJobRunner which handles iterating through all tenants.
    """
    from app.jobs.tenant_job_runner import run_tenant_job

    try:
        result = await run_tenant_job(job_name)
        logger.info(
            f"Job '{job_name}' completed: "
            f"{result.get('successful', 0)}/{result.get('tenant_count', 0)} tenants successful"
        )
    except Exception as e:
        logger.error(f"Job '{job_name}' failed: {e}")


def start_scheduler():
    """Start the background job scheduler with tenant-aware jobs."""
    if not scheduler.running:
        # Import tenant job runner to register jobs
        # This import triggers @tenant_job decorators
        from app.jobs import tenant_job_runner  # noqa: F401

        # ============================================================
        # TENANT-AWARE SCHEDULED JOBS
        # These jobs run across ALL active tenants
        # ============================================================

        # Sync inventory cache every 5 minutes (per tenant)
        scheduler.add_job(
            run_tenant_aware_job,
            'interval',
            minutes=5,
            args=['sync_inventory_cache'],
            id='sync_inventory_cache',
            name='[Multi-Tenant] Sync Inventory Cache',
            replace_existing=True,
        )

        # Refresh serviceability cache every 15 minutes (per tenant)
        scheduler.add_job(
            run_tenant_aware_job,
            'interval',
            minutes=15,
            args=['refresh_serviceability_cache'],
            id='refresh_serviceability_cache',
            name='[Multi-Tenant] Refresh Serviceability Cache',
            replace_existing=True,
        )

        # Check pending payments every 10 minutes (per tenant)
        scheduler.add_job(
            run_tenant_aware_job,
            'interval',
            minutes=10,
            args=['check_pending_payments'],
            id='check_pending_payments',
            name='[Multi-Tenant] Check Pending Payments',
            replace_existing=True,
        )

        # Process abandoned carts every hour (per tenant)
        scheduler.add_job(
            run_tenant_aware_job,
            'interval',
            hours=1,
            args=['process_abandoned_carts'],
            id='process_abandoned_carts',
            name='[Multi-Tenant] Process Abandoned Carts',
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Multi-tenant background job scheduler started")

        # Log all scheduled jobs
        jobs = scheduler.get_jobs()
        for job in jobs:
            logger.info(f"Scheduled job: {job.name} - Next run: {job.next_run_time}")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background job scheduler stopped")


def get_job_status():
    """Get status of all scheduled jobs."""
    jobs = scheduler.get_jobs()
    return [
        {
            'id': job.id,
            'name': job.name,
            'next_run_time': str(job.next_run_time) if job.next_run_time else None,
            'trigger': str(job.trigger),
        }
        for job in jobs
    ]
