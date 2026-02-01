"""
Marketplace Inventory Sync Job.

Pushes channel inventory quantities to marketplace APIs:
- Amazon SP-API
- Flipkart Seller API
- Other marketplace integrations

Sync intervals are configurable per channel.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from abc import ABC, abstractmethod

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import (
    ChannelInventory, SalesChannel, MarketplaceIntegration,
    ChannelType
)
from app.config import settings

logger = logging.getLogger(__name__)


# ==================== Marketplace API Adapters ====================

class MarketplaceAdapter(ABC):
    """Abstract base class for marketplace API adapters."""

    @abstractmethod
    async def sync_inventory(
        self,
        items: List[Dict[str, Any]],
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync inventory to marketplace.

        Args:
            items: List of {"sku": str, "quantity": int, "fulfillment_channel": str}
            credentials: API credentials

        Returns:
            Sync result with success/failure counts
        """
        pass


class AmazonSPAPIAdapter(MarketplaceAdapter):
    """Amazon Selling Partner API adapter."""

    async def sync_inventory(
        self,
        items: List[Dict[str, Any]],
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync inventory to Amazon SP-API.

        In production, this would:
        1. Authenticate with SP-API using credentials
        2. Call Inventory API to update quantities
        3. Handle rate limiting and retries
        """
        # TODO: Implement actual Amazon SP-API integration
        # For now, simulate successful sync
        logger.info(f"[Amazon] Would sync {len(items)} items to Amazon SP-API")

        return {
            "success": True,
            "synced_count": len(items),
            "failed_count": 0,
            "errors": [],
            "marketplace": "AMAZON",
        }


class FlipkartAPIAdapter(MarketplaceAdapter):
    """Flipkart Seller API adapter."""

    async def sync_inventory(
        self,
        items: List[Dict[str, Any]],
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync inventory to Flipkart Seller API.

        In production, this would:
        1. Authenticate with Flipkart API
        2. Call Listing API to update quantities
        3. Handle batch updates
        """
        # TODO: Implement actual Flipkart API integration
        logger.info(f"[Flipkart] Would sync {len(items)} items to Flipkart API")

        return {
            "success": True,
            "synced_count": len(items),
            "failed_count": 0,
            "errors": [],
            "marketplace": "FLIPKART",
        }


class GenericMarketplaceAdapter(MarketplaceAdapter):
    """Generic marketplace adapter for other integrations."""

    def __init__(self, marketplace_name: str):
        self.marketplace_name = marketplace_name

    async def sync_inventory(
        self,
        items: List[Dict[str, Any]],
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.info(f"[{self.marketplace_name}] Would sync {len(items)} items")

        return {
            "success": True,
            "synced_count": len(items),
            "failed_count": 0,
            "errors": [],
            "marketplace": self.marketplace_name,
        }


def get_marketplace_adapter(channel_type: str) -> MarketplaceAdapter:
    """Get appropriate marketplace adapter based on channel type."""
    adapters = {
        "AMAZON": AmazonSPAPIAdapter(),
        "FLIPKART": FlipkartAPIAdapter(),
        "MYNTRA": GenericMarketplaceAdapter("MYNTRA"),
        "MEESHO": GenericMarketplaceAdapter("MEESHO"),
        "JIOMART": GenericMarketplaceAdapter("JIOMART"),
    }
    return adapters.get(channel_type, GenericMarketplaceAdapter(channel_type))


# ==================== Main Sync Job ====================

async def run_marketplace_sync_job(db: AsyncSession) -> Dict[str, Any]:
    """
    Main job to sync inventory to all marketplace channels.

    Returns:
        Summary of sync operations
    """
    logger.info("Starting marketplace inventory sync job...")

    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "channels_synced": 0,
        "total_items_synced": 0,
        "total_items_failed": 0,
        "channel_results": [],
        "errors": [],
    }

    try:
        # Get all active marketplace channels
        marketplace_types = [
            ChannelType.AMAZON.value,
            ChannelType.FLIPKART.value,
            ChannelType.MYNTRA.value,
            ChannelType.MEESHO.value,
            ChannelType.JIOMART.value,
            ChannelType.MARKETPLACE.value,
        ]

        query = (
            select(SalesChannel)
            .where(
                and_(
                    SalesChannel.channel_type.in_(marketplace_types),
                    SalesChannel.status == "ACTIVE",
                    SalesChannel.sync_enabled == True,
                )
            )
        )

        result = await db.execute(query)
        channels = result.scalars().all()

        logger.info(f"Found {len(channels)} marketplace channels to sync")

        for channel in channels:
            try:
                channel_result = await sync_channel_inventory(db, channel)
                results["channel_results"].append(channel_result)
                results["channels_synced"] += 1
                results["total_items_synced"] += channel_result.get("synced_count", 0)
                results["total_items_failed"] += channel_result.get("failed_count", 0)

            except Exception as e:
                error_msg = f"Error syncing channel {channel.code}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

    except Exception as e:
        error_msg = f"Marketplace sync job failed: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)

    results["completed_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"Marketplace sync job completed: "
        f"{results['channels_synced']} channels, "
        f"{results['total_items_synced']} items synced, "
        f"{results['total_items_failed']} failed"
    )

    return results


async def sync_channel_inventory(
    db: AsyncSession,
    channel: SalesChannel,
    product_ids: Optional[List] = None
) -> Dict[str, Any]:
    """
    Sync inventory for a specific channel.

    Args:
        db: Database session
        channel: SalesChannel to sync
        product_ids: Optional list of product IDs to sync (if None, syncs all)

    Returns:
        Sync result for this channel
    """
    logger.info(f"Syncing inventory for channel: {channel.code} ({channel.channel_type})")

    result = {
        "channel_id": str(channel.id),
        "channel_code": channel.code,
        "channel_type": channel.channel_type,
        "synced_count": 0,
        "failed_count": 0,
        "items": [],
        "errors": [],
    }

    try:
        # Get channel inventory records
        query = (
            select(ChannelInventory)
            .where(
                and_(
                    ChannelInventory.channel_id == channel.id,
                    ChannelInventory.is_active == True,
                )
            )
        )

        if product_ids:
            query = query.where(ChannelInventory.product_id.in_(product_ids))

        inv_result = await db.execute(query)
        inventories = inv_result.scalars().all()

        if not inventories:
            logger.info(f"No inventory records found for channel {channel.code}")
            return result

        # Prepare items for sync
        sync_items = []
        for inv in inventories:
            # Calculate available quantity
            available = max(0,
                (inv.allocated_quantity or 0) -
                (inv.buffer_quantity or 0) -
                (inv.reserved_quantity or 0)
            )

            # Apply sync buffer if configured
            # (reduce reported quantity by buffer % to prevent overselling)
            sync_buffer_pct = 0  # Could be configured per channel
            if sync_buffer_pct > 0:
                available = int(available * (1 - sync_buffer_pct / 100))

            sync_items.append({
                "channel_inventory_id": str(inv.id),
                "product_id": str(inv.product_id),
                "warehouse_id": str(inv.warehouse_id),
                "quantity": available,
                "previous_marketplace_qty": inv.marketplace_quantity,
            })

        # Get marketplace adapter
        adapter = get_marketplace_adapter(channel.channel_type)

        # Get credentials (if configured)
        credentials = {}
        integration_result = await db.execute(
            select(MarketplaceIntegration).where(
                MarketplaceIntegration.channel_id == channel.id
            )
        )
        integration = integration_result.scalar_one_or_none()

        if integration:
            credentials = {
                "client_id": integration.client_id,
                "client_secret": integration.client_secret,  # Note: should be decrypted
                "refresh_token": integration.refresh_token,
                "api_key": integration.api_key,
            }

        # Call marketplace API
        sync_result = await adapter.sync_inventory(sync_items, credentials)

        result["synced_count"] = sync_result.get("synced_count", 0)
        result["failed_count"] = sync_result.get("failed_count", 0)
        result["errors"] = sync_result.get("errors", [])

        # Update marketplace_quantity and last_synced_at for synced items
        if sync_result.get("success"):
            for item in sync_items:
                # Find the inventory record and update it
                for inv in inventories:
                    if str(inv.id) == item["channel_inventory_id"]:
                        inv.marketplace_quantity = item["quantity"]
                        inv.last_synced_at = datetime.now(timezone.utc)
                        break

            await db.commit()

            result["items"] = [
                {
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "previous_qty": item["previous_marketplace_qty"],
                }
                for item in sync_items
            ]

        logger.info(f"Channel {channel.code}: synced {result['synced_count']} items")

    except Exception as e:
        error_msg = f"Error syncing channel {channel.code}: {e}"
        logger.error(error_msg)
        result["errors"].append(error_msg)

    return result


async def sync_single_channel(
    db: AsyncSession,
    channel_id: str,
    product_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Manually trigger sync for a specific channel.

    Args:
        db: Database session
        channel_id: Channel UUID as string
        product_ids: Optional list of product IDs to sync

    Returns:
        Sync result
    """
    import uuid

    # Get channel
    channel_result = await db.execute(
        select(SalesChannel).where(SalesChannel.id == uuid.UUID(channel_id))
    )
    channel = channel_result.scalar_one_or_none()

    if not channel:
        return {
            "success": False,
            "error": f"Channel {channel_id} not found",
        }

    # Convert product_ids to UUIDs
    product_uuids = None
    if product_ids:
        product_uuids = [uuid.UUID(pid) for pid in product_ids]

    return await sync_channel_inventory(db, channel, product_uuids)


# ==================== Scheduler Integration ====================

def register_marketplace_sync_job(scheduler):
    """
    Register the marketplace sync job with the APScheduler.

    Args:
        scheduler: APScheduler instance
    """
    from app.database import get_db_context

    async def job_wrapper():
        async with get_db_context() as db:
            await run_marketplace_sync_job(db)

    interval_minutes = getattr(settings, 'MARKETPLACE_SYNC_INTERVAL_MINUTES', 30)

    scheduler.add_job(
        job_wrapper,
        'interval',
        minutes=interval_minutes,
        id='marketplace_inventory_sync',
        name='Sync inventory to marketplaces',
        replace_existing=True,
    )

    logger.info(f"Marketplace sync job registered to run every {interval_minutes} minutes")
