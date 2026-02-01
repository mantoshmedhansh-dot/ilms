"""Service for managing picklists and warehouse picking operations."""
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from math import ceil
import uuid

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.picklist import Picklist, PicklistItem, PicklistStatus, PicklistType
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductVariant
from app.models.inventory import StockItem, StockItemStatus
from app.models.wms import WarehouseBin
from app.schemas.picklist import PicklistGenerateRequest


class PicklistService:
    """Service for picklist management and picking operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== PICKLIST NUMBER GENERATION ====================

    async def generate_picklist_number(self) -> str:
        """Generate unique picklist number: PL-YYYYMMDD-XXXX"""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"PL-{today}-"

        stmt = select(func.count(Picklist.id)).where(
            Picklist.picklist_number.like(f"{prefix}%")
        )
        count = (await self.db.execute(stmt)).scalar() or 0

        return f"{prefix}{(count + 1):04d}"

    # ==================== PICKLIST CRUD ====================

    async def get_picklist(self, picklist_id: uuid.UUID) -> Optional[Picklist]:
        """Get picklist by ID with items."""
        stmt = (
            select(Picklist)
            .options(
                selectinload(Picklist.items),
                selectinload(Picklist.warehouse),
                selectinload(Picklist.assigned_user),
            )
            .where(Picklist.id == picklist_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_picklists(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[PicklistStatus] = None,
        assigned_to: Optional[uuid.UUID] = None,
        picklist_type: Optional[PicklistType] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Picklist], int]:
        """Get paginated picklists with filters."""
        stmt = (
            select(Picklist)
            .options(selectinload(Picklist.warehouse))
            .order_by(Picklist.priority, Picklist.created_at.desc())
        )

        filters = []
        if warehouse_id:
            filters.append(Picklist.warehouse_id == warehouse_id)
        if status:
            filters.append(Picklist.status == status)
        if assigned_to:
            filters.append(Picklist.assigned_to == assigned_to)
        if picklist_type:
            filters.append(Picklist.picklist_type == picklist_type)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count
        count_stmt = select(func.count(Picklist.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    # ==================== PICKLIST GENERATION ====================

    async def generate_picklist(
        self,
        request: PicklistGenerateRequest,
        created_by: Optional[uuid.UUID] = None
    ) -> Picklist:
        """Generate picklist from orders."""
        # Get orders
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.id.in_(request.order_ids),
                Order.status == OrderStatus.CONFIRMED
            )
        )
        result = await self.db.execute(stmt)
        orders = list(result.scalars().all())

        if not orders:
            raise ValueError("No valid orders found for picklist generation")

        # Create picklist
        picklist_number = await self.generate_picklist_number()
        picklist = Picklist(
            picklist_number=picklist_number,
            warehouse_id=request.warehouse_id,
            picklist_type=request.picklist_type,
            priority=request.priority,
            notes=request.notes,
            created_by=created_by,
            total_orders=len(orders),
        )

        # Add items from orders
        total_items = 0
        total_quantity = 0
        pick_sequence = 0

        for order in orders:
            for order_item in order.items:
                # Get bin location for product
                bin_location = await self._get_bin_location(
                    request.warehouse_id,
                    order_item.product_id
                )

                pick_sequence += 1
                picklist_item = PicklistItem(
                    picklist_id=picklist.id,
                    order_id=order.id,
                    order_item_id=order_item.id,
                    product_id=order_item.product_id,
                    variant_id=order_item.variant_id,
                    sku=order_item.product_sku,
                    product_name=order_item.product_name,
                    variant_name=order_item.variant_name,
                    bin_location=bin_location,
                    quantity_required=order_item.quantity,
                    pick_sequence=pick_sequence,
                )
                picklist.items.append(picklist_item)
                total_items += 1
                total_quantity += order_item.quantity

            # Update order status
            order.status = OrderStatus.PICKLIST_CREATED.value

        picklist.total_items = total_items
        picklist.total_quantity = total_quantity

        self.db.add(picklist)
        await self.db.commit()
        await self.db.refresh(picklist)

        return picklist

    async def _get_bin_location(
        self,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID
    ) -> Optional[str]:
        """Get bin location for a product in warehouse."""
        stmt = (
            select(StockItem.rack_location, WarehouseBin.bin_code)
            .outerjoin(WarehouseBin, StockItem.bin_id == WarehouseBin.id)
            .where(
                StockItem.warehouse_id == warehouse_id,
                StockItem.product_id == product_id,
                StockItem.status == StockItemStatus.AVAILABLE
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if row:
            return row[1] or row[0]  # Prefer bin_code over rack_location
        return None

    # ==================== PICKING OPERATIONS ====================

    async def assign_picker(
        self,
        picklist_id: uuid.UUID,
        assigned_to: uuid.UUID
    ) -> Picklist:
        """Assign picker to picklist."""
        picklist = await self.get_picklist(picklist_id)
        if not picklist:
            raise ValueError("Picklist not found")

        if picklist.status not in [PicklistStatus.PENDING, PicklistStatus.ASSIGNED]:
            raise ValueError(f"Cannot assign picker to picklist in {picklist.status} status")

        picklist.assigned_to = assigned_to
        picklist.assigned_at = datetime.now(timezone.utc)
        picklist.status = PicklistStatus.ASSIGNED.value

        await self.db.commit()
        await self.db.refresh(picklist)
        return picklist

    async def start_picking(self, picklist_id: uuid.UUID) -> Picklist:
        """Start picking process."""
        picklist = await self.get_picklist(picklist_id)
        if not picklist:
            raise ValueError("Picklist not found")

        if picklist.status not in [PicklistStatus.PENDING, PicklistStatus.ASSIGNED]:
            raise ValueError(f"Cannot start picking for picklist in {picklist.status} status")

        picklist.status = PicklistStatus.IN_PROGRESS.value
        picklist.started_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(picklist)
        return picklist

    async def pick_item(
        self,
        picklist_item_id: uuid.UUID,
        quantity_picked: int,
        serial_numbers: Optional[List[str]] = None,
        picked_by: Optional[uuid.UUID] = None,
        notes: Optional[str] = None
    ) -> PicklistItem:
        """Record picked item."""
        stmt = select(PicklistItem).where(PicklistItem.id == picklist_item_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()

        if not item:
            raise ValueError("Picklist item not found")

        if quantity_picked > item.pending_quantity:
            raise ValueError(f"Cannot pick {quantity_picked}, only {item.pending_quantity} remaining")

        item.quantity_picked += quantity_picked
        item.picked_by = picked_by
        item.picked_at = datetime.now(timezone.utc)
        item.notes = notes

        if serial_numbers:
            existing = item.picked_serials or ""
            if existing:
                item.picked_serials = existing + "," + ",".join(serial_numbers)
            else:
                item.picked_serials = ",".join(serial_numbers)

        if item.quantity_picked >= item.quantity_required:
            item.is_picked = True

        # Update picklist totals
        picklist = await self.get_picklist(item.picklist_id)
        picklist.picked_quantity = sum(i.quantity_picked for i in picklist.items)

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def mark_item_short(
        self,
        picklist_item_id: uuid.UUID,
        quantity_short: int,
        reason: str
    ) -> PicklistItem:
        """Mark item as short (not found in bin)."""
        stmt = select(PicklistItem).where(PicklistItem.id == picklist_item_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()

        if not item:
            raise ValueError("Picklist item not found")

        item.quantity_short = quantity_short
        item.is_short = True
        item.short_reason = reason

        # Mark as picked if all accounted for
        if item.quantity_picked + item.quantity_short >= item.quantity_required:
            item.is_picked = True

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def complete_picking(
        self,
        picklist_id: uuid.UUID,
        notes: Optional[str] = None
    ) -> Picklist:
        """Complete picking process."""
        picklist = await self.get_picklist(picklist_id)
        if not picklist:
            raise ValueError("Picklist not found")

        if picklist.status != PicklistStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete picklist in {picklist.status} status")

        # Check if all items are picked
        all_picked = all(item.is_picked for item in picklist.items)
        has_shorts = any(item.quantity_short > 0 for item in picklist.items)

        if all_picked:
            picklist.status = PicklistStatus.COMPLETED.value if not has_shorts else PicklistStatus.PARTIALLY_PICKED
        else:
            picklist.status = PicklistStatus.PARTIALLY_PICKED.value

        picklist.completed_at = datetime.now(timezone.utc)
        if notes:
            picklist.notes = (picklist.notes or "") + "\n" + notes

        # Update order statuses
        for item in picklist.items:
            if item.is_picked and not item.is_short:
                stmt = select(Order).where(Order.id == item.order_id)
                result = await self.db.execute(stmt)
                order = result.scalar_one_or_none()
                if order:
                    order.status = OrderStatus.PICKED.value
                    order.picked_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(picklist)
        return picklist

    async def cancel_picklist(
        self,
        picklist_id: uuid.UUID,
        reason: str
    ) -> Picklist:
        """Cancel picklist."""
        picklist = await self.get_picklist(picklist_id)
        if not picklist:
            raise ValueError("Picklist not found")

        if picklist.status in [PicklistStatus.COMPLETED, PicklistStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel picklist in {picklist.status} status")

        picklist.status = PicklistStatus.CANCELLED.value
        picklist.cancelled_at = datetime.now(timezone.utc)
        picklist.cancellation_reason = reason

        # Revert order statuses
        for item in picklist.items:
            stmt = select(Order).where(Order.id == item.order_id)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()
            if order and order.status == OrderStatus.PICKLIST_CREATED:
                order.status = OrderStatus.CONFIRMED.value

        await self.db.commit()
        await self.db.refresh(picklist)
        return picklist
