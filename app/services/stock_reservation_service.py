"""
Stock Reservation Service for D2C Storefront.

Prevents overselling by temporarily reserving stock when:
1. Customer proceeds to checkout
2. Customer initiates payment

Reservations auto-expire after TTL to prevent stuck inventory.
"""
import uuid
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventorySummary, StockItem
from app.models.channel import ChannelInventory, SalesChannel
from app.services.cache_service import get_cache
from app.config import settings


# Reservation TTL in seconds (10 minutes default)
RESERVATION_TTL = 600


@dataclass
class ReservationItem:
    """Single item in a reservation."""
    product_id: str
    quantity: int
    warehouse_id: Optional[str] = None


@dataclass
class ReservationResult:
    """Result of a reservation attempt."""
    success: bool
    reservation_id: Optional[str] = None
    message: str = ""
    reserved_items: List[Dict] = None
    failed_items: List[Dict] = None

    def __post_init__(self):
        if self.reserved_items is None:
            self.reserved_items = []
        if self.failed_items is None:
            self.failed_items = []


class StockReservationService:
    """
    Manages temporary stock reservations for checkout process.

    Flow:
    1. create_reservation() - Called when customer clicks "Proceed to Checkout"
    2. confirm_reservation() - Called when payment succeeds
    3. release_reservation() - Called when payment fails/times out

    Uses Redis for fast reservation tracking with auto-expiry.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = get_cache()

    def _reservation_key(self, reservation_id: str) -> str:
        """Generate cache key for reservation."""
        return f"stock:reservation:{reservation_id}"

    def _product_reserved_key(self, product_id: str) -> str:
        """Generate cache key for product's total reserved quantity."""
        return f"stock:reserved:{product_id}"

    async def _get_channel_by_code(self, channel_code: str) -> Optional[SalesChannel]:
        """Get sales channel by code."""
        result = await self.db.execute(
            select(SalesChannel).where(
                and_(
                    or_(
                        SalesChannel.code == channel_code,
                        SalesChannel.channel_type == channel_code,
                    ),
                    SalesChannel.status == "ACTIVE",
                )
            ).order_by(SalesChannel.created_at)
        )
        return result.scalars().first()

    def _channel_reserved_key(self, channel_id: str, product_id: str) -> str:
        """Generate cache key for channel-specific reserved quantity."""
        return f"channel:soft_reserved:{channel_id}:{product_id}"

    async def _get_channel_soft_reserved(self, channel_id: str, product_id: str) -> int:
        """Get channel-specific soft-reserved quantity from cache."""
        key = self._channel_reserved_key(channel_id, product_id)
        value = await self.cache.get(key)
        return int(value) if value else 0

    async def check_availability(
        self,
        items: List[ReservationItem],
        channel: str = "D2C"
    ) -> Dict[str, Dict]:
        """
        Check stock availability for multiple items.
        Returns dict with product_id -> availability info.

        Now channel-aware: checks ChannelInventory for the specified channel first.
        Falls back to InventorySummary (shared pool) if channel inventory not configured.
        """
        result = {}

        # Try to get the channel for channel-specific inventory
        channel_obj = await self._get_channel_by_code(channel)
        use_channel_inventory = channel_obj and getattr(settings, 'CHANNEL_INVENTORY_ENABLED', True)

        for item in items:
            if use_channel_inventory:
                # Query channel-specific inventory
                # Available = allocated - buffer - reserved
                query = (
                    select(
                        func.sum(
                            func.greatest(
                                0,
                                func.coalesce(ChannelInventory.allocated_quantity, 0) -
                                func.coalesce(ChannelInventory.buffer_quantity, 0) -
                                func.coalesce(ChannelInventory.reserved_quantity, 0)
                            )
                        ).label('total_available'),
                        func.sum(func.coalesce(ChannelInventory.reserved_quantity, 0)).label('total_reserved'),
                        func.sum(func.coalesce(ChannelInventory.allocated_quantity, 0)).label('total_allocated'),
                    )
                    .where(
                        and_(
                            ChannelInventory.channel_id == channel_obj.id,
                            ChannelInventory.product_id == item.product_id,
                            ChannelInventory.is_active == True,
                        )
                    )
                )

                db_result = await self.db.execute(query)
                row = db_result.first()

                total_available = row.total_available or 0 if row else 0
                total_reserved = row.total_reserved or 0 if row else 0
                total_allocated = row.total_allocated or 0 if row else 0

                # Get channel-specific soft reservations from cache
                soft_reserved = await self._get_channel_soft_reserved(str(channel_obj.id), item.product_id)

                # Actual available = channel available - channel soft reserved
                actual_available = total_available - soft_reserved

                result[item.product_id] = {
                    "product_id": item.product_id,
                    "requested": item.quantity,
                    "available": max(0, actual_available),
                    "is_available": actual_available >= item.quantity,
                    "channel_allocated": total_allocated,
                    "channel_reserved": total_reserved,
                    "soft_reserved": soft_reserved,
                    "channel_code": channel,
                    "channel_id": str(channel_obj.id),
                }
            else:
                # Fallback to legacy shared pool (InventorySummary)
                query = (
                    select(
                        func.sum(InventorySummary.available_quantity).label('total_available'),
                        func.sum(InventorySummary.reserved_quantity).label('total_reserved'),
                    )
                    .where(InventorySummary.product_id == item.product_id)
                )

                db_result = await self.db.execute(query)
                row = db_result.first()

                total_available = row.total_available or 0 if row else 0
                total_reserved = row.total_reserved or 0 if row else 0

                # Get soft reservations from cache (legacy)
                soft_reserved = await self._get_soft_reserved(item.product_id)

                # Actual available = DB available - DB reserved - soft reserved
                actual_available = total_available - total_reserved - soft_reserved

                result[item.product_id] = {
                    "product_id": item.product_id,
                    "requested": item.quantity,
                    "available": max(0, actual_available),
                    "is_available": actual_available >= item.quantity,
                    "db_available": total_available,
                    "db_reserved": total_reserved,
                    "soft_reserved": soft_reserved,
                    "channel_code": "SHARED",
                }

        return result

    async def _get_soft_reserved(self, product_id: str) -> int:
        """Get total soft-reserved quantity from cache."""
        key = self._product_reserved_key(product_id)
        value = await self.cache.get(key)
        return int(value) if value else 0

    async def _increment_soft_reserved(self, product_id: str, quantity: int) -> bool:
        """Increment soft-reserved quantity in cache."""
        key = self._product_reserved_key(product_id)
        current = await self._get_soft_reserved(product_id)
        new_value = current + quantity
        # Set with longer TTL than individual reservations to handle cleanup
        return await self.cache.set(key, new_value, ttl=RESERVATION_TTL + 60)

    async def _decrement_soft_reserved(self, product_id: str, quantity: int) -> bool:
        """Decrement soft-reserved quantity in cache."""
        key = self._product_reserved_key(product_id)
        current = await self._get_soft_reserved(product_id)
        new_value = max(0, current - quantity)
        if new_value == 0:
            await self.cache.delete(key)
            return True
        return await self.cache.set(key, new_value, ttl=RESERVATION_TTL + 60)

    async def create_reservation(
        self,
        items: List[ReservationItem],
        customer_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ttl: int = RESERVATION_TTL,
        channel: str = "D2C",
    ) -> ReservationResult:
        """
        Create a stock reservation for checkout.

        Args:
            items: List of products and quantities to reserve
            customer_id: Customer ID (for logged-in users)
            session_id: Session ID (for guests)
            ttl: Time-to-live in seconds (default 10 minutes)
            channel: Sales channel code (default D2C)

        Returns:
            ReservationResult with reservation_id if successful
        """
        # Get channel for channel-specific reservations
        channel_obj = await self._get_channel_by_code(channel)
        use_channel_inventory = channel_obj and getattr(settings, 'CHANNEL_INVENTORY_ENABLED', True)

        # Check availability first
        availability = await self.check_availability(items, channel=channel)

        reserved_items = []
        failed_items = []

        for item in items:
            avail = availability.get(item.product_id, {})
            if avail.get("is_available", False):
                reserved_items.append({
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "warehouse_id": item.warehouse_id,
                    "channel_id": str(channel_obj.id) if channel_obj else None,
                })
            else:
                failed_items.append({
                    "product_id": item.product_id,
                    "requested": item.quantity,
                    "available": avail.get("available", 0),
                    "reason": "Insufficient stock",
                })

        if failed_items:
            return ReservationResult(
                success=False,
                message=f"{len(failed_items)} item(s) have insufficient stock",
                reserved_items=[],
                failed_items=failed_items,
            )

        # Create reservation
        reservation_id = str(uuid.uuid4())
        reservation_data = {
            "reservation_id": reservation_id,
            "customer_id": customer_id,
            "session_id": session_id,
            "channel_code": channel,
            "channel_id": str(channel_obj.id) if channel_obj else None,
            "items": reserved_items,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat(),
            "status": "ACTIVE",
        }

        # Store reservation in cache
        await self.cache.set(
            self._reservation_key(reservation_id),
            reservation_data,
            ttl=ttl
        )

        # Increment soft-reserved quantities
        for item in reserved_items:
            if use_channel_inventory and channel_obj:
                # Channel-specific soft reservation
                key = self._channel_reserved_key(str(channel_obj.id), item["product_id"])
                current = await self._get_channel_soft_reserved(str(channel_obj.id), item["product_id"])
                await self.cache.set(key, current + item["quantity"], ttl=ttl + 60)
            else:
                # Legacy shared pool reservation
                await self._increment_soft_reserved(item["product_id"], item["quantity"])

        return ReservationResult(
            success=True,
            reservation_id=reservation_id,
            message="Stock reserved successfully",
            reserved_items=reserved_items,
            failed_items=[],
        )

    async def get_reservation(self, reservation_id: str) -> Optional[Dict]:
        """Get reservation details by ID."""
        return await self.cache.get(self._reservation_key(reservation_id))

    async def confirm_reservation(
        self,
        reservation_id: str,
        order_id: str,
    ) -> bool:
        """
        Confirm a reservation after successful payment.
        Converts soft reservation to hard allocation.

        Args:
            reservation_id: The reservation to confirm
            order_id: The order ID to allocate stock to

        Returns:
            True if successful
        """
        reservation = await self.get_reservation(reservation_id)
        if not reservation:
            return False

        if reservation.get("status") != "ACTIVE":
            return False

        # Update reservation status
        reservation["status"] = "CONFIRMED"
        reservation["order_id"] = order_id
        reservation["confirmed_at"] = datetime.now(timezone.utc).isoformat()

        # Store updated reservation (short TTL since it's confirmed)
        await self.cache.set(
            self._reservation_key(reservation_id),
            reservation,
            ttl=300  # Keep for 5 minutes for audit
        )

        # Decrement soft-reserved (will be handled by actual allocation)
        channel_id = reservation.get("channel_id")

        for item in reservation.get("items", []):
            if channel_id:
                # Decrement channel-specific soft reservation
                key = self._channel_reserved_key(channel_id, item["product_id"])
                current = await self._get_channel_soft_reserved(channel_id, item["product_id"])
                new_value = max(0, current - item["quantity"])
                if new_value == 0:
                    await self.cache.delete(key)
                else:
                    await self.cache.set(key, new_value, ttl=RESERVATION_TTL + 60)

                # Increment hard reserved in ChannelInventory
                await self._increment_channel_hard_reserved(channel_id, item["product_id"], item["quantity"])
            else:
                # Legacy: decrement shared pool soft reservation
                await self._decrement_soft_reserved(item["product_id"], item["quantity"])

        return True

    async def _increment_channel_hard_reserved(
        self,
        channel_id: str,
        product_id: str,
        quantity: int
    ) -> bool:
        """Increment hard reserved quantity in ChannelInventory table."""
        try:
            # Find the channel inventory record
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
                channel_inv.reserved_quantity = (channel_inv.reserved_quantity or 0) + quantity
                await self.db.commit()
                return True
        except Exception:
            pass
        return False

    async def release_reservation(self, reservation_id: str) -> bool:
        """
        Release a reservation (payment failed/cancelled).

        Args:
            reservation_id: The reservation to release

        Returns:
            True if successful
        """
        reservation = await self.get_reservation(reservation_id)
        if not reservation:
            return False

        if reservation.get("status") != "ACTIVE":
            return False

        # Decrement soft-reserved quantities
        channel_id = reservation.get("channel_id")

        for item in reservation.get("items", []):
            if channel_id:
                # Decrement channel-specific soft reservation
                key = self._channel_reserved_key(channel_id, item["product_id"])
                current = await self._get_channel_soft_reserved(channel_id, item["product_id"])
                new_value = max(0, current - item["quantity"])
                if new_value == 0:
                    await self.cache.delete(key)
                else:
                    await self.cache.set(key, new_value, ttl=RESERVATION_TTL + 60)
            else:
                # Legacy: decrement shared pool soft reservation
                await self._decrement_soft_reserved(item["product_id"], item["quantity"])

        # Delete the reservation
        await self.cache.delete(self._reservation_key(reservation_id))

        return True

    async def extend_reservation(
        self,
        reservation_id: str,
        additional_seconds: int = 300,
    ) -> bool:
        """
        Extend a reservation's TTL (e.g., when payment is processing).

        Args:
            reservation_id: The reservation to extend
            additional_seconds: Extra time to add (default 5 minutes)

        Returns:
            True if successful
        """
        reservation = await self.get_reservation(reservation_id)
        if not reservation:
            return False

        if reservation.get("status") != "ACTIVE":
            return False

        # Update expiry
        new_expiry = datetime.now(timezone.utc) + timedelta(seconds=additional_seconds)
        reservation["expires_at"] = new_expiry.isoformat()

        # Re-store with new TTL
        await self.cache.set(
            self._reservation_key(reservation_id),
            reservation,
            ttl=additional_seconds
        )

        return True


