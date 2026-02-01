"""
Background Jobs Module

Handles scheduled tasks for:
- Cache refresh (serviceability, products)
- Inventory sync
- Payment status checks
- Order processing
"""

from app.jobs.scheduler import scheduler, start_scheduler, shutdown_scheduler
from app.jobs.cache_jobs import refresh_serviceability_cache, warm_popular_pincodes

__all__ = [
    "scheduler",
    "start_scheduler",
    "shutdown_scheduler",
    "refresh_serviceability_cache",
    "warm_popular_pincodes",
]
