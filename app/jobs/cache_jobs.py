"""
Cache Management Jobs

Background jobs for managing serviceability cache, inventory sync,
and warming popular pincode caches.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# In-memory cache for serviceability (fallback when Redis is unavailable)
_serviceability_cache: Dict[str, Any] = {}
_inventory_cache: Dict[str, int] = {}
_cache_last_updated: datetime = None

# Popular pincodes to pre-warm (high traffic areas)
POPULAR_PINCODES = [
    # Delhi NCR
    "110001", "110002", "110003", "110005", "110006",
    "122001", "122002", "122003", "122004", "122005",  # Gurgaon
    "201301", "201302", "201303", "201304", "201305",  # Noida
    # Mumbai
    "400001", "400002", "400003", "400050", "400051",
    "400053", "400054", "400055", "400056", "400057",
    # Bangalore
    "560001", "560002", "560003", "560004", "560005",
    "560008", "560009", "560010", "560011", "560012",
    # Chennai
    "600001", "600002", "600003", "600004", "600005",
    # Kolkata
    "700001", "700002", "700003", "700004", "700005",
    # Hyderabad
    "500001", "500002", "500003", "500004", "500005",
    # Pune
    "411001", "411002", "411003", "411004", "411005",
]


async def get_redis_client():
    """Get Redis client with fallback handling."""
    try:
        import redis.asyncio as redis
        from app.config import settings

        client = redis.from_url(
            settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )
        # Test connection
        await client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis connection failed, using in-memory cache: {e}")
        return None


async def refresh_serviceability_cache():
    """
    Refresh serviceability cache from database.

    This job runs every 15 minutes to keep the cache fresh.
    Fetches all serviceable pincodes and their delivery estimates
    from the database and updates Redis/in-memory cache.
    """
    global _serviceability_cache, _cache_last_updated

    logger.info("Starting serviceability cache refresh...")
    start_time = datetime.now(timezone.utc)

    try:
        # Import here to avoid circular imports
        from app.database import get_db_session
        from sqlalchemy import text

        async with get_db_session() as session:
            # Fetch all serviceable areas from warehouse_serviceability table
            result = await session.execute(
                text("""
                    SELECT
                        pincode,
                        city,
                        state,
                        is_serviceable,
                        estimated_days,
                        cod_available,
                        shipping_cost
                    FROM warehouse_serviceability
                    WHERE is_active = true
                """)
            )
            rows = result.fetchall()

            # Build cache data
            cache_data = {}
            for row in rows:
                cache_data[row.pincode] = {
                    "pincode": row.pincode,
                    "city": row.city,
                    "state": row.state,
                    "is_serviceable": row.is_serviceable,
                    "delivery_days": row.estimated_days,
                    "cod_available": row.cod_available,
                    "shipping_cost": row.shipping_cost,
                    "cached_at": datetime.now().isoformat()
                }

            # Try to update Redis cache
            redis_client = await get_redis_client()
            if redis_client:
                try:
                    # Use pipeline for batch operations
                    pipe = redis_client.pipeline()
                    for pincode, data in cache_data.items():
                        import json
                        pipe.setex(
                            f"serviceability:{pincode}",
                            3600,  # 1 hour TTL
                            json.dumps(data)
                        )
                    await pipe.execute()
                    await redis_client.close()
                    logger.info(f"Updated Redis cache with {len(cache_data)} pincodes")
                except Exception as e:
                    logger.error(f"Redis cache update failed: {e}")

            # Always update in-memory cache as fallback
            _serviceability_cache = cache_data
            _cache_last_updated = datetime.now(timezone.utc)

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Serviceability cache refresh completed: "
                f"{len(cache_data)} pincodes in {elapsed:.2f}s"
            )

    except Exception as e:
        logger.error(f"Serviceability cache refresh failed: {e}")
        raise


async def warm_popular_pincodes():
    """
    Pre-warm cache for popular/high-traffic pincodes.

    This job runs every 30 minutes to ensure popular areas
    always have fresh data available instantly.
    """
    logger.info("Starting popular pincodes cache warming...")
    start_time = datetime.now(timezone.utc)
    warmed_count = 0

    try:
        from app.database import get_db_session
        from sqlalchemy import text

        async with get_db_session() as session:
            # Fetch data for popular pincodes
            placeholders = ", ".join([f":pin{i}" for i in range(len(POPULAR_PINCODES))])
            params = {f"pin{i}": pin for i, pin in enumerate(POPULAR_PINCODES)}

            result = await session.execute(
                text(f"""
                    SELECT
                        pincode,
                        city,
                        state,
                        is_serviceable,
                        estimated_days,
                        cod_available,
                        shipping_cost
                    FROM warehouse_serviceability
                    WHERE pincode IN ({placeholders})
                    AND is_active = true
                """),
                params
            )
            rows = result.fetchall()

            # Update cache with high priority
            redis_client = await get_redis_client()
            for row in rows:
                cache_data = {
                    "pincode": row.pincode,
                    "city": row.city,
                    "state": row.state,
                    "is_serviceable": row.is_serviceable,
                    "delivery_days": row.estimated_days,
                    "cod_available": row.cod_available,
                    "shipping_cost": row.shipping_cost,
                    "cached_at": datetime.now().isoformat(),
                    "priority": "high"
                }

                if redis_client:
                    try:
                        import json
                        await redis_client.setex(
                            f"serviceability:{row.pincode}",
                            7200,  # 2 hour TTL for popular pincodes
                            json.dumps(cache_data)
                        )
                    except Exception:
                        pass

                # Always update in-memory
                _serviceability_cache[row.pincode] = cache_data
                warmed_count += 1

            if redis_client:
                await redis_client.close()

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Popular pincodes cache warming completed: "
                f"{warmed_count} pincodes in {elapsed:.2f}s"
            )

    except Exception as e:
        logger.error(f"Popular pincodes cache warming failed: {e}")
        raise


async def sync_inventory_cache():
    """
    Sync inventory levels from database to cache.

    This job runs every 5 minutes to keep inventory data fresh
    for quick stock availability checks.
    """
    global _inventory_cache

    logger.info("Starting inventory cache sync...")
    start_time = datetime.now(timezone.utc)

    try:
        from app.database import get_db_session
        from sqlalchemy import text

        async with get_db_session() as session:
            # Fetch current inventory levels
            result = await session.execute(
                text("""
                    SELECT
                        product_id,
                        sku,
                        quantity_available,
                        reserved_quantity,
                        warehouse_id
                    FROM inventory
                    WHERE is_active = true
                """)
            )
            rows = result.fetchall()

            # Build inventory cache
            inventory_data = {}
            for row in rows:
                key = f"{row.product_id}:{row.warehouse_id}"
                inventory_data[key] = {
                    "product_id": row.product_id,
                    "sku": row.sku,
                    "available": row.quantity_available - row.reserved_quantity,
                    "warehouse_id": row.warehouse_id,
                    "synced_at": datetime.now().isoformat()
                }

            # Update Redis cache
            redis_client = await get_redis_client()
            if redis_client:
                try:
                    import json
                    pipe = redis_client.pipeline()
                    for key, data in inventory_data.items():
                        pipe.setex(
                            f"inventory:{key}",
                            600,  # 10 minute TTL
                            json.dumps(data)
                        )
                    await pipe.execute()
                    await redis_client.close()
                except Exception as e:
                    logger.error(f"Redis inventory update failed: {e}")

            # Update in-memory cache
            _inventory_cache = {k: v["available"] for k, v in inventory_data.items()}

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Inventory cache sync completed: "
                f"{len(inventory_data)} items in {elapsed:.2f}s"
            )

    except Exception as e:
        logger.error(f"Inventory cache sync failed: {e}")
        raise


async def check_serviceability(pincode: str) -> Dict[str, Any]:
    """
    Quick serviceability check from cache (Phase 1).

    Target response time: <100ms

    Args:
        pincode: The pincode to check

    Returns:
        Serviceability data from cache
    """
    # Try Redis first
    redis_client = await get_redis_client()
    if redis_client:
        try:
            import json
            data = await redis_client.get(f"serviceability:{pincode}")
            await redis_client.close()
            if data:
                return json.loads(data)
        except Exception:
            pass

    # Fallback to in-memory cache
    if pincode in _serviceability_cache:
        return _serviceability_cache[pincode]

    # Not in cache - return not serviceable
    return {
        "pincode": pincode,
        "is_serviceable": False,
        "message": "Pincode not found in cache",
        "cached_at": None
    }


async def get_inventory_from_cache(product_id: str, warehouse_id: str = "default") -> int:
    """
    Get inventory level from cache.

    Args:
        product_id: The product ID
        warehouse_id: The warehouse ID (default: "default")

    Returns:
        Available quantity from cache
    """
    key = f"{product_id}:{warehouse_id}"

    # Try Redis first
    redis_client = await get_redis_client()
    if redis_client:
        try:
            import json
            data = await redis_client.get(f"inventory:{key}")
            await redis_client.close()
            if data:
                return json.loads(data).get("available", 0)
        except Exception:
            pass

    # Fallback to in-memory cache
    return _inventory_cache.get(key, 0)