# ==================== API Helper Functions ====================

async def reserve_stock_for_checkout(
    db: AsyncSession,
    items: List[Dict],
    customer_id: Optional[str] = None,
    session_id: Optional[str] = None,
    channel: str = "D2C",
) -> ReservationResult:
    """
    Helper function to create stock reservation.

    Args:
        db: Database session
        items: List of {"product_id": str, "quantity": int}
        customer_id: Customer ID if logged in
        session_id: Session ID for tracking
        channel: Sales channel code (default D2C)

    Returns:
        ReservationResult
    """
    service = StockReservationService(db)
    reservation_items = [
        ReservationItem(
            product_id=item["product_id"],
            quantity=item["quantity"],
            warehouse_id=item.get("warehouse_id"),
        )
        for item in items
    ]
    return await service.create_reservation(
        items=reservation_items,
        customer_id=customer_id,
        session_id=session_id,
        channel=channel,
    )


async def confirm_checkout_reservation(
    db: AsyncSession,
    reservation_id: str,
    order_id: str,
) -> bool:
    """Helper to confirm reservation after payment."""
    service = StockReservationService(db)
    return await service.confirm_reservation(reservation_id, order_id)


async def release_checkout_reservation(
    db: AsyncSession,
    reservation_id: str,
) -> bool:
    """Helper to release reservation on payment failure."""
    service = StockReservationService(db)
    return await service.release_reservation(reservation_id)
