"""Service for Warehouse Management System operations."""
from typing import List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wms import WarehouseZone, WarehouseBin, PutAwayRule, ZoneType, BinType
from app.models.inventory import StockItem, StockItemStatus
from app.models.product import Product
from app.schemas.wms import ZoneCreate, ZoneUpdate, BinCreate, BinUpdate, PutAwayRuleCreate


class WMSService:
    """Service for WMS zone, bin, and putaway management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== ZONE MANAGEMENT ====================

    async def get_zone(self, zone_id: uuid.UUID) -> Optional[WarehouseZone]:
        """Get zone by ID."""
        stmt = (
            select(WarehouseZone)
            .options(selectinload(WarehouseZone.bins))
            .where(WarehouseZone.id == zone_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_zones(
        self,
        warehouse_id: uuid.UUID,
        zone_type: Optional[ZoneType] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[WarehouseZone], int]:
        """Get zones for warehouse."""
        stmt = (
            select(WarehouseZone)
            .where(WarehouseZone.warehouse_id == warehouse_id)
            .order_by(WarehouseZone.sort_order, WarehouseZone.zone_code)
        )

        filters = [WarehouseZone.warehouse_id == warehouse_id]
        if zone_type:
            filters.append(WarehouseZone.zone_type == zone_type)
        if is_active is not None:
            filters.append(WarehouseZone.is_active == is_active)

        stmt = stmt.where(and_(*filters))

        # Count
        count_stmt = select(func.count(WarehouseZone.id)).where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def create_zone(self, data: ZoneCreate) -> WarehouseZone:
        """Create warehouse zone."""
        # Check if zone code exists in warehouse
        stmt = select(WarehouseZone).where(
            WarehouseZone.warehouse_id == data.warehouse_id,
            WarehouseZone.zone_code == data.zone_code
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError(f"Zone code {data.zone_code} already exists in this warehouse")

        zone = WarehouseZone(**data.model_dump())
        self.db.add(zone)
        await self.db.commit()
        await self.db.refresh(zone)
        return zone

    async def update_zone(
        self,
        zone_id: uuid.UUID,
        data: ZoneUpdate
    ) -> WarehouseZone:
        """Update warehouse zone."""
        zone = await self.get_zone(zone_id)
        if not zone:
            raise ValueError("Zone not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(zone, key, value)

        await self.db.commit()
        await self.db.refresh(zone)
        return zone

    # ==================== BIN MANAGEMENT ====================

    async def get_bin(self, bin_id: uuid.UUID) -> Optional[WarehouseBin]:
        """Get bin by ID."""
        stmt = (
            select(WarehouseBin)
            .options(selectinload(WarehouseBin.zone))
            .where(WarehouseBin.id == bin_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_bin_by_code(
        self,
        warehouse_id: uuid.UUID,
        bin_code: str
    ) -> Optional[WarehouseBin]:
        """Get bin by code."""
        stmt = select(WarehouseBin).where(
            WarehouseBin.warehouse_id == warehouse_id,
            WarehouseBin.bin_code == bin_code
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_bins(
        self,
        warehouse_id: uuid.UUID,
        zone_id: Optional[uuid.UUID] = None,
        bin_type: Optional[BinType] = None,
        is_active: bool = True,
        only_available: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[WarehouseBin], int]:
        """Get bins with filters."""
        stmt = (
            select(WarehouseBin)
            .options(selectinload(WarehouseBin.zone))
            .where(WarehouseBin.warehouse_id == warehouse_id)
            .order_by(WarehouseBin.pick_sequence, WarehouseBin.bin_code)
        )

        filters = [WarehouseBin.warehouse_id == warehouse_id]
        if zone_id:
            filters.append(WarehouseBin.zone_id == zone_id)
        if bin_type:
            filters.append(WarehouseBin.bin_type == bin_type)
        if is_active is not None:
            filters.append(WarehouseBin.is_active == is_active)
        if only_available:
            filters.append(WarehouseBin.is_reserved == False)
            filters.append(
                or_(
                    WarehouseBin.max_capacity.is_(None),
                    WarehouseBin.current_items < WarehouseBin.max_capacity
                )
            )

        stmt = stmt.where(and_(*filters))

        # Count
        count_stmt = select(func.count(WarehouseBin.id)).where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def create_bin(self, data: BinCreate) -> WarehouseBin:
        """Create warehouse bin."""
        # Check if bin code exists
        existing = await self.get_bin_by_code(data.warehouse_id, data.bin_code)
        if existing:
            raise ValueError(f"Bin code {data.bin_code} already exists in this warehouse")

        bin = WarehouseBin(**data.model_dump())
        self.db.add(bin)
        await self.db.commit()
        await self.db.refresh(bin)
        return bin

    async def create_bins_bulk(
        self,
        warehouse_id: uuid.UUID,
        zone_id: Optional[uuid.UUID],
        prefix: str,
        aisle_range: Tuple[str, str],
        rack_range: Tuple[int, int],
        shelf_range: Tuple[int, int],
        bin_type: BinType = BinType.SHELF,
        max_capacity: Optional[int] = None
    ) -> int:
        """Bulk create bins with pattern."""
        count = 0
        sequence = 0

        for aisle in range(ord(aisle_range[0]), ord(aisle_range[1]) + 1):
            aisle_char = chr(aisle)
            for rack in range(rack_range[0], rack_range[1] + 1):
                for shelf in range(shelf_range[0], shelf_range[1] + 1):
                    bin_code = f"{prefix}{aisle_char}{rack:02d}-S{shelf:02d}"
                    sequence += 1

                    # Check if exists
                    existing = await self.get_bin_by_code(warehouse_id, bin_code)
                    if existing:
                        continue

                    bin = WarehouseBin(
                        warehouse_id=warehouse_id,
                        zone_id=zone_id,
                        bin_code=bin_code,
                        aisle=aisle_char,
                        rack=str(rack),
                        shelf=str(shelf),
                        bin_type=bin_type,
                        max_capacity=max_capacity,
                        pick_sequence=sequence,
                    )
                    self.db.add(bin)
                    count += 1

        await self.db.commit()
        return count

    async def update_bin(
        self,
        bin_id: uuid.UUID,
        data: BinUpdate
    ) -> WarehouseBin:
        """Update warehouse bin."""
        bin = await self.get_bin(bin_id)
        if not bin:
            raise ValueError("Bin not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(bin, key, value)

        await self.db.commit()
        await self.db.refresh(bin)
        return bin

    # ==================== BIN ENQUIRY ====================

    async def get_bin_contents(
        self,
        bin_id: uuid.UUID
    ) -> Tuple[WarehouseBin, List[StockItem]]:
        """Get bin with its contents."""
        bin = await self.get_bin(bin_id)
        if not bin:
            raise ValueError("Bin not found")

        stmt = (
            select(StockItem)
            .options(selectinload(StockItem.product))
            .where(
                StockItem.bin_id == bin_id,
                StockItem.status.in_([
                    StockItemStatus.AVAILABLE,
                    StockItemStatus.RESERVED,
                    StockItemStatus.ALLOCATED
                ])
            )
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return bin, items

    # ==================== PUTAWAY RULES ====================

    async def get_putaway_rules(
        self,
        warehouse_id: uuid.UUID,
        is_active: bool = True
    ) -> List[PutAwayRule]:
        """Get putaway rules for warehouse."""
        stmt = (
            select(PutAwayRule)
            .options(selectinload(PutAwayRule.target_zone))
            .where(
                PutAwayRule.warehouse_id == warehouse_id,
                PutAwayRule.is_active == is_active
            )
            .order_by(PutAwayRule.priority)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_putaway_rule(self, data: PutAwayRuleCreate) -> PutAwayRule:
        """Create putaway rule."""
        rule = PutAwayRule(**data.model_dump())
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def suggest_bin(
        self,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int = 1
    ) -> List[WarehouseBin]:
        """Suggest bins for putaway based on rules."""
        # Get product details
        stmt = select(Product).where(Product.id == product_id)
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise ValueError("Product not found")

        # Get matching putaway rules
        rules = await self.get_putaway_rules(warehouse_id)

        target_zone_id = None
        bin_pattern = None

        for rule in rules:
            # Check if rule matches
            if rule.product_id and rule.product_id == product_id:
                target_zone_id = rule.target_zone_id
                bin_pattern = rule.target_bin_pattern
                break
            if rule.category_id and rule.category_id == product.category_id:
                target_zone_id = rule.target_zone_id
                bin_pattern = rule.target_bin_pattern
                break
            if rule.brand_id and rule.brand_id == product.brand_id:
                target_zone_id = rule.target_zone_id
                bin_pattern = rule.target_bin_pattern
                break
            # Default rule (no criteria)
            if not rule.product_id and not rule.category_id and not rule.brand_id:
                target_zone_id = rule.target_zone_id
                bin_pattern = rule.target_bin_pattern

        # Find available bins
        stmt = (
            select(WarehouseBin)
            .options(selectinload(WarehouseBin.zone))
            .where(
                WarehouseBin.warehouse_id == warehouse_id,
                WarehouseBin.is_active == True,
                WarehouseBin.is_reserved == False,
                WarehouseBin.is_receivable == True
            )
            .order_by(WarehouseBin.pick_sequence)
        )

        if target_zone_id:
            stmt = stmt.where(WarehouseBin.zone_id == target_zone_id)

        if bin_pattern:
            stmt = stmt.where(WarehouseBin.bin_code.like(bin_pattern.replace("*", "%")))

        # Filter by available capacity
        stmt = stmt.where(
            or_(
                WarehouseBin.max_capacity.is_(None),
                WarehouseBin.current_items + quantity <= WarehouseBin.max_capacity
            )
        )

        stmt = stmt.limit(5)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def execute_putaway(
        self,
        stock_item_id: uuid.UUID,
        bin_id: uuid.UUID,
        notes: Optional[str] = None
    ) -> StockItem:
        """Execute putaway - assign item to bin."""
        # Get stock item
        stmt = select(StockItem).where(StockItem.id == stock_item_id)
        result = await self.db.execute(stmt)
        stock_item = result.scalar_one_or_none()

        if not stock_item:
            raise ValueError("Stock item not found")

        # Get bin
        bin = await self.get_bin(bin_id)
        if not bin:
            raise ValueError("Bin not found")

        if stock_item.warehouse_id != bin.warehouse_id:
            raise ValueError("Stock item and bin are in different warehouses")

        # Check bin capacity
        if bin.max_capacity and bin.current_items >= bin.max_capacity:
            raise ValueError("Bin is at capacity")

        # Update old bin if item was in one
        if stock_item.bin_id:
            old_bin = await self.get_bin(stock_item.bin_id)
            if old_bin:
                old_bin.current_items = max(0, old_bin.current_items - 1)

        # Assign to new bin
        stock_item.bin_id = bin_id
        stock_item.rack_location = bin.bin_code

        # Update bin counts
        bin.current_items += 1
        bin.last_activity_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(stock_item)
        return stock_item

    async def move_inventory(
        self,
        stock_item_id: uuid.UUID,
        from_bin_id: uuid.UUID,
        to_bin_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> StockItem:
        """Move inventory from one bin to another."""
        # Get stock item
        stmt = select(StockItem).where(
            StockItem.id == stock_item_id,
            StockItem.bin_id == from_bin_id
        )
        result = await self.db.execute(stmt)
        stock_item = result.scalar_one_or_none()

        if not stock_item:
            raise ValueError("Stock item not found in source bin")

        # Get target bin
        to_bin = await self.get_bin(to_bin_id)
        if not to_bin:
            raise ValueError("Target bin not found")

        # Check capacity
        if to_bin.max_capacity and to_bin.current_items >= to_bin.max_capacity:
            raise ValueError("Target bin is at capacity")

        # Get source bin
        from_bin = await self.get_bin(from_bin_id)

        # Update bins
        if from_bin:
            from_bin.current_items = max(0, from_bin.current_items - 1)

        to_bin.current_items += 1
        to_bin.last_activity_at = datetime.now(timezone.utc)

        # Update stock item
        stock_item.bin_id = to_bin_id
        stock_item.rack_location = to_bin.bin_code
        stock_item.last_movement_date = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(stock_item)
        return stock_item
