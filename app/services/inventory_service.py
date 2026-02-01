"""Inventory Service for stock management operations."""
from typing import Optional, List, Tuple
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.warehouse import Warehouse, WarehouseType
from app.models.inventory import (
    StockItem, StockItemStatus,
    InventorySummary,
    StockMovement, StockMovementType,
)
from app.models.stock_transfer import (
    StockTransfer, StockTransferItem, StockTransferSerial,
    TransferStatus, TransferType,
)
from app.models.stock_adjustment import (
    StockAdjustment, StockAdjustmentItem,
    AdjustmentType, AdjustmentStatus,
    InventoryAudit,
)
from app.models.product import Product, ProductVariant


class InventoryService:
    """Service for inventory management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== WAREHOUSE METHODS ====================

    async def get_warehouses(
        self,
        warehouse_type: Optional[WarehouseType] = None,
        region_id: Optional[uuid.UUID] = None,
        is_active: bool = True,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Warehouse], int]:
        """Get paginated list of warehouses."""
        query = select(Warehouse)

        # Filters
        conditions = [Warehouse.is_active == is_active]

        if warehouse_type:
            conditions.append(Warehouse.warehouse_type == warehouse_type)
        if region_id:
            conditions.append(Warehouse.region_id == region_id)
        if search:
            conditions.append(
                or_(
                    Warehouse.name.ilike(f"%{search}%"),
                    Warehouse.code.ilike(f"%{search}%"),
                    Warehouse.city.ilike(f"%{search}%"),
                )
            )

        query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(Warehouse.name).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def get_warehouse_by_id(self, warehouse_id: uuid.UUID) -> Optional[Warehouse]:
        """Get warehouse by ID."""
        query = select(Warehouse).where(Warehouse.id == warehouse_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_warehouse_by_code(self, code: str) -> Optional[Warehouse]:
        """Get warehouse by code."""
        query = select(Warehouse).where(Warehouse.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_warehouse(self, data: dict) -> Warehouse:
        """Create a new warehouse."""
        # Generate code if not provided
        if not data.get("code"):
            data["code"] = await self._generate_warehouse_code(data.get("warehouse_type", WarehouseType.REGIONAL))

        warehouse = Warehouse(**data)
        self.db.add(warehouse)
        await self.db.commit()
        await self.db.refresh(warehouse)
        return warehouse

    async def update_warehouse(self, warehouse_id: uuid.UUID, data: dict) -> Optional[Warehouse]:
        """Update a warehouse."""
        warehouse = await self.get_warehouse_by_id(warehouse_id)
        if not warehouse:
            return None

        for key, value in data.items():
            if hasattr(warehouse, key):
                setattr(warehouse, key, value)

        await self.db.commit()
        await self.db.refresh(warehouse)
        return warehouse

    async def _generate_warehouse_code(self, warehouse_type: WarehouseType) -> str:
        """Generate unique warehouse code."""
        prefix_map = {
            WarehouseType.MAIN: "WH-M",
            WarehouseType.REGIONAL: "WH-R",
            WarehouseType.SERVICE_CENTER: "WH-S",
            WarehouseType.DEALER: "WH-D",
            WarehouseType.VIRTUAL: "WH-V",
        }
        prefix = prefix_map.get(warehouse_type, "WH")

        # Get max number
        query = select(func.max(Warehouse.code)).where(Warehouse.code.like(f"{prefix}%"))
        result = await self.db.scalar(query)

        if result:
            try:
                num = int(result.split("-")[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1

        return f"{prefix}-{num:04d}"

    # ==================== STOCK ITEM METHODS ====================

    async def get_stock_items(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        status: Optional[StockItemStatus] = None,
        serial_number: Optional[str] = None,
        batch_number: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockItem], int]:
        """Get paginated list of stock items."""
        query = select(StockItem).options(
            joinedload(StockItem.product),
            joinedload(StockItem.warehouse),
        )

        conditions = []
        if warehouse_id:
            conditions.append(StockItem.warehouse_id == warehouse_id)
        if product_id:
            conditions.append(StockItem.product_id == product_id)
        if status:
            conditions.append(StockItem.status == status)
        if serial_number:
            conditions.append(StockItem.serial_number.ilike(f"%{serial_number}%"))
        if batch_number:
            conditions.append(StockItem.batch_number == batch_number)

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(StockItem.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().unique().all(), total

    async def get_stock_item_by_id(self, item_id: uuid.UUID) -> Optional[StockItem]:
        """Get stock item by ID."""
        query = select(StockItem).options(
            joinedload(StockItem.product),
            joinedload(StockItem.warehouse),
        ).where(StockItem.id == item_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_stock_item_by_serial(self, serial_number: str) -> Optional[StockItem]:
        """Get stock item by serial number."""
        query = select(StockItem).options(
            joinedload(StockItem.product),
            joinedload(StockItem.warehouse),
        ).where(StockItem.serial_number == serial_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_stock_item(self, data: dict, created_by: uuid.UUID) -> StockItem:
        """Create a single stock item."""
        stock_item = StockItem(**data)
        self.db.add(stock_item)

        # Update inventory summary
        await self._update_inventory_summary(
            data["warehouse_id"],
            data["product_id"],
            data.get("variant_id"),
            quantity_change=1,
        )

        # Create stock movement
        await self._create_stock_movement(
            movement_type=StockMovementType.RECEIPT,
            warehouse_id=data["warehouse_id"],
            product_id=data["product_id"],
            variant_id=data.get("variant_id"),
            stock_item_id=stock_item.id,
            quantity=1,
            unit_cost=data.get("purchase_price", 0),
            reference_type="manual_receipt",
            created_by=created_by,
        )

        await self.db.commit()
        await self.db.refresh(stock_item)
        return stock_item

    async def bulk_receive_stock(
        self,
        warehouse_id: uuid.UUID,
        grn_number: str,
        items: List[dict],
        purchase_order_id: Optional[uuid.UUID] = None,
        vendor_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID = None,
    ) -> List[StockItem]:
        """Bulk receive stock items (GRN)."""
        created_items = []

        for item_data in items:
            product_id = item_data["product_id"]
            variant_id = item_data.get("variant_id")
            quantity = item_data["quantity"]
            serial_numbers = item_data.get("serial_numbers", [])

            # If serial numbers provided, create individual items
            if serial_numbers:
                for serial in serial_numbers:
                    stock_item = StockItem(
                        product_id=product_id,
                        variant_id=variant_id,
                        warehouse_id=warehouse_id,
                        serial_number=serial,
                        batch_number=item_data.get("batch_number"),
                        grn_number=grn_number,
                        purchase_order_id=purchase_order_id,
                        vendor_id=vendor_id,
                        purchase_price=item_data.get("purchase_price", 0),
                        manufacturing_date=item_data.get("manufacturing_date"),
                        expiry_date=item_data.get("expiry_date"),
                        status=StockItemStatus.AVAILABLE,
                    )
                    self.db.add(stock_item)
                    created_items.append(stock_item)
            else:
                # Create non-serialized items
                for _ in range(quantity):
                    stock_item = StockItem(
                        product_id=product_id,
                        variant_id=variant_id,
                        warehouse_id=warehouse_id,
                        batch_number=item_data.get("batch_number"),
                        grn_number=grn_number,
                        purchase_order_id=purchase_order_id,
                        vendor_id=vendor_id,
                        purchase_price=item_data.get("purchase_price", 0),
                        manufacturing_date=item_data.get("manufacturing_date"),
                        expiry_date=item_data.get("expiry_date"),
                        status=StockItemStatus.AVAILABLE,
                    )
                    self.db.add(stock_item)
                    created_items.append(stock_item)

            # Update inventory summary
            await self._update_inventory_summary(
                warehouse_id, product_id, variant_id, quantity_change=quantity
            )

            # Create stock movement
            await self._create_stock_movement(
                movement_type=StockMovementType.RECEIPT,
                warehouse_id=warehouse_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
                unit_cost=item_data.get("purchase_price", 0),
                reference_type="grn",
                reference_number=grn_number,
                created_by=created_by,
            )

        await self.db.commit()
        return created_items

    async def allocate_stock_for_order(
        self,
        order_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID],
        quantity: int,
    ) -> List[StockItem]:
        """Allocate available stock items for an order."""
        # Get available items (FIFO)
        query = select(StockItem).where(
            and_(
                StockItem.warehouse_id == warehouse_id,
                StockItem.product_id == product_id,
                StockItem.status == StockItemStatus.AVAILABLE,
            )
        ).order_by(StockItem.received_date).limit(quantity)

        if variant_id:
            query = query.where(StockItem.variant_id == variant_id)

        result = await self.db.execute(query)
        items = result.scalars().all()

        if len(items) < quantity:
            raise ValueError(f"Insufficient stock. Available: {len(items)}, Requested: {quantity}")

        # Allocate items
        for item in items:
            item.status = StockItemStatus.ALLOCATED.value
            item.order_id = order_id
            item.allocated_at = datetime.now(timezone.utc)

        # Update inventory summary
        await self._update_inventory_summary(
            warehouse_id, product_id, variant_id,
            available_change=-quantity, allocated_change=quantity
        )

        await self.db.commit()
        return items

    # ==================== INVENTORY SUMMARY METHODS ====================

    async def get_inventory_summary(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[InventorySummary], int]:
        """Get inventory summary."""
        query = select(InventorySummary).options(
            joinedload(InventorySummary.product),
            joinedload(InventorySummary.warehouse),
        )

        conditions = []
        if warehouse_id:
            conditions.append(InventorySummary.warehouse_id == warehouse_id)
        if product_id:
            conditions.append(InventorySummary.product_id == product_id)
        if low_stock_only:
            conditions.append(InventorySummary.available_quantity <= InventorySummary.reorder_level)
        if out_of_stock_only:
            conditions.append(InventorySummary.available_quantity == 0)

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(InventorySummary.available_quantity).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().unique().all(), total

    async def _update_inventory_summary(
        self,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID],
        quantity_change: int = 0,
        available_change: int = 0,
        reserved_change: int = 0,
        allocated_change: int = 0,
        damaged_change: int = 0,
        in_transit_change: int = 0,
    ):
        """Update or create inventory summary."""
        # Try to get existing summary
        query = select(InventorySummary).where(
            and_(
                InventorySummary.warehouse_id == warehouse_id,
                InventorySummary.product_id == product_id,
            )
        )
        if variant_id:
            query = query.where(InventorySummary.variant_id == variant_id)
        else:
            query = query.where(InventorySummary.variant_id.is_(None))

        result = await self.db.execute(query)
        summary = result.scalar_one_or_none()

        if summary:
            # Update existing
            summary.total_quantity += quantity_change
            if quantity_change > 0:
                summary.available_quantity += quantity_change
            summary.available_quantity += available_change
            summary.reserved_quantity += reserved_change
            summary.allocated_quantity += allocated_change
            summary.damaged_quantity += damaged_change
            summary.in_transit_quantity += in_transit_change

            if quantity_change > 0:
                summary.last_stock_in_date = datetime.now(timezone.utc)
            elif quantity_change < 0:
                summary.last_stock_out_date = datetime.now(timezone.utc)
        else:
            # Create new
            summary = InventorySummary(
                warehouse_id=warehouse_id,
                product_id=product_id,
                variant_id=variant_id,
                total_quantity=max(0, quantity_change),
                available_quantity=max(0, quantity_change + available_change),
                reserved_quantity=max(0, reserved_change),
                allocated_quantity=max(0, allocated_change),
                damaged_quantity=max(0, damaged_change),
                in_transit_quantity=max(0, in_transit_change),
            )
            if quantity_change > 0:
                summary.last_stock_in_date = datetime.now(timezone.utc)
            self.db.add(summary)

    # ==================== STOCK MOVEMENT METHODS ====================

    async def get_stock_movements(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        movement_type: Optional[StockMovementType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockMovement], int]:
        """Get stock movement history."""
        query = select(StockMovement).options(
            joinedload(StockMovement.product),
            joinedload(StockMovement.warehouse),
        )

        conditions = []
        if warehouse_id:
            conditions.append(StockMovement.warehouse_id == warehouse_id)
        if product_id:
            conditions.append(StockMovement.product_id == product_id)
        if movement_type:
            conditions.append(StockMovement.movement_type == movement_type)
        if date_from:
            conditions.append(StockMovement.movement_date >= date_from)
        if date_to:
            conditions.append(StockMovement.movement_date <= date_to)

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(StockMovement.movement_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().unique().all(), total

    async def _create_stock_movement(
        self,
        movement_type: StockMovementType,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        variant_id: Optional[uuid.UUID] = None,
        stock_item_id: Optional[uuid.UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        reference_number: Optional[str] = None,
        unit_cost: float = 0,
        notes: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> StockMovement:
        """Create a stock movement record."""
        # Generate movement number
        movement_number = await self._generate_movement_number()

        # Get current balance
        summary_query = select(InventorySummary.total_quantity).where(
            and_(
                InventorySummary.warehouse_id == warehouse_id,
                InventorySummary.product_id == product_id,
            )
        )
        result = await self.db.scalar(summary_query)
        balance_before = result or 0

        # Calculate balance after
        if movement_type in [
            StockMovementType.RECEIPT,
            StockMovementType.TRANSFER_IN,
            StockMovementType.RETURN_IN,
            StockMovementType.ADJUSTMENT_PLUS,
            StockMovementType.FOUND,
        ]:
            balance_after = balance_before + quantity
        else:
            balance_after = balance_before - abs(quantity)
            quantity = -abs(quantity)  # Make negative for outgoing

        movement = StockMovement(
            movement_number=movement_number,
            movement_type=movement_type,
            warehouse_id=warehouse_id,
            product_id=product_id,
            variant_id=variant_id,
            stock_item_id=stock_item_id,
            quantity=quantity,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_number=reference_number,
            unit_cost=unit_cost,
            total_cost=abs(quantity) * unit_cost,
            created_by=created_by,
            notes=notes,
        )
        self.db.add(movement)
        return movement

    async def _generate_movement_number(self) -> str:
        """Generate unique movement number."""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        query = select(func.count()).select_from(StockMovement).where(
            StockMovement.movement_number.like(f"MOV-{date_part}%")
        )
        count = await self.db.scalar(query)
        return f"MOV-{date_part}-{(count or 0) + 1:04d}"

    # ==================== STATISTICS ====================

    async def get_inventory_stats(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Get inventory statistics for Stock Items page.

        Returns stats with field names matching frontend expectations:
        - total_skus: Unique products with inventory records
        - in_stock: Products with available_quantity > 0
        - low_stock: Products below reorder level
        - out_of_stock: Products with zero available quantity
        """
        # Total SKUs (unique products in inventory)
        total_skus_query = select(func.count(func.distinct(InventorySummary.product_id)))
        if warehouse_id:
            total_skus_query = total_skus_query.where(InventorySummary.warehouse_id == warehouse_id)
        total_skus = await self.db.scalar(total_skus_query) or 0

        # In stock count - products with available_quantity > 0
        in_stock_query = select(func.count()).select_from(InventorySummary).where(
            InventorySummary.available_quantity > 0
        )
        if warehouse_id:
            in_stock_query = in_stock_query.where(InventorySummary.warehouse_id == warehouse_id)
        in_stock = await self.db.scalar(in_stock_query) or 0

        # Total value
        value_query = select(func.sum(InventorySummary.total_value))
        if warehouse_id:
            value_query = value_query.where(InventorySummary.warehouse_id == warehouse_id)
        total_value = await self.db.scalar(value_query) or 0

        # Low stock count - products below reorder level but not zero
        low_stock_query = select(func.count()).select_from(InventorySummary).where(
            and_(
                InventorySummary.available_quantity <= func.coalesce(InventorySummary.reorder_level, 10),
                InventorySummary.available_quantity > 0,
            )
        )
        if warehouse_id:
            low_stock_query = low_stock_query.where(InventorySummary.warehouse_id == warehouse_id)
        low_stock = await self.db.scalar(low_stock_query) or 0

        # Out of stock count - products with zero available quantity
        out_of_stock_query = select(func.count()).select_from(InventorySummary).where(
            InventorySummary.available_quantity == 0
        )
        if warehouse_id:
            out_of_stock_query = out_of_stock_query.where(InventorySummary.warehouse_id == warehouse_id)
        out_of_stock = await self.db.scalar(out_of_stock_query) or 0

        # Warehouses count
        warehouses_query = select(func.count()).select_from(Warehouse).where(Warehouse.is_active == True)
        warehouses_count = await self.db.scalar(warehouses_query) or 0

        # Pending transfers
        transfers_query = select(func.count()).select_from(StockTransfer).where(
            StockTransfer.status.in_([TransferStatus.PENDING_APPROVAL, TransferStatus.APPROVED, TransferStatus.IN_TRANSIT])
        )
        pending_transfers = await self.db.scalar(transfers_query) or 0

        # Pending adjustments
        adjustments_query = select(func.count()).select_from(StockAdjustment).where(
            StockAdjustment.status == AdjustmentStatus.PENDING_APPROVAL
        )
        pending_adjustments = await self.db.scalar(adjustments_query) or 0

        # Return with frontend-expected field names
        return {
            "total_skus": total_skus,
            "in_stock": in_stock,
            "total_stock_value": float(total_value),
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "warehouses_count": warehouses_count,
            "pending_transfers": pending_transfers,
            "pending_adjustments": pending_adjustments,
        }

    async def get_dashboard_stats(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Get inventory statistics for Dashboard Summary page.

        Returns stats for the main inventory dashboard:
        - total_items: Total inventory records
        - total_warehouses: Active warehouse count
        - pending_transfers: Transfers in progress
        - low_stock_items: Items below reorder level
        """
        # Total items in inventory_summary
        total_items_query = select(func.count()).select_from(InventorySummary)
        if warehouse_id:
            total_items_query = total_items_query.where(InventorySummary.warehouse_id == warehouse_id)
        total_items = await self.db.scalar(total_items_query) or 0

        # Total active warehouses
        warehouses_query = select(func.count()).select_from(Warehouse).where(Warehouse.is_active == True)
        total_warehouses = await self.db.scalar(warehouses_query) or 0

        # Pending transfers
        transfers_query = select(func.count()).select_from(StockTransfer).where(
            StockTransfer.status.in_([TransferStatus.PENDING_APPROVAL, TransferStatus.APPROVED, TransferStatus.IN_TRANSIT])
        )
        pending_transfers = await self.db.scalar(transfers_query) or 0

        # Low stock items
        low_stock_query = select(func.count()).select_from(InventorySummary).where(
            and_(
                InventorySummary.available_quantity <= func.coalesce(InventorySummary.reorder_level, 10),
                InventorySummary.available_quantity > 0,
            )
        )
        if warehouse_id:
            low_stock_query = low_stock_query.where(InventorySummary.warehouse_id == warehouse_id)
        low_stock_items = await self.db.scalar(low_stock_query) or 0

        # Total value
        value_query = select(func.sum(InventorySummary.total_value))
        if warehouse_id:
            value_query = value_query.where(InventorySummary.warehouse_id == warehouse_id)
        total_value = await self.db.scalar(value_query) or 0

        return {
            "total_items": total_items,
            "total_warehouses": total_warehouses,
            "pending_transfers": pending_transfers,
            "low_stock_items": low_stock_items,
            "total_value": float(total_value),
        }
