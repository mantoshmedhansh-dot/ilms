"""
Channel Inventory Service.

Central service for channel-specific inventory management.
Handles:
1. Channel availability queries
2. Soft reservations against channel inventory
3. Allocation from main pool to channels
4. Auto-replenishment logic
5. Marketplace sync triggers
"""
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import SalesChannel, ChannelInventory, ChannelType
from app.models.inventory import InventorySummary, StockItem
from app.models.warehouse import Warehouse
from app.services.cache_service import get_cache
from app.config import settings


class FallbackStrategy(str, Enum):
    """Fallback strategy when channel inventory is exhausted."""
    NO_FALLBACK = "NO_FALLBACK"  # Return out of stock
    SHARED_POOL = "SHARED_POOL"  # Use unallocated FG inventory
    AUTO_REPLENISH = "AUTO_REPLENISH"  # Auto-allocate more from main pool


class ChannelInventoryService:
    """
    Central service for channel-specific inventory management.

    This service integrates ChannelInventory with the existing inventory flow:
    - D2C Storefront shows channel-specific availability
    - Reservations are made against channel allocations
    - Orders consume channel inventory
    - Auto-replenishment keeps channels stocked
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = get_cache()

    # ==================== Channel Availability ====================

    async def get_channel_availability(
        self,
        channel_code: str,
        product_id: uuid.UUID,
        warehouse_id: Optional[uuid.UUID] = None,
        include_soft_reserved: bool = True
    ) -> Dict[str, Any]:
        """
        Get available quantity for a specific channel.

        Args:
            channel_code: Channel code (e.g., 'D2C', 'AMAZON', 'FLIPKART')
            product_id: Product to check
            warehouse_id: Specific warehouse (optional, aggregates all if None)
            include_soft_reserved: Whether to subtract soft reservations from cache

        Returns:
            Dict with availability details
        """
        # Get channel by code
        channel = await self._get_channel_by_code(channel_code)
        if not channel:
            return {
                "product_id": str(product_id),
                "channel_code": channel_code,
                "is_available": False,
                "available_quantity": 0,
                "error": f"Channel {channel_code} not found"
            }

        # Query channel inventory
        query = (
            select(
                func.sum(ChannelInventory.allocated_quantity).label('total_allocated'),
                func.sum(ChannelInventory.buffer_quantity).label('total_buffer'),
                func.sum(ChannelInventory.reserved_quantity).label('total_reserved'),
            )
            .where(
                and_(
                    ChannelInventory.channel_id == channel.id,
                    ChannelInventory.product_id == product_id,
                    ChannelInventory.is_active == True,
                )
            )
        )

        if warehouse_id:
            query = query.where(ChannelInventory.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        row = result.first()

        total_allocated = row.total_allocated or 0 if row else 0
        total_buffer = row.total_buffer or 0 if row else 0
        total_reserved = row.total_reserved or 0 if row else 0

        # Get soft reservations from cache
        soft_reserved = 0
        if include_soft_reserved:
            soft_reserved = await self._get_channel_soft_reserved(channel.id, product_id)

        # Calculate available: allocated - buffer - reserved - soft_reserved
        available = max(0, total_allocated - total_buffer - total_reserved - soft_reserved)

        return {
            "product_id": str(product_id),
            "channel_code": channel_code,
            "channel_id": str(channel.id),
            "is_available": available > 0,
            "available_quantity": available,
            "allocated_quantity": total_allocated,
            "buffer_quantity": total_buffer,
            "reserved_quantity": total_reserved,
            "soft_reserved": soft_reserved,
            "warehouse_id": str(warehouse_id) if warehouse_id else None,
        }

    async def get_channel_availability_bulk(
        self,
        channel_code: str,
        product_ids: List[uuid.UUID],
        warehouse_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get availability for multiple products on a channel.

        Args:
            channel_code: Channel code
            product_ids: List of product IDs
            warehouse_id: Specific warehouse (optional)

        Returns:
            Dict mapping product_id -> availability info
        """
        result = {}

        channel = await self._get_channel_by_code(channel_code)
        if not channel:
            for pid in product_ids:
                result[str(pid)] = {
                    "product_id": str(pid),
                    "channel_code": channel_code,
                    "is_available": False,
                    "available_quantity": 0,
                    "error": f"Channel {channel_code} not found"
                }
            return result

        # Query all channel inventory in one query
        query = (
            select(
                ChannelInventory.product_id,
                func.sum(ChannelInventory.allocated_quantity).label('total_allocated'),
                func.sum(ChannelInventory.buffer_quantity).label('total_buffer'),
                func.sum(ChannelInventory.reserved_quantity).label('total_reserved'),
            )
            .where(
                and_(
                    ChannelInventory.channel_id == channel.id,
                    ChannelInventory.product_id.in_(product_ids),
                    ChannelInventory.is_active == True,
                )
            )
            .group_by(ChannelInventory.product_id)
        )

        if warehouse_id:
            query = query.where(ChannelInventory.warehouse_id == warehouse_id)

        db_result = await self.db.execute(query)
        rows = db_result.all()

        # Build map from query results
        inventory_map = {}
        for row in rows:
            inventory_map[row.product_id] = {
                "allocated": row.total_allocated or 0,
                "buffer": row.total_buffer or 0,
                "reserved": row.total_reserved or 0,
            }

        # Get soft reservations for all products
        for pid in product_ids:
            inv = inventory_map.get(pid, {"allocated": 0, "buffer": 0, "reserved": 0})
            soft_reserved = await self._get_channel_soft_reserved(channel.id, pid)

            available = max(0, inv["allocated"] - inv["buffer"] - inv["reserved"] - soft_reserved)

            result[str(pid)] = {
                "product_id": str(pid),
                "channel_code": channel_code,
                "channel_id": str(channel.id),
                "is_available": available > 0,
                "available_quantity": available,
                "allocated_quantity": inv["allocated"],
                "buffer_quantity": inv["buffer"],
                "reserved_quantity": inv["reserved"],
                "soft_reserved": soft_reserved,
            }

        return result

    # ==================== Channel Reservations ====================

    async def reserve_for_channel(
        self,
        channel_code: str,
        items: List[Dict[str, Any]],
        reservation_id: str,
        ttl_seconds: int = 600
    ) -> Dict[str, Any]:
        """
        Create soft reservation against channel inventory.

        Args:
            channel_code: Channel code (e.g., 'D2C')
            items: List of {"product_id": uuid, "quantity": int}
            reservation_id: Unique reservation ID
            ttl_seconds: Time-to-live for reservation (default 10 minutes)

        Returns:
            Reservation result with success status
        """
        channel = await self._get_channel_by_code(channel_code)
        if not channel:
            return {
                "success": False,
                "error": f"Channel {channel_code} not found",
                "reserved_items": [],
                "failed_items": items,
            }

        reserved_items = []
        failed_items = []

        # Check availability for each item
        for item in items:
            product_id = uuid.UUID(str(item["product_id"]))
            quantity = item["quantity"]

            availability = await self.get_channel_availability(
                channel_code=channel_code,
                product_id=product_id,
                include_soft_reserved=True
            )

            if availability["available_quantity"] >= quantity:
                reserved_items.append({
                    "product_id": str(product_id),
                    "quantity": quantity,
                    "channel_id": str(channel.id),
                })
            else:
                failed_items.append({
                    "product_id": str(product_id),
                    "requested": quantity,
                    "available": availability["available_quantity"],
                    "reason": "Insufficient channel inventory",
                })

        if failed_items:
            return {
                "success": False,
                "reservation_id": None,
                "error": f"{len(failed_items)} item(s) have insufficient channel inventory",
                "reserved_items": [],
                "failed_items": failed_items,
            }

        # Create soft reservations in cache
        reservation_data = {
            "reservation_id": reservation_id,
            "channel_id": str(channel.id),
            "channel_code": channel_code,
            "items": reserved_items,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "ACTIVE",
        }

        # Store reservation
        await self.cache.set(
            f"channel:reservation:{reservation_id}",
            reservation_data,
            ttl=ttl_seconds
        )

        # Increment soft reserved for each product
        for item in reserved_items:
            await self._increment_channel_soft_reserved(
                channel.id,
                uuid.UUID(item["product_id"]),
                item["quantity"],
                ttl_seconds + 60  # Slightly longer TTL for cleanup
            )

        return {
            "success": True,
            "reservation_id": reservation_id,
            "channel_code": channel_code,
            "reserved_items": reserved_items,
            "failed_items": [],
        }

    async def confirm_reservation(
        self,
        reservation_id: str,
        order_id: uuid.UUID
    ) -> bool:
        """
        Confirm a reservation after successful payment.
        Converts soft reservation to hard allocation.

        Args:
            reservation_id: The reservation to confirm
            order_id: The order ID to allocate to

        Returns:
            True if successful
        """
        # Get reservation from cache
        reservation = await self.cache.get(f"channel:reservation:{reservation_id}")
        if not reservation:
            return False

        if reservation.get("status") != "ACTIVE":
            return False

        channel_id = uuid.UUID(reservation["channel_id"])

        # Update reservation status
        reservation["status"] = "CONFIRMED"
        reservation["order_id"] = str(order_id)
        reservation["confirmed_at"] = datetime.now(timezone.utc).isoformat()

        await self.cache.set(
            f"channel:reservation:{reservation_id}",
            reservation,
            ttl=300  # Keep for 5 minutes for audit
        )

        # Decrement soft reserved and increment hard reserved in ChannelInventory
        for item in reservation.get("items", []):
            product_id = uuid.UUID(item["product_id"])
            quantity = item["quantity"]

            # Decrement soft reserved in cache
            await self._decrement_channel_soft_reserved(channel_id, product_id, quantity)

            # Increment reserved_quantity in ChannelInventory
            await self._increment_channel_reserved(channel_id, product_id, quantity)

        return True

    async def release_reservation(self, reservation_id: str) -> bool:
        """
        Release a reservation (payment failed/cancelled).

        Args:
            reservation_id: The reservation to release

        Returns:
            True if successful
        """
        reservation = await self.cache.get(f"channel:reservation:{reservation_id}")
        if not reservation:
            return False

        if reservation.get("status") != "ACTIVE":
            return False

        channel_id = uuid.UUID(reservation["channel_id"])

        # Decrement soft reserved for each item
        for item in reservation.get("items", []):
            product_id = uuid.UUID(item["product_id"])
            quantity = item["quantity"]
            await self._decrement_channel_soft_reserved(channel_id, product_id, quantity)

        # Delete reservation
        await self.cache.delete(f"channel:reservation:{reservation_id}")

        return True

    # ==================== Channel Allocation ====================

    async def allocate_to_channel(
        self,
        channel_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        buffer_quantity: int = 0,
        safety_stock: Optional[int] = None,
        reorder_point: Optional[int] = None,
        variant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Admin: Allocate inventory from main pool to channel.

        Args:
            channel_id: Target channel
            warehouse_id: Source warehouse
            product_id: Product to allocate
            quantity: Quantity to allocate
            buffer_quantity: Safety buffer (not sellable)
            safety_stock: Target level for auto-replenish
            reorder_point: Trigger level for auto-replenish
            variant_id: Product variant (optional)

        Returns:
            Allocation result
        """
        # Verify main pool has enough inventory
        main_pool = await self._get_main_pool_available(warehouse_id, product_id)

        if main_pool["unallocated_quantity"] < quantity:
            return {
                "success": False,
                "error": f"Insufficient unallocated inventory. Available: {main_pool['unallocated_quantity']}, Requested: {quantity}",
                "available_in_main_pool": main_pool["unallocated_quantity"],
            }

        # Check if channel inventory record exists
        existing = await self.db.execute(
            select(ChannelInventory).where(
                and_(
                    ChannelInventory.channel_id == channel_id,
                    ChannelInventory.warehouse_id == warehouse_id,
                    ChannelInventory.product_id == product_id,
                    ChannelInventory.variant_id == variant_id,
                )
            )
        )
        channel_inv = existing.scalar_one_or_none()

        if channel_inv:
            # Update existing allocation
            channel_inv.allocated_quantity += quantity
            if buffer_quantity > 0:
                channel_inv.buffer_quantity = buffer_quantity
        else:
            # Create new allocation
            channel_inv = ChannelInventory(
                channel_id=channel_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                variant_id=variant_id,
                allocated_quantity=quantity,
                buffer_quantity=buffer_quantity,
                reserved_quantity=0,
                marketplace_quantity=0,
                is_active=True,
            )
            self.db.add(channel_inv)

        await self.db.commit()
        await self.db.refresh(channel_inv)

        return {
            "success": True,
            "channel_inventory_id": str(channel_inv.id),
            "channel_id": str(channel_id),
            "warehouse_id": str(warehouse_id),
            "product_id": str(product_id),
            "allocated_quantity": channel_inv.allocated_quantity,
            "buffer_quantity": channel_inv.buffer_quantity,
            "available_quantity": channel_inv.available_quantity,
        }

    async def deallocate_from_channel(
        self,
        channel_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        variant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Return inventory from channel back to main pool.

        Args:
            channel_id: Source channel
            warehouse_id: Warehouse
            product_id: Product to deallocate
            quantity: Quantity to return
            variant_id: Product variant (optional)

        Returns:
            Deallocation result
        """
        existing = await self.db.execute(
            select(ChannelInventory).where(
                and_(
                    ChannelInventory.channel_id == channel_id,
                    ChannelInventory.warehouse_id == warehouse_id,
                    ChannelInventory.product_id == product_id,
                    ChannelInventory.variant_id == variant_id,
                )
            )
        )
        channel_inv = existing.scalar_one_or_none()

        if not channel_inv:
            return {
                "success": False,
                "error": "Channel inventory record not found",
            }

        # Can only deallocate unreserved inventory
        max_deallocatable = channel_inv.allocated_quantity - channel_inv.reserved_quantity - channel_inv.buffer_quantity

        if quantity > max_deallocatable:
            return {
                "success": False,
                "error": f"Can only deallocate {max_deallocatable} units (rest is reserved or buffer)",
                "max_deallocatable": max_deallocatable,
            }

        channel_inv.allocated_quantity -= quantity
        await self.db.commit()

        return {
            "success": True,
            "channel_id": str(channel_id),
            "product_id": str(product_id),
            "deallocated_quantity": quantity,
            "remaining_allocated": channel_inv.allocated_quantity,
        }

    # ==================== Auto-Replenishment ====================

    async def check_and_replenish(
        self,
        channel_id: uuid.UUID,
        product_id: uuid.UUID,
        safety_stock: int,
        reorder_point: int
    ) -> Dict[str, Any]:
        """
        Check if channel needs replenishment and auto-allocate from main pool.

        Triggered when:
        - available_quantity falls below reorder_point
        - Replenishes up to safety_stock level

        Args:
            channel_id: Channel to check
            product_id: Product to check
            safety_stock: Target level to maintain
            reorder_point: Trigger replenishment when below this

        Returns:
            Replenishment result
        """
        # Get channel's current inventory across all warehouses
        query = (
            select(ChannelInventory)
            .where(
                and_(
                    ChannelInventory.channel_id == channel_id,
                    ChannelInventory.product_id == product_id,
                    ChannelInventory.is_active == True,
                )
            )
        )
        result = await self.db.execute(query)
        channel_invs = result.scalars().all()

        if not channel_invs:
            return {
                "replenished": False,
                "reason": "No channel inventory record found",
            }

        # Calculate total available across all warehouses
        total_available = sum(ci.available_quantity for ci in channel_invs)

        if total_available >= reorder_point:
            return {
                "replenished": False,
                "reason": f"Available ({total_available}) above reorder point ({reorder_point})",
                "current_available": total_available,
            }

        # Calculate needed quantity
        needed = safety_stock - total_available

        # Try to get from unallocated main pool
        replenished_total = 0
        replenish_details = []

        for channel_inv in channel_invs:
            main_pool = await self._get_main_pool_available(
                channel_inv.warehouse_id,
                product_id
            )

            if main_pool["unallocated_quantity"] > 0:
                replenish_qty = min(needed - replenished_total, main_pool["unallocated_quantity"])

                if replenish_qty > 0:
                    channel_inv.allocated_quantity += replenish_qty
                    replenished_total += replenish_qty

                    replenish_details.append({
                        "warehouse_id": str(channel_inv.warehouse_id),
                        "quantity": replenish_qty,
                    })

                if replenished_total >= needed:
                    break

        if replenished_total > 0:
            await self.db.commit()

        return {
            "replenished": replenished_total > 0,
            "quantity_replenished": replenished_total,
            "quantity_needed": needed,
            "new_available": total_available + replenished_total,
            "details": replenish_details,
        }

    # ==================== Order Consumption ====================

    async def consume_for_order(
        self,
        channel_code: str,
        order_id: uuid.UUID,
        items: List[Dict[str, Any]],
        warehouse_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Consume channel inventory when order is confirmed.

        Args:
            channel_code: Channel the order came from
            order_id: Order ID
            items: List of {"product_id": uuid, "quantity": int}
            warehouse_id: Fulfillment warehouse

        Returns:
            Consumption result
        """
        channel = await self._get_channel_by_code(channel_code)
        if not channel:
            return {
                "success": False,
                "error": f"Channel {channel_code} not found",
            }

        consumed_items = []

        for item in items:
            product_id = uuid.UUID(str(item["product_id"]))
            quantity = item["quantity"]

            # Find channel inventory for this warehouse
            result = await self.db.execute(
                select(ChannelInventory).where(
                    and_(
                        ChannelInventory.channel_id == channel.id,
                        ChannelInventory.warehouse_id == warehouse_id,
                        ChannelInventory.product_id == product_id,
                    )
                )
            )
            channel_inv = result.scalar_one_or_none()

            if channel_inv:
                # Decrease allocated quantity (order is consuming)
                channel_inv.allocated_quantity = max(0, channel_inv.allocated_quantity - quantity)
                # Also decrease reserved if it was reserved
                channel_inv.reserved_quantity = max(0, channel_inv.reserved_quantity - quantity)

                consumed_items.append({
                    "product_id": str(product_id),
                    "quantity": quantity,
                    "new_allocated": channel_inv.allocated_quantity,
                })

        # Note: Commit is handled by the caller for transaction atomicity
        # This allows the order update and inventory consumption to be atomic

        return {
            "success": True,
            "order_id": str(order_id),
            "channel_code": channel_code,
            "consumed_items": consumed_items,
        }

    # ==================== Helper Methods ====================

    async def _get_channel_by_code(self, channel_code: str) -> Optional[SalesChannel]:
        """Get channel by code."""
        result = await self.db.execute(
            select(SalesChannel).where(
                and_(
                    SalesChannel.code == channel_code,
                    SalesChannel.status == "ACTIVE",
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_d2c_channel(self) -> Optional[SalesChannel]:
        """Get the primary D2C channel."""
        # Try exact D2C code first
        result = await self.db.execute(
            select(SalesChannel).where(
                and_(
                    or_(
                        SalesChannel.code == "D2C",
                        SalesChannel.channel_type == "D2C",
                        SalesChannel.channel_type == "D2C_WEBSITE",
                    ),
                    SalesChannel.status == "ACTIVE",
                )
            ).order_by(SalesChannel.created_at)
        )
        return result.scalars().first()

    async def _get_main_pool_available(
        self,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID
    ) -> Dict[str, int]:
        """
        Get main pool inventory and calculate unallocated quantity.

        Unallocated = InventorySummary.available - sum(ChannelInventory.allocated)
        """
        # Get main pool inventory
        summary_result = await self.db.execute(
            select(InventorySummary).where(
                and_(
                    InventorySummary.warehouse_id == warehouse_id,
                    InventorySummary.product_id == product_id,
                )
            )
        )
        summary = summary_result.scalar_one_or_none()

        if not summary:
            return {
                "total_available": 0,
                "allocated_to_channels": 0,
                "unallocated_quantity": 0,
            }

        total_available = summary.available_quantity or 0

        # Get total allocated to all channels
        allocated_result = await self.db.execute(
            select(func.sum(ChannelInventory.allocated_quantity)).where(
                and_(
                    ChannelInventory.warehouse_id == warehouse_id,
                    ChannelInventory.product_id == product_id,
                    ChannelInventory.is_active == True,
                )
            )
        )
        allocated_to_channels = allocated_result.scalar() or 0

        return {
            "total_available": total_available,
            "allocated_to_channels": allocated_to_channels,
            "unallocated_quantity": max(0, total_available - allocated_to_channels),
        }

    async def _get_channel_soft_reserved(
        self,
        channel_id: uuid.UUID,
        product_id: uuid.UUID
    ) -> int:
        """Get soft-reserved quantity for channel from cache."""
        key = f"channel:soft_reserved:{channel_id}:{product_id}"
        value = await self.cache.get(key)
        return int(value) if value else 0

    async def _increment_channel_soft_reserved(
        self,
        channel_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        ttl: int = 660
    ) -> bool:
        """Increment soft-reserved quantity in cache."""
        key = f"channel:soft_reserved:{channel_id}:{product_id}"
        current = await self._get_channel_soft_reserved(channel_id, product_id)
        return await self.cache.set(key, current + quantity, ttl=ttl)

    async def _decrement_channel_soft_reserved(
        self,
        channel_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int
    ) -> bool:
        """Decrement soft-reserved quantity in cache."""
        key = f"channel:soft_reserved:{channel_id}:{product_id}"
        current = await self._get_channel_soft_reserved(channel_id, product_id)
        new_value = max(0, current - quantity)
        if new_value == 0:
            await self.cache.delete(key)
            return True
        return await self.cache.set(key, new_value, ttl=660)

    async def _increment_channel_reserved(
        self,
        channel_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int
    ) -> bool:
        """Increment hard reserved quantity in ChannelInventory."""
        # Update all matching records proportionally or just the first one
        result = await self.db.execute(
            select(ChannelInventory).where(
                and_(
                    ChannelInventory.channel_id == channel_id,
                    ChannelInventory.product_id == product_id,
                    ChannelInventory.is_active == True,
                )
            ).order_by(ChannelInventory.allocated_quantity.desc())
        )
        channel_inv = result.scalars().first()

        if channel_inv:
            channel_inv.reserved_quantity += quantity
            await self.db.commit()
            return True

        return False


# ==================== Convenience Functions ====================

async def get_channel_availability(
    db: AsyncSession,
    channel_code: str,
    product_id: uuid.UUID,
    warehouse_id: Optional[uuid.UUID] = None
) -> Dict[str, Any]:
    """Helper function to get channel availability."""
    service = ChannelInventoryService(db)
    return await service.get_channel_availability(
        channel_code=channel_code,
        product_id=product_id,
        warehouse_id=warehouse_id
    )


async def reserve_channel_inventory(
    db: AsyncSession,
    channel_code: str,
    items: List[Dict],
    reservation_id: str
) -> Dict[str, Any]:
    """Helper function to create channel reservation."""
    service = ChannelInventoryService(db)
    return await service.reserve_for_channel(
        channel_code=channel_code,
        items=items,
        reservation_id=reservation_id
    )


    # ==================== Dashboard Methods ====================

    async def get_inventory_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive channel inventory dashboard data.

        Returns:
            Dict with by_channel, by_warehouse, by_channel_location breakdowns
        """
        # Get all active channels
        channels_query = select(SalesChannel).where(SalesChannel.status == "ACTIVE")
        channels_result = await self.db.execute(channels_query)
        channels = channels_result.scalars().all()

        # Get all active warehouses
        warehouses_query = select(Warehouse).where(Warehouse.is_active == True)
        warehouses_result = await self.db.execute(warehouses_query)
        warehouses = warehouses_result.scalars().all()

        # Build channel summaries
        by_channel = []
        total_allocated_quantity = 0
        total_available_quantity = 0
        total_products_allocated = set()

        for channel in channels:
            # Get inventory stats for this channel
            stats_query = select(
                func.count(ChannelInventory.id).label("products_count"),
                func.coalesce(func.sum(ChannelInventory.allocated_quantity), 0).label("total_allocated"),
                func.coalesce(func.sum(ChannelInventory.buffer_quantity), 0).label("total_buffer"),
                func.coalesce(func.sum(ChannelInventory.reserved_quantity), 0).label("total_reserved"),
            ).where(
                and_(
                    ChannelInventory.channel_id == channel.id,
                    ChannelInventory.is_active == True,
                )
            )
            stats_result = await self.db.execute(stats_query)
            stats = stats_result.one()

            allocated = int(stats.total_allocated)
            buffer = int(stats.total_buffer)
            reserved = int(stats.total_reserved)
            available = max(0, allocated - buffer - reserved)

            total_allocated_quantity += allocated
            total_available_quantity += available

            # Get unique products
            products_query = select(ChannelInventory.product_id).where(
                and_(
                    ChannelInventory.channel_id == channel.id,
                    ChannelInventory.is_active == True,
                )
            ).distinct()
            products_result = await self.db.execute(products_query)
            for row in products_result.all():
                total_products_allocated.add(row.product_id)

            # Count low stock (available < reorder_point)
            low_stock_query = select(func.count(ChannelInventory.id)).where(
                and_(
                    ChannelInventory.channel_id == channel.id,
                    ChannelInventory.is_active == True,
                    ChannelInventory.reorder_point > 0,
                    (
                        func.coalesce(ChannelInventory.allocated_quantity, 0) -
                        func.coalesce(ChannelInventory.buffer_quantity, 0) -
                        func.coalesce(ChannelInventory.reserved_quantity, 0)
                    ) < ChannelInventory.reorder_point,
                )
            )
            low_stock_result = await self.db.execute(low_stock_query)
            low_stock_count = low_stock_result.scalar() or 0

            # Count out of stock (available == 0)
            oos_query = select(func.count(ChannelInventory.id)).where(
                and_(
                    ChannelInventory.channel_id == channel.id,
                    ChannelInventory.is_active == True,
                    (
                        func.coalesce(ChannelInventory.allocated_quantity, 0) -
                        func.coalesce(ChannelInventory.buffer_quantity, 0) -
                        func.coalesce(ChannelInventory.reserved_quantity, 0)
                    ) <= 0,
                )
            )
            oos_result = await self.db.execute(oos_query)
            oos_count = oos_result.scalar() or 0

            by_channel.append({
                "channel_id": channel.id,
                "channel_code": channel.code,
                "channel_name": channel.name,
                "channel_type": channel.channel_type or "OTHER",
                "total_allocated": allocated,
                "total_buffer": buffer,
                "total_reserved": reserved,
                "total_available": available,
                "products_count": stats.products_count,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": oos_count,
            })

        # Build warehouse summaries
        by_warehouse = []
        for warehouse in warehouses:
            # Get inventory stats for this warehouse from inventory_summary
            inv_query = select(
                func.count(InventorySummary.id).label("products_count"),
                func.coalesce(func.sum(InventorySummary.total_quantity), 0).label("total_quantity"),
                func.coalesce(func.sum(InventorySummary.reserved_quantity), 0).label("total_reserved"),
                func.coalesce(func.sum(InventorySummary.available_quantity), 0).label("total_available"),
            ).where(InventorySummary.warehouse_id == warehouse.id)
            inv_result = await self.db.execute(inv_query)
            inv_stats = inv_result.one()

            # Count low stock in this warehouse
            low_stock_query = select(func.count(InventorySummary.id)).where(
                and_(
                    InventorySummary.warehouse_id == warehouse.id,
                    InventorySummary.is_low_stock == True,
                )
            )
            low_stock_result = await self.db.execute(low_stock_query)
            low_stock_count = low_stock_result.scalar() or 0

            # Count channels served from this warehouse
            channels_query = select(func.count(func.distinct(ChannelInventory.channel_id))).where(
                and_(
                    ChannelInventory.warehouse_id == warehouse.id,
                    ChannelInventory.is_active == True,
                )
            )
            channels_result = await self.db.execute(channels_query)
            channels_served = channels_result.scalar() or 0

            by_warehouse.append({
                "warehouse_id": warehouse.id,
                "warehouse_code": warehouse.code,
                "warehouse_name": warehouse.name,
                "total_quantity": int(inv_stats.total_quantity),
                "total_reserved": int(inv_stats.total_reserved),
                "total_available": int(inv_stats.total_available),
                "products_count": inv_stats.products_count,
                "low_stock_count": low_stock_count,
                "channels_served": channels_served,
            })

        # Build channel-location breakdown
        by_channel_location = []
        breakdown_query = select(
            ChannelInventory.channel_id,
            ChannelInventory.warehouse_id,
            func.count(ChannelInventory.id).label("products_count"),
            func.coalesce(func.sum(ChannelInventory.allocated_quantity), 0).label("allocated"),
            func.coalesce(func.sum(ChannelInventory.buffer_quantity), 0).label("buffer"),
            func.coalesce(func.sum(ChannelInventory.reserved_quantity), 0).label("reserved"),
        ).where(
            ChannelInventory.is_active == True
        ).group_by(
            ChannelInventory.channel_id,
            ChannelInventory.warehouse_id
        )

        breakdown_result = await self.db.execute(breakdown_query)

        # Build lookup maps
        channel_map = {c.id: c for c in channels}
        warehouse_map = {w.id: w for w in warehouses}

        for row in breakdown_result.all():
            channel = channel_map.get(row.channel_id)
            warehouse = warehouse_map.get(row.warehouse_id)

            if channel and warehouse:
                allocated = int(row.allocated)
                buffer = int(row.buffer)
                reserved = int(row.reserved)

                by_channel_location.append({
                    "channel_id": row.channel_id,
                    "channel_code": channel.code,
                    "channel_name": channel.name,
                    "warehouse_id": row.warehouse_id,
                    "warehouse_code": warehouse.code,
                    "warehouse_name": warehouse.name,
                    "allocated_quantity": allocated,
                    "buffer_quantity": buffer,
                    "reserved_quantity": reserved,
                    "available_quantity": max(0, allocated - buffer - reserved),
                    "products_count": row.products_count,
                })

        return {
            "total_channels": len(channels),
            "total_warehouses": len(warehouses),
            "total_products_allocated": len(total_products_allocated),
            "total_allocated_quantity": total_allocated_quantity,
            "total_available_quantity": total_available_quantity,
            "by_channel": by_channel,
            "by_warehouse": by_warehouse,
            "by_channel_location": by_channel_location,
        }


# ==================== Convenience Functions ====================


async def allocate_grn_to_channels(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    total_quantity: int,
    allocations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Allocate GRN received quantity to channels.

    Args:
        db: Database session
        warehouse_id: Receiving warehouse
        product_id: Product received
        total_quantity: Total quantity received
        allocations: List of {"channel_id": uuid, "quantity": int, "buffer": int}

    Returns:
        Allocation results for each channel
    """
    service = ChannelInventoryService(db)
    results = []
    total_allocated = 0

    for alloc in allocations:
        channel_id = uuid.UUID(str(alloc["channel_id"]))
        quantity = alloc["quantity"]
        buffer = alloc.get("buffer", 0)

        result = await service.allocate_to_channel(
            channel_id=channel_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            quantity=quantity,
            buffer_quantity=buffer
        )

        results.append(result)
        if result["success"]:
            total_allocated += quantity

    return {
        "total_received": total_quantity,
        "total_allocated": total_allocated,
        "unallocated": total_quantity - total_allocated,
        "channel_allocations": results,
    }
