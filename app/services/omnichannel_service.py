"""
Omnichannel Service - Phase 3: BOPIS/BORIS & Ship-from-Store.

Business logic for omnichannel fulfillment operations.
"""
import uuid
import random
import string
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from math import radians, cos, sin, asin, sqrt

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.omnichannel import (
    StoreLocation, BOPISOrder, ShipFromStoreOrder,
    StoreInventoryReservation, StoreReturn
)
from app.schemas.omnichannel import (
    StoreLocationCreate, StoreLocationUpdate,
    BOPISOrderCreate, BOPISPickupRequest,
    ShipFromStoreCreate, SFSAcceptRequest, SFSRejectRequest, SFSShipRequest,
    StoreReturnCreate, ReturnInspectionRequest, ReturnRefundRequest,
    ReservationCreate, StoreOmnichannelStats, OmnichannelDashboardStats
)


class OmnichannelService:
    """Service for omnichannel fulfillment operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    # =========================================================================
    # STORE LOCATION MANAGEMENT
    # =========================================================================

    async def create_store(
        self,
        data: StoreLocationCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> StoreLocation:
        """Create a new store location."""
        # Check for duplicate store code
        existing = await self.db.execute(
            select(StoreLocation).where(
                StoreLocation.tenant_id == self.tenant_id,
                StoreLocation.store_code == data.store_code
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Store code {data.store_code} already exists"
            )

        store = StoreLocation(
            tenant_id=self.tenant_id,
            **data.model_dump()
        )

        self.db.add(store)
        await self.db.flush()
        await self.db.refresh(store)
        return store

    async def get_store(self, store_id: uuid.UUID) -> StoreLocation:
        """Get store by ID."""
        result = await self.db.execute(
            select(StoreLocation).where(
                StoreLocation.id == store_id,
                StoreLocation.tenant_id == self.tenant_id
            )
        )
        store = result.scalar_one_or_none()
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )
        return store

    async def get_stores(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        city: Optional[str] = None,
        bopis_enabled: Optional[bool] = None,
        sfs_enabled: Optional[bool] = None
    ) -> Tuple[List[StoreLocation], int]:
        """Get paginated list of stores."""
        query = select(StoreLocation).where(
            StoreLocation.tenant_id == self.tenant_id
        )

        if status:
            query = query.where(StoreLocation.status == status)
        if city:
            query = query.where(StoreLocation.city.ilike(f"%{city}%"))
        if bopis_enabled is not None:
            query = query.where(StoreLocation.bopis_enabled == bopis_enabled)
        if sfs_enabled is not None:
            query = query.where(StoreLocation.ship_from_store_enabled == sfs_enabled)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(StoreLocation.name).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def update_store(
        self,
        store_id: uuid.UUID,
        data: StoreLocationUpdate
    ) -> StoreLocation:
        """Update store location."""
        store = await self.get_store(store_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(store, field, value)

        await self.db.flush()
        await self.db.refresh(store)
        return store

    async def find_nearby_stores(
        self,
        latitude: Decimal,
        longitude: Decimal,
        radius_km: float = 10.0,
        bopis_enabled: Optional[bool] = None,
        sfs_enabled: Optional[bool] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find stores near a location using Haversine formula."""
        query = select(StoreLocation).where(
            StoreLocation.tenant_id == self.tenant_id,
            StoreLocation.status == "ACTIVE",
            StoreLocation.latitude.isnot(None),
            StoreLocation.longitude.isnot(None)
        )

        if bopis_enabled is not None:
            query = query.where(StoreLocation.bopis_enabled == bopis_enabled)
        if sfs_enabled is not None:
            query = query.where(StoreLocation.ship_from_store_enabled == sfs_enabled)

        result = await self.db.execute(query)
        stores = result.scalars().all()

        # Calculate distances
        stores_with_distance = []
        for store in stores:
            distance = self._haversine_distance(
                float(latitude), float(longitude),
                float(store.latitude), float(store.longitude)
            )
            if distance <= radius_km:
                stores_with_distance.append({
                    "store": store,
                    "distance_km": round(distance, 2)
                })

        # Sort by distance and limit
        stores_with_distance.sort(key=lambda x: x["distance_km"])
        return stores_with_distance[:limit]

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula."""
        R = 6371  # Earth's radius in km

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))

        return R * c

    # =========================================================================
    # BOPIS ORDER MANAGEMENT
    # =========================================================================

    async def create_bopis_order(
        self,
        data: BOPISOrderCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> BOPISOrder:
        """Create a BOPIS order."""
        # Verify store exists and has BOPIS enabled
        store = await self.get_store(data.store_id)
        if not store.bopis_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store does not support BOPIS"
            )

        # Check item limit
        total_items = sum(item.quantity for item in data.items)
        if store.bopis_max_items and total_items > store.bopis_max_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order exceeds max BOPIS items ({store.bopis_max_items})"
            )

        # Generate pickup code
        pickup_code = self._generate_pickup_code()

        # Calculate estimated ready time and pickup deadline
        now = datetime.now(timezone.utc)
        estimated_ready_at = now + timedelta(minutes=store.bopis_prep_time_minutes)
        pickup_deadline = estimated_ready_at + timedelta(hours=store.bopis_pickup_window_hours)

        # Prepare items data
        items_data = [item.model_dump() for item in data.items]

        bopis_order = BOPISOrder(
            tenant_id=self.tenant_id,
            order_id=data.order_id,
            store_id=data.store_id,
            customer_id=data.customer_id,
            pickup_code=pickup_code,
            pickup_location_type=data.pickup_location_type.value,
            pickup_instructions=data.pickup_instructions,
            estimated_ready_at=estimated_ready_at,
            pickup_deadline=pickup_deadline,
            items={"items": items_data},
            total_items=total_items,
            status="PENDING"
        )

        self.db.add(bopis_order)
        await self.db.flush()

        # Create inventory reservations
        for item in data.items:
            reservation = StoreInventoryReservation(
                tenant_id=self.tenant_id,
                store_id=data.store_id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                sku=item.sku,
                quantity_reserved=item.quantity,
                reservation_type="BOPIS",
                order_id=data.order_id,
                bopis_order_id=bopis_order.id,
                expires_at=pickup_deadline
            )
            self.db.add(reservation)

        await self.db.refresh(bopis_order)
        return bopis_order

    def _generate_pickup_code(self) -> str:
        """Generate unique pickup code."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=8))

    async def get_bopis_order(self, bopis_id: uuid.UUID) -> BOPISOrder:
        """Get BOPIS order by ID."""
        result = await self.db.execute(
            select(BOPISOrder)
            .options(selectinload(BOPISOrder.store))
            .where(
                BOPISOrder.id == bopis_id,
                BOPISOrder.tenant_id == self.tenant_id
            )
        )
        bopis = result.scalar_one_or_none()
        if not bopis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOPIS order not found"
            )
        return bopis

    async def get_bopis_by_pickup_code(self, pickup_code: str) -> BOPISOrder:
        """Get BOPIS order by pickup code."""
        result = await self.db.execute(
            select(BOPISOrder)
            .options(selectinload(BOPISOrder.store))
            .where(
                BOPISOrder.pickup_code == pickup_code,
                BOPISOrder.tenant_id == self.tenant_id
            )
        )
        bopis = result.scalar_one_or_none()
        if not bopis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOPIS order not found"
            )
        return bopis

    async def get_bopis_orders(
        self,
        skip: int = 0,
        limit: int = 20,
        store_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None
    ) -> Tuple[List[BOPISOrder], int]:
        """Get paginated list of BOPIS orders."""
        query = select(BOPISOrder).where(
            BOPISOrder.tenant_id == self.tenant_id
        )

        if store_id:
            query = query.where(BOPISOrder.store_id == store_id)
        if status:
            query = query.where(BOPISOrder.status == status)
        if customer_id:
            query = query.where(BOPISOrder.customer_id == customer_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(BOPISOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def confirm_bopis_order(
        self,
        bopis_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> BOPISOrder:
        """Store confirms BOPIS order availability."""
        bopis = await self.get_bopis_order(bopis_id)

        if bopis.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm order in {bopis.status} status"
            )

        bopis.status = "CONFIRMED"
        bopis.assigned_to = user_id

        await self.db.flush()
        await self.db.refresh(bopis)
        return bopis

    async def start_bopis_picking(
        self,
        bopis_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> BOPISOrder:
        """Start picking for BOPIS order."""
        bopis = await self.get_bopis_order(bopis_id)

        if bopis.status not in ["CONFIRMED", "PENDING"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start picking for order in {bopis.status} status"
            )

        bopis.status = "PICKING"
        bopis.assigned_to = user_id

        await self.db.flush()
        await self.db.refresh(bopis)
        return bopis

    async def mark_bopis_ready(
        self,
        bopis_id: uuid.UUID,
        user_id: uuid.UUID,
        storage_location: Optional[str] = None
    ) -> BOPISOrder:
        """Mark BOPIS order as ready for pickup."""
        bopis = await self.get_bopis_order(bopis_id)

        if bopis.status not in ["PICKING", "CONFIRMED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark ready for order in {bopis.status} status"
            )

        now = datetime.now(timezone.utc)
        bopis.status = "READY"
        bopis.actual_ready_at = now
        bopis.picked_by = user_id
        bopis.picked_items = bopis.total_items
        if storage_location:
            bopis.storage_location = storage_location

        await self.db.flush()
        await self.db.refresh(bopis)
        return bopis

    async def notify_customer_ready(
        self,
        bopis_id: uuid.UUID
    ) -> BOPISOrder:
        """Send ready notification to customer."""
        bopis = await self.get_bopis_order(bopis_id)

        if bopis.status != "READY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order must be READY to send notification"
            )

        bopis.status = "NOTIFIED"
        bopis.ready_notification_sent = True
        bopis.ready_notification_sent_at = datetime.now(timezone.utc)

        # TODO: Send actual notification (SMS/Email/Push)

        await self.db.flush()
        await self.db.refresh(bopis)
        return bopis

    async def complete_bopis_pickup(
        self,
        bopis_id: uuid.UUID,
        pickup_data: BOPISPickupRequest,
        user_id: uuid.UUID
    ) -> BOPISOrder:
        """Complete BOPIS order pickup."""
        bopis = await self.get_bopis_order(bopis_id)

        if bopis.status not in ["READY", "NOTIFIED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot complete pickup for order in {bopis.status} status"
            )

        now = datetime.now(timezone.utc)
        bopis.status = "PICKED_UP"
        bopis.picked_up_at = now
        bopis.picked_up_by_name = pickup_data.picked_up_by_name
        bopis.picked_up_by_phone = pickup_data.picked_up_by_phone
        bopis.id_verification_type = pickup_data.id_verification_type
        bopis.id_verification_number = pickup_data.id_verification_number
        bopis.handed_over_by = user_id

        if pickup_data.notes:
            bopis.notes = pickup_data.notes

        # Mark reservations as fulfilled
        await self._fulfill_reservations(bopis.id, "bopis")

        await self.db.flush()
        await self.db.refresh(bopis)
        return bopis

    async def cancel_bopis_order(
        self,
        bopis_id: uuid.UUID,
        reason: str,
        user_id: uuid.UUID
    ) -> BOPISOrder:
        """Cancel BOPIS order."""
        bopis = await self.get_bopis_order(bopis_id)

        if bopis.status in ["PICKED_UP", "CANCELLED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order in {bopis.status} status"
            )

        now = datetime.now(timezone.utc)
        bopis.status = "CANCELLED"
        bopis.cancelled_at = now
        bopis.cancellation_reason = reason
        bopis.cancelled_by = user_id

        # Release reservations
        await self._release_reservations(bopis.id, "bopis")

        await self.db.flush()
        await self.db.refresh(bopis)
        return bopis

    # =========================================================================
    # SHIP-FROM-STORE MANAGEMENT
    # =========================================================================

    async def create_sfs_order(
        self,
        data: ShipFromStoreCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> ShipFromStoreOrder:
        """Create ship-from-store order."""
        # Verify store has SFS enabled
        store = await self.get_store(data.store_id)
        if not store.ship_from_store_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store does not support ship-from-store"
            )

        # Check daily capacity
        if store.sfs_max_orders_per_day:
            today_count = await self._get_store_sfs_count_today(data.store_id)
            if today_count >= store.sfs_max_orders_per_day:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Store has reached daily SFS capacity"
                )

        # Generate SFS number
        sfs_number = await self._generate_sfs_number()

        # Prepare items data
        items_data = [item.model_dump() for item in data.items]
        total_items = sum(item.quantity for item in data.items)

        sfs_order = ShipFromStoreOrder(
            tenant_id=self.tenant_id,
            order_id=data.order_id,
            store_id=data.store_id,
            sfs_number=sfs_number,
            items={"items": items_data},
            total_items=total_items,
            shipping_address=data.shipping_address,
            sla_deadline=data.sla_deadline,
            status="PENDING"
        )

        self.db.add(sfs_order)
        await self.db.flush()
        await self.db.refresh(sfs_order)
        return sfs_order

    async def _get_store_sfs_count_today(self, store_id: uuid.UUID) -> int:
        """Get count of SFS orders for store today."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await self.db.execute(
            select(func.count()).where(
                ShipFromStoreOrder.store_id == store_id,
                ShipFromStoreOrder.tenant_id == self.tenant_id,
                ShipFromStoreOrder.created_at >= today_start
            )
        )
        return result.scalar() or 0

    async def _generate_sfs_number(self) -> str:
        """Generate unique SFS order number."""
        now = datetime.now(timezone.utc)
        prefix = f"SFS-{now.strftime('%Y%m%d')}"

        # Get count for today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count()).where(
                ShipFromStoreOrder.tenant_id == self.tenant_id,
                ShipFromStoreOrder.created_at >= today_start
            )
        )
        count = (result.scalar() or 0) + 1

        return f"{prefix}-{count:04d}"

    async def get_sfs_order(self, sfs_id: uuid.UUID) -> ShipFromStoreOrder:
        """Get SFS order by ID."""
        result = await self.db.execute(
            select(ShipFromStoreOrder)
            .options(selectinload(ShipFromStoreOrder.store))
            .where(
                ShipFromStoreOrder.id == sfs_id,
                ShipFromStoreOrder.tenant_id == self.tenant_id
            )
        )
        sfs = result.scalar_one_or_none()
        if not sfs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SFS order not found"
            )
        return sfs

    async def get_sfs_orders(
        self,
        skip: int = 0,
        limit: int = 20,
        store_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None
    ) -> Tuple[List[ShipFromStoreOrder], int]:
        """Get paginated list of SFS orders."""
        query = select(ShipFromStoreOrder).where(
            ShipFromStoreOrder.tenant_id == self.tenant_id
        )

        if store_id:
            query = query.where(ShipFromStoreOrder.store_id == store_id)
        if status:
            query = query.where(ShipFromStoreOrder.status == status)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(ShipFromStoreOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def accept_sfs_order(
        self,
        sfs_id: uuid.UUID,
        data: SFSAcceptRequest,
        user_id: uuid.UUID
    ) -> ShipFromStoreOrder:
        """Store accepts SFS order."""
        sfs = await self.get_sfs_order(sfs_id)

        if sfs.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept order in {sfs.status} status"
            )

        sfs.status = "ACCEPTED"
        sfs.accepted_by = user_id
        sfs.accepted_at = datetime.now(timezone.utc)

        if data.notes:
            sfs.notes = data.notes

        await self.db.flush()
        await self.db.refresh(sfs)
        return sfs

    async def reject_sfs_order(
        self,
        sfs_id: uuid.UUID,
        data: SFSRejectRequest,
        user_id: uuid.UUID
    ) -> ShipFromStoreOrder:
        """Store rejects SFS order."""
        sfs = await self.get_sfs_order(sfs_id)

        if sfs.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject order in {sfs.status} status"
            )

        sfs.status = "REJECTED"
        sfs.rejected_by = user_id
        sfs.rejected_at = datetime.now(timezone.utc)
        sfs.rejection_reason = data.rejection_reason

        await self.db.flush()
        await self.db.refresh(sfs)
        return sfs

    async def start_sfs_picking(
        self,
        sfs_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> ShipFromStoreOrder:
        """Start picking for SFS order."""
        sfs = await self.get_sfs_order(sfs_id)

        if sfs.status != "ACCEPTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start picking for order in {sfs.status} status"
            )

        sfs.status = "PICKING"
        sfs.picked_by = user_id
        sfs.picking_started_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(sfs)
        return sfs

    async def mark_sfs_packed(
        self,
        sfs_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> ShipFromStoreOrder:
        """Mark SFS order as packed."""
        sfs = await self.get_sfs_order(sfs_id)

        if sfs.status != "PICKING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark packed for order in {sfs.status} status"
            )

        sfs.status = "PACKED"
        sfs.packed_by = user_id
        sfs.packed_at = datetime.now(timezone.utc)
        sfs.picked_items = sfs.total_items
        sfs.packed_items = sfs.total_items

        await self.db.flush()
        await self.db.refresh(sfs)
        return sfs

    async def ship_sfs_order(
        self,
        sfs_id: uuid.UUID,
        data: SFSShipRequest,
        user_id: uuid.UUID
    ) -> ShipFromStoreOrder:
        """Mark SFS order as shipped."""
        sfs = await self.get_sfs_order(sfs_id)

        if sfs.status != "PACKED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot ship order in {sfs.status} status"
            )

        sfs.status = "SHIPPED"
        sfs.shipped_by = user_id
        sfs.shipped_at = datetime.now(timezone.utc)
        sfs.carrier_id = data.carrier_id
        sfs.tracking_number = data.tracking_number

        if data.notes:
            sfs.notes = data.notes

        await self.db.flush()
        await self.db.refresh(sfs)
        return sfs

    # =========================================================================
    # STORE RETURNS (BORIS)
    # =========================================================================

    async def create_store_return(
        self,
        data: StoreReturnCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> StoreReturn:
        """Create in-store return (BORIS)."""
        # Verify store has BORIS enabled
        store = await self.get_store(data.store_id)
        if not store.boris_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store does not support in-store returns"
            )

        # Generate return number
        return_number = await self._generate_return_number()

        # Prepare items data
        items_data = [item.model_dump() for item in data.items]
        total_items = sum(item.quantity for item in data.items)

        store_return = StoreReturn(
            tenant_id=self.tenant_id,
            return_number=return_number,
            order_id=data.order_id,
            store_id=data.store_id,
            customer_id=data.customer_id,
            items={"items": items_data},
            total_items=total_items,
            return_reason=data.return_reason,
            return_comments=data.return_comments,
            scheduled_date=data.scheduled_date,
            scheduled_time_slot=data.scheduled_time_slot,
            status="INITIATED" if not data.scheduled_date else "SCHEDULED"
        )

        self.db.add(store_return)
        await self.db.flush()
        await self.db.refresh(store_return)
        return store_return

    async def _generate_return_number(self) -> str:
        """Generate unique return number."""
        now = datetime.now(timezone.utc)
        prefix = f"RET-{now.strftime('%Y%m%d')}"

        # Get count for today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count()).where(
                StoreReturn.tenant_id == self.tenant_id,
                StoreReturn.created_at >= today_start
            )
        )
        count = (result.scalar() or 0) + 1

        return f"{prefix}-{count:04d}"

    async def get_store_return(self, return_id: uuid.UUID) -> StoreReturn:
        """Get store return by ID."""
        result = await self.db.execute(
            select(StoreReturn)
            .options(selectinload(StoreReturn.store))
            .where(
                StoreReturn.id == return_id,
                StoreReturn.tenant_id == self.tenant_id
            )
        )
        ret = result.scalar_one_or_none()
        if not ret:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store return not found"
            )
        return ret

    async def get_store_returns(
        self,
        skip: int = 0,
        limit: int = 20,
        store_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None
    ) -> Tuple[List[StoreReturn], int]:
        """Get paginated list of store returns."""
        query = select(StoreReturn).where(
            StoreReturn.tenant_id == self.tenant_id
        )

        if store_id:
            query = query.where(StoreReturn.store_id == store_id)
        if status:
            query = query.where(StoreReturn.status == status)
        if customer_id:
            query = query.where(StoreReturn.customer_id == customer_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(StoreReturn.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def receive_return(
        self,
        return_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> StoreReturn:
        """Mark return as received at store."""
        ret = await self.get_store_return(return_id)

        if ret.status not in ["INITIATED", "SCHEDULED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot receive return in {ret.status} status"
            )

        ret.status = "RECEIVED"
        ret.received_at = datetime.now(timezone.utc)
        ret.received_by = user_id

        await self.db.flush()
        await self.db.refresh(ret)
        return ret

    async def inspect_return(
        self,
        return_id: uuid.UUID,
        data: ReturnInspectionRequest,
        user_id: uuid.UUID
    ) -> StoreReturn:
        """Complete return inspection."""
        ret = await self.get_store_return(return_id)

        if ret.status != "RECEIVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot inspect return in {ret.status} status"
            )

        ret.status = "INSPECTING"
        ret.inspected_at = datetime.now(timezone.utc)
        ret.inspected_by = user_id
        ret.item_condition = data.item_condition
        ret.inspection_notes = data.inspection_notes
        ret.inspected_items = ret.total_items
        ret.approved_items = data.approved_items
        ret.rejected_items = data.rejected_items

        # Auto-approve or reject based on inspection
        if data.approved_items > 0:
            ret.status = "APPROVED"
        elif data.rejected_items == ret.total_items:
            ret.status = "REJECTED"

        await self.db.flush()
        await self.db.refresh(ret)
        return ret

    async def process_return_refund(
        self,
        return_id: uuid.UUID,
        data: ReturnRefundRequest,
        user_id: uuid.UUID
    ) -> StoreReturn:
        """Process refund for approved return."""
        ret = await self.get_store_return(return_id)

        if ret.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot refund return in {ret.status} status"
            )

        ret.status = "REFUNDED"
        ret.refund_amount = data.refund_amount
        ret.refund_method = data.refund_method
        ret.refunded_at = datetime.now(timezone.utc)
        ret.approved_by = user_id

        if data.notes:
            ret.notes = data.notes

        await self.db.flush()
        await self.db.refresh(ret)
        return ret

    async def complete_return(
        self,
        return_id: uuid.UUID,
        restock_decision: str,
        user_id: uuid.UUID
    ) -> StoreReturn:
        """Complete return with restock decision."""
        ret = await self.get_store_return(return_id)

        if ret.status != "REFUNDED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot complete return in {ret.status} status"
            )

        ret.status = "COMPLETED"
        ret.completed_at = datetime.now(timezone.utc)
        ret.restock_decision = restock_decision
        ret.restocked_at = datetime.now(timezone.utc) if restock_decision == "RESTOCK" else None

        await self.db.flush()
        await self.db.refresh(ret)
        return ret

    # =========================================================================
    # INVENTORY RESERVATIONS
    # =========================================================================

    async def _fulfill_reservations(
        self,
        ref_id: uuid.UUID,
        ref_type: str  # "bopis" or "sfs"
    ):
        """Mark reservations as fulfilled."""
        if ref_type == "bopis":
            query = select(StoreInventoryReservation).where(
                StoreInventoryReservation.bopis_order_id == ref_id,
                StoreInventoryReservation.tenant_id == self.tenant_id
            )
        else:
            query = select(StoreInventoryReservation).where(
                StoreInventoryReservation.sfs_order_id == ref_id,
                StoreInventoryReservation.tenant_id == self.tenant_id
            )

        result = await self.db.execute(query)
        reservations = result.scalars().all()

        now = datetime.now(timezone.utc)
        for res in reservations:
            res.quantity_fulfilled = res.quantity_reserved
            res.fulfilled_at = now
            res.is_active = False

    async def _release_reservations(
        self,
        ref_id: uuid.UUID,
        ref_type: str  # "bopis" or "sfs"
    ):
        """Release reservations back to inventory."""
        if ref_type == "bopis":
            query = select(StoreInventoryReservation).where(
                StoreInventoryReservation.bopis_order_id == ref_id,
                StoreInventoryReservation.tenant_id == self.tenant_id
            )
        else:
            query = select(StoreInventoryReservation).where(
                StoreInventoryReservation.sfs_order_id == ref_id,
                StoreInventoryReservation.tenant_id == self.tenant_id
            )

        result = await self.db.execute(query)
        reservations = result.scalars().all()

        now = datetime.now(timezone.utc)
        for res in reservations:
            res.quantity_released = res.quantity_reserved - res.quantity_fulfilled
            res.released_at = now
            res.is_active = False

    # =========================================================================
    # STATISTICS
    # =========================================================================

    async def get_store_stats(self, store_id: uuid.UUID) -> StoreOmnichannelStats:
        """Get omnichannel stats for a store."""
        store = await self.get_store(store_id)

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # BOPIS Stats
        bopis_today = await self.db.execute(
            select(func.count()).where(
                BOPISOrder.store_id == store_id,
                BOPISOrder.tenant_id == self.tenant_id,
                BOPISOrder.created_at >= today_start
            )
        )
        bopis_pending = await self.db.execute(
            select(func.count()).where(
                BOPISOrder.store_id == store_id,
                BOPISOrder.tenant_id == self.tenant_id,
                BOPISOrder.status.in_(["PENDING", "CONFIRMED", "PICKING"])
            )
        )
        bopis_ready = await self.db.execute(
            select(func.count()).where(
                BOPISOrder.store_id == store_id,
                BOPISOrder.tenant_id == self.tenant_id,
                BOPISOrder.status.in_(["READY", "NOTIFIED"])
            )
        )
        bopis_picked_up = await self.db.execute(
            select(func.count()).where(
                BOPISOrder.store_id == store_id,
                BOPISOrder.tenant_id == self.tenant_id,
                BOPISOrder.status == "PICKED_UP",
                BOPISOrder.picked_up_at >= today_start
            )
        )

        # SFS Stats
        sfs_today = await self.db.execute(
            select(func.count()).where(
                ShipFromStoreOrder.store_id == store_id,
                ShipFromStoreOrder.tenant_id == self.tenant_id,
                ShipFromStoreOrder.created_at >= today_start
            )
        )
        sfs_pending = await self.db.execute(
            select(func.count()).where(
                ShipFromStoreOrder.store_id == store_id,
                ShipFromStoreOrder.tenant_id == self.tenant_id,
                ShipFromStoreOrder.status == "PENDING"
            )
        )
        sfs_shipped = await self.db.execute(
            select(func.count()).where(
                ShipFromStoreOrder.store_id == store_id,
                ShipFromStoreOrder.tenant_id == self.tenant_id,
                ShipFromStoreOrder.status == "SHIPPED",
                ShipFromStoreOrder.shipped_at >= today_start
            )
        )

        # Return Stats
        returns_today = await self.db.execute(
            select(func.count()).where(
                StoreReturn.store_id == store_id,
                StoreReturn.tenant_id == self.tenant_id,
                StoreReturn.created_at >= today_start
            )
        )
        returns_pending = await self.db.execute(
            select(func.count()).where(
                StoreReturn.store_id == store_id,
                StoreReturn.tenant_id == self.tenant_id,
                StoreReturn.status.in_(["INITIATED", "SCHEDULED", "RECEIVED", "INSPECTING"])
            )
        )

        # Reservations
        total_reservations = await self.db.execute(
            select(func.count()).where(
                StoreInventoryReservation.store_id == store_id,
                StoreInventoryReservation.tenant_id == self.tenant_id
            )
        )
        active_reservations = await self.db.execute(
            select(func.count()).where(
                StoreInventoryReservation.store_id == store_id,
                StoreInventoryReservation.tenant_id == self.tenant_id,
                StoreInventoryReservation.is_active == True
            )
        )

        return StoreOmnichannelStats(
            store_id=store.id,
            store_code=store.store_code,
            store_name=store.name,
            bopis_orders_today=bopis_today.scalar() or 0,
            bopis_pending=bopis_pending.scalar() or 0,
            bopis_ready=bopis_ready.scalar() or 0,
            bopis_picked_up_today=bopis_picked_up.scalar() or 0,
            bopis_expired_today=0,  # TODO: Calculate expired
            sfs_orders_today=sfs_today.scalar() or 0,
            sfs_pending=sfs_pending.scalar() or 0,
            sfs_shipped_today=sfs_shipped.scalar() or 0,
            sfs_rejected_today=0,  # TODO: Calculate rejected
            returns_today=returns_today.scalar() or 0,
            returns_pending=returns_pending.scalar() or 0,
            returns_completed_today=0,  # TODO: Calculate completed
            total_reservations=total_reservations.scalar() or 0,
            active_reservations=active_reservations.scalar() or 0
        )

    async def get_dashboard_stats(self) -> OmnichannelDashboardStats:
        """Get overall omnichannel dashboard stats."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Store counts
        total_stores = await self.db.execute(
            select(func.count()).where(
                StoreLocation.tenant_id == self.tenant_id,
                StoreLocation.status == "ACTIVE"
            )
        )
        bopis_stores = await self.db.execute(
            select(func.count()).where(
                StoreLocation.tenant_id == self.tenant_id,
                StoreLocation.status == "ACTIVE",
                StoreLocation.bopis_enabled == True
            )
        )
        sfs_stores = await self.db.execute(
            select(func.count()).where(
                StoreLocation.tenant_id == self.tenant_id,
                StoreLocation.status == "ACTIVE",
                StoreLocation.ship_from_store_enabled == True
            )
        )
        boris_stores = await self.db.execute(
            select(func.count()).where(
                StoreLocation.tenant_id == self.tenant_id,
                StoreLocation.status == "ACTIVE",
                StoreLocation.boris_enabled == True
            )
        )

        # BOPIS Stats
        total_bopis = await self.db.execute(
            select(func.count()).where(
                BOPISOrder.tenant_id == self.tenant_id,
                BOPISOrder.created_at >= today_start
            )
        )
        bopis_ready = await self.db.execute(
            select(func.count()).where(
                BOPISOrder.tenant_id == self.tenant_id,
                BOPISOrder.status.in_(["READY", "NOTIFIED"])
            )
        )
        bopis_picked_up = await self.db.execute(
            select(func.count()).where(
                BOPISOrder.tenant_id == self.tenant_id,
                BOPISOrder.status == "PICKED_UP",
                BOPISOrder.picked_up_at >= today_start
            )
        )

        # SFS Stats
        total_sfs = await self.db.execute(
            select(func.count()).where(
                ShipFromStoreOrder.tenant_id == self.tenant_id,
                ShipFromStoreOrder.created_at >= today_start
            )
        )
        sfs_pending = await self.db.execute(
            select(func.count()).where(
                ShipFromStoreOrder.tenant_id == self.tenant_id,
                ShipFromStoreOrder.status == "PENDING"
            )
        )
        sfs_shipped = await self.db.execute(
            select(func.count()).where(
                ShipFromStoreOrder.tenant_id == self.tenant_id,
                ShipFromStoreOrder.status == "SHIPPED",
                ShipFromStoreOrder.shipped_at >= today_start
            )
        )

        # Return Stats
        total_returns = await self.db.execute(
            select(func.count()).where(
                StoreReturn.tenant_id == self.tenant_id,
                StoreReturn.created_at >= today_start
            )
        )
        returns_pending = await self.db.execute(
            select(func.count()).where(
                StoreReturn.tenant_id == self.tenant_id,
                StoreReturn.status.in_(["RECEIVED", "INSPECTING"])
            )
        )
        returns_completed = await self.db.execute(
            select(func.count()).where(
                StoreReturn.tenant_id == self.tenant_id,
                StoreReturn.status == "COMPLETED",
                StoreReturn.completed_at >= today_start
            )
        )

        # Refunded amount today
        refunded_result = await self.db.execute(
            select(func.coalesce(func.sum(StoreReturn.refund_amount), 0)).where(
                StoreReturn.tenant_id == self.tenant_id,
                StoreReturn.status.in_(["REFUNDED", "COMPLETED"]),
                StoreReturn.refunded_at >= today_start
            )
        )

        return OmnichannelDashboardStats(
            total_stores=total_stores.scalar() or 0,
            bopis_enabled_stores=bopis_stores.scalar() or 0,
            sfs_enabled_stores=sfs_stores.scalar() or 0,
            boris_enabled_stores=boris_stores.scalar() or 0,
            total_bopis_today=total_bopis.scalar() or 0,
            bopis_ready_for_pickup=bopis_ready.scalar() or 0,
            bopis_picked_up_today=bopis_picked_up.scalar() or 0,
            bopis_expired_today=0,
            total_sfs_today=total_sfs.scalar() or 0,
            sfs_pending=sfs_pending.scalar() or 0,
            sfs_shipped_today=sfs_shipped.scalar() or 0,
            total_store_returns_today=total_returns.scalar() or 0,
            returns_pending_inspection=returns_pending.scalar() or 0,
            returns_completed_today=returns_completed.scalar() or 0,
            returns_refunded_today=refunded_result.scalar() or Decimal("0")
        )
