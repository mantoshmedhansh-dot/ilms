"""
Auto-Replenish Background Job.

Automatically replenishes channel inventory from shared pool when:
1. Channel inventory falls below reorder point
2. Replenishes up to safety stock level

Triggers:
- Periodic check (every 15 minutes by default)
- After order ships (when channel available decreases)
- When order allocation fails due to low stock
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import ChannelInventory, SalesChannel, ProductChannelSettings
from app.models.inventory import InventorySummary
from app.services.channel_inventory_service import ChannelInventoryService
from app.config import settings

logger = logging.getLogger(__name__)


async def run_auto_replenish_job(db: AsyncSession) -> Dict[str, Any]:
    """
    Main job to check and auto-replenish all channel inventory.

    Returns:
        Summary of replenishment actions taken
    """
    logger.info("Starting auto-replenish job...")

    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "channels_processed": 0,
        "products_checked": 0,
        "replenishments": [],
        "errors": [],
    }

    try:
        service = ChannelInventoryService(db)

        # Get all channel inventory records with auto_replenish enabled
        query = (
            select(ChannelInventory)
            .where(
                and_(
                    ChannelInventory.is_active == True,
                    ChannelInventory.auto_replenish_enabled == True,
                    ChannelInventory.safety_stock > 0,
                    ChannelInventory.reorder_point > 0,
                )
            )
        )

        result = await db.execute(query)
        channel_inventories = result.scalars().all()

        logger.info(f"Found {len(channel_inventories)} channel inventory records with auto-replenish enabled")

        for channel_inv in channel_inventories:
            results["products_checked"] += 1

            try:
                # Calculate current available
                current_available = max(0,
                    (channel_inv.allocated_quantity or 0) -
                    (channel_inv.buffer_quantity or 0) -
                    (channel_inv.reserved_quantity or 0)
                )

                # Check if below reorder point
                if current_available < channel_inv.reorder_point:
                    logger.info(
                        f"Channel {channel_inv.channel_id}, Product {channel_inv.product_id}: "
                        f"Available ({current_available}) below reorder point ({channel_inv.reorder_point})"
                    )

                    # Trigger replenishment
                    replenish_result = await service.check_and_replenish(
                        channel_id=channel_inv.channel_id,
                        product_id=channel_inv.product_id,
                        safety_stock=channel_inv.safety_stock,
                        reorder_point=channel_inv.reorder_point
                    )

                    if replenish_result.get("replenished"):
                        results["replenishments"].append({
                            "channel_id": str(channel_inv.channel_id),
                            "product_id": str(channel_inv.product_id),
                            "warehouse_id": str(channel_inv.warehouse_id),
                            "quantity_replenished": replenish_result.get("quantity_replenished", 0),
                            "new_available": replenish_result.get("new_available", 0),
                            "details": replenish_result.get("details", []),
                        })
                        logger.info(
                            f"Replenished {replenish_result.get('quantity_replenished')} units "
                            f"for channel {channel_inv.channel_id}, product {channel_inv.product_id}"
                        )

            except Exception as e:
                error_msg = f"Error processing channel {channel_inv.channel_id}, product {channel_inv.product_id}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        # Count unique channels processed
        channel_ids = set(ci.channel_id for ci in channel_inventories)
        results["channels_processed"] = len(channel_ids)

    except Exception as e:
        error_msg = f"Auto-replenish job failed: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["total_replenished"] = sum(r.get("quantity_replenished", 0) for r in results["replenishments"])

    logger.info(
        f"Auto-replenish job completed: "
        f"{results['products_checked']} products checked, "
        f"{len(results['replenishments'])} replenishments, "
        f"{results['total_replenished']} total units replenished"
    )

    return results


async def replenish_channel_product(
    db: AsyncSession,
    channel_id: str,
    product_id: str,
    safety_stock: int = None,
    reorder_point: int = None
) -> Dict[str, Any]:
    """
    Manually trigger replenishment for a specific channel-product combination.

    Args:
        db: Database session
        channel_id: Channel UUID as string
        product_id: Product UUID as string
        safety_stock: Override safety stock level (optional)
        reorder_point: Override reorder point (optional)

    Returns:
        Replenishment result
    """
    import uuid

    service = ChannelInventoryService(db)

    # Get current settings if not provided
    if safety_stock is None or reorder_point is None:
        query = select(ChannelInventory).where(
            and_(
                ChannelInventory.channel_id == uuid.UUID(channel_id),
                ChannelInventory.product_id == uuid.UUID(product_id),
                ChannelInventory.is_active == True,
            )
        )
        result = await db.execute(query)
        channel_inv = result.scalars().first()

        if channel_inv:
            safety_stock = safety_stock or channel_inv.safety_stock or 50
            reorder_point = reorder_point or channel_inv.reorder_point or 10
        else:
            safety_stock = safety_stock or 50
            reorder_point = reorder_point or 10

    return await service.check_and_replenish(
        channel_id=uuid.UUID(channel_id),
        product_id=uuid.UUID(product_id),
        safety_stock=safety_stock,
        reorder_point=reorder_point
    )


async def replenish_channel(
    db: AsyncSession,
    channel_id: str
) -> Dict[str, Any]:
    """
    Replenish all low-stock products for a specific channel.

    Args:
        db: Database session
        channel_id: Channel UUID as string

    Returns:
        Summary of replenishment actions
    """
    import uuid

    results = {
        "channel_id": channel_id,
        "products_checked": 0,
        "replenishments": [],
        "errors": [],
    }

    try:
        service = ChannelInventoryService(db)

        # Get all channel inventory for this channel
        query = (
            select(ChannelInventory)
            .where(
                and_(
                    ChannelInventory.channel_id == uuid.UUID(channel_id),
                    ChannelInventory.is_active == True,
                    ChannelInventory.auto_replenish_enabled == True,
                )
            )
        )

        result = await db.execute(query)
        channel_inventories = result.scalars().all()

        for channel_inv in channel_inventories:
            results["products_checked"] += 1

            safety_stock = channel_inv.safety_stock or 50
            reorder_point = channel_inv.reorder_point or 10

            # Calculate current available
            current_available = max(0,
                (channel_inv.allocated_quantity or 0) -
                (channel_inv.buffer_quantity or 0) -
                (channel_inv.reserved_quantity or 0)
            )

            if current_available < reorder_point:
                replenish_result = await service.check_and_replenish(
                    channel_id=channel_inv.channel_id,
                    product_id=channel_inv.product_id,
                    safety_stock=safety_stock,
                    reorder_point=reorder_point
                )

                if replenish_result.get("replenished"):
                    results["replenishments"].append({
                        "product_id": str(channel_inv.product_id),
                        "quantity_replenished": replenish_result.get("quantity_replenished", 0),
                    })

    except Exception as e:
        results["errors"].append(str(e))

    return results


# ==================== Scheduler Integration ====================

def register_auto_replenish_job(scheduler):
    """
    Register the auto-replenish job with the APScheduler.

    Args:
        scheduler: APScheduler instance
    """
    from app.database import get_db_context

    async def job_wrapper():
        async with get_db_context() as db:
            await run_auto_replenish_job(db)

    interval_minutes = getattr(settings, 'AUTO_REPLENISH_INTERVAL_MINUTES', 15)

    scheduler.add_job(
        job_wrapper,
        'interval',
        minutes=interval_minutes,
        id='auto_replenish_channel_inventory',
        name='Auto-replenish channel inventory',
        replace_existing=True,
    )

    logger.info(f"Auto-replenish job registered to run every {interval_minutes} minutes")
