"""
APScheduler Configuration

Background job scheduler for periodic tasks.
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


def start_scheduler():
    """Start the background job scheduler."""
    if not scheduler.running:
        # Import jobs here to avoid circular imports
        from app.jobs.cache_jobs import (
            refresh_serviceability_cache,
            warm_popular_pincodes,
            sync_inventory_cache,
        )
        from app.jobs.order_jobs import (
            check_pending_payments,
            process_abandoned_carts,
        )

        # Add scheduled jobs

        # Cache refresh every 15 minutes
        scheduler.add_job(
            refresh_serviceability_cache,
            'interval',
            minutes=15,
            id='refresh_serviceability_cache',
            name='Refresh Serviceability Cache',
            replace_existing=True,
        )

        # Warm popular pincodes every 30 minutes
        scheduler.add_job(
            warm_popular_pincodes,
            'interval',
            minutes=30,
            id='warm_popular_pincodes',
            name='Warm Popular Pincodes Cache',
            replace_existing=True,
        )

        # Sync inventory cache every 5 minutes
        scheduler.add_job(
            sync_inventory_cache,
            'interval',
            minutes=5,
            id='sync_inventory_cache',
            name='Sync Inventory Cache',
            replace_existing=True,
        )

        # Check pending payments every 10 minutes
        scheduler.add_job(
            check_pending_payments,
            'interval',
            minutes=10,
            id='check_pending_payments',
            name='Check Pending Payments',
            replace_existing=True,
        )

        # Process abandoned carts every hour
        scheduler.add_job(
            process_abandoned_carts,
            'interval',
            hours=1,
            id='process_abandoned_carts',
            name='Process Abandoned Carts',
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Background job scheduler started")

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
