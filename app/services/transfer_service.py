"""Stock Transfer Service for warehouse-to-warehouse movements."""
from typing import Optional, List, Tuple
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.stock_transfer import (
    StockTransfer, StockTransferItem, StockTransferSerial,
    TransferStatus, TransferType,
)
from app.models.warehouse import Warehouse
from app.models.inventory import StockItem, StockItemStatus, StockMovementType
from app.services.inventory_service import InventoryService


class TransferService:
    """Service for stock transfer operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_service = InventoryService(db)

    async def get_transfers(
        self,
        from_warehouse_id: Optional[uuid.UUID] = None,
        to_warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[TransferStatus] = None,
        transfer_type: Optional[TransferType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[StockTransfer], int]:
        """Get paginated list of stock transfers."""
        query = select(StockTransfer).options(
            joinedload(StockTransfer.from_warehouse),
            joinedload(StockTransfer.to_warehouse),
        )

        conditions = []
        if from_warehouse_id:
            conditions.append(StockTransfer.from_warehouse_id == from_warehouse_id)
        if to_warehouse_id:
            conditions.append(StockTransfer.to_warehouse_id == to_warehouse_id)
        if status:
            conditions.append(StockTransfer.status == status)
        if transfer_type:
            conditions.append(StockTransfer.transfer_type == transfer_type)
        if date_from:
            conditions.append(StockTransfer.request_date >= date_from)
        if date_to:
            conditions.append(StockTransfer.request_date <= date_to)

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(StockTransfer.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().unique().all(), total

    async def get_transfer_by_id(
        self,
        transfer_id: uuid.UUID,
        include_items: bool = False,
    ) -> Optional[StockTransfer]:
        """Get transfer by ID."""
        query = select(StockTransfer).options(
            joinedload(StockTransfer.from_warehouse),
            joinedload(StockTransfer.to_warehouse),
        )

        if include_items:
            query = query.options(
                selectinload(StockTransfer.items).joinedload(StockTransferItem.product),
            )

        query = query.where(StockTransfer.id == transfer_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_transfer_by_number(self, transfer_number: str) -> Optional[StockTransfer]:
        """Get transfer by number."""
        query = select(StockTransfer).options(
            joinedload(StockTransfer.from_warehouse),
            joinedload(StockTransfer.to_warehouse),
            selectinload(StockTransfer.items),
        ).where(StockTransfer.transfer_number == transfer_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_transfer(
        self,
        from_warehouse_id: uuid.UUID,
        to_warehouse_id: uuid.UUID,
        items: List[dict],
        transfer_type: TransferType = TransferType.STOCK_TRANSFER,
        expected_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        requested_by: uuid.UUID = None,
    ) -> StockTransfer:
        """Create a new stock transfer request."""
        # Validate warehouses
        if from_warehouse_id == to_warehouse_id:
            raise ValueError("Source and destination warehouses cannot be the same")

        from_wh = await self.db.get(Warehouse, from_warehouse_id)
        to_wh = await self.db.get(Warehouse, to_warehouse_id)

        if not from_wh or not from_wh.is_active:
            raise ValueError("Invalid source warehouse")
        if not to_wh or not to_wh.is_active:
            raise ValueError("Invalid destination warehouse")

        # Generate transfer number
        transfer_number = await self._generate_transfer_number()

        # Calculate totals
        total_quantity = sum(item["requested_quantity"] for item in items)

        transfer = StockTransfer(
            transfer_number=transfer_number,
            transfer_type=transfer_type,
            status=TransferStatus.DRAFT,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            expected_date=expected_date,
            requested_by=requested_by,
            total_items=len(items),
            total_quantity=total_quantity,
            notes=notes,
        )
        self.db.add(transfer)
        await self.db.flush()

        # Add items
        for item_data in items:
            transfer_item = StockTransferItem(
                transfer_id=transfer.id,
                product_id=item_data["product_id"],
                variant_id=item_data.get("variant_id"),
                requested_quantity=item_data["requested_quantity"],
                notes=item_data.get("notes"),
            )
            self.db.add(transfer_item)

        await self.db.commit()
        await self.db.refresh(transfer)
        return transfer

    async def submit_for_approval(
        self,
        transfer_id: uuid.UUID,
    ) -> StockTransfer:
        """Submit transfer for approval."""
        transfer = await self.get_transfer_by_id(transfer_id)
        if not transfer:
            raise ValueError("Transfer not found")

        if transfer.status != TransferStatus.DRAFT:
            raise ValueError("Only draft transfers can be submitted")

        transfer.status = TransferStatus.PENDING_APPROVAL.value
        await self.db.commit()
        await self.db.refresh(transfer)
        return transfer

    async def approve_transfer(
        self,
        transfer_id: uuid.UUID,
        approved_by: uuid.UUID,
        item_approvals: Optional[List[dict]] = None,
        notes: Optional[str] = None,
    ) -> StockTransfer:
        """Approve a transfer request."""
        transfer = await self.get_transfer_by_id(transfer_id, include_items=True)
        if not transfer:
            raise ValueError("Transfer not found")

        if transfer.status != TransferStatus.PENDING_APPROVAL:
            raise ValueError("Transfer is not pending approval")

        # Update item quantities if specified
        if item_approvals:
            for approval in item_approvals:
                for item in transfer.items:
                    if str(item.id) == str(approval["item_id"]):
                        item.approved_quantity = approval.get("approved_quantity", item.requested_quantity)
                        break
        else:
            # Approve all requested quantities
            for item in transfer.items:
                item.approved_quantity = item.requested_quantity

        transfer.status = TransferStatus.APPROVED.value
        transfer.approved_by = approved_by
        transfer.approved_at = datetime.now(timezone.utc)
        if notes:
            transfer.internal_notes = notes

        await self.db.commit()
        await self.db.refresh(transfer)
        return transfer

    async def reject_transfer(
        self,
        transfer_id: uuid.UUID,
        rejected_by: uuid.UUID,
        reason: str,
    ) -> StockTransfer:
        """Reject a transfer request."""
        transfer = await self.get_transfer_by_id(transfer_id)
        if not transfer:
            raise ValueError("Transfer not found")

        if transfer.status != TransferStatus.PENDING_APPROVAL:
            raise ValueError("Transfer is not pending approval")

        transfer.status = TransferStatus.REJECTED.value
        transfer.approved_by = rejected_by
        transfer.approved_at = datetime.now(timezone.utc)
        transfer.rejection_reason = reason

        await self.db.commit()
        await self.db.refresh(transfer)
        return transfer

    async def dispatch_transfer(
        self,
        transfer_id: uuid.UUID,
        dispatched_by: uuid.UUID,
        vehicle_number: Optional[str] = None,
        driver_name: Optional[str] = None,
        driver_phone: Optional[str] = None,
        challan_number: Optional[str] = None,
        eway_bill_number: Optional[str] = None,
        serial_items: Optional[List[uuid.UUID]] = None,
        notes: Optional[str] = None,
    ) -> StockTransfer:
        """Dispatch approved transfer."""
        transfer = await self.get_transfer_by_id(transfer_id, include_items=True)
        if not transfer:
            raise ValueError("Transfer not found")

        if transfer.status != TransferStatus.APPROVED:
            raise ValueError("Only approved transfers can be dispatched")

        # Update stock items status to IN_TRANSIT
        for item in transfer.items:
            # Get available stock items
            query = select(StockItem).where(
                and_(
                    StockItem.warehouse_id == transfer.from_warehouse_id,
                    StockItem.product_id == item.product_id,
                    StockItem.status == StockItemStatus.AVAILABLE,
                )
            ).limit(item.approved_quantity or item.requested_quantity)

            if item.variant_id:
                query = query.where(StockItem.variant_id == item.variant_id)

            result = await self.db.execute(query)
            stock_items = result.scalars().all()

            dispatched_qty = len(stock_items)
            item.dispatched_quantity = dispatched_qty

            # Update stock items
            for stock_item in stock_items:
                stock_item.status = StockItemStatus.IN_TRANSIT.value
                stock_item.last_movement_date = datetime.now(timezone.utc)

                # Create serial tracking
                serial_record = StockTransferSerial(
                    transfer_item_id=item.id,
                    stock_item_id=stock_item.id,
                    is_dispatched=True,
                )
                self.db.add(serial_record)

            # Update inventory summary at source
            await self.inventory_service._update_inventory_summary(
                transfer.from_warehouse_id,
                item.product_id,
                item.variant_id,
                available_change=-dispatched_qty,
                in_transit_change=dispatched_qty,
            )

            # Create movement record
            await self.inventory_service._create_stock_movement(
                movement_type=StockMovementType.TRANSFER_OUT,
                warehouse_id=transfer.from_warehouse_id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=dispatched_qty,
                reference_type="transfer",
                reference_id=transfer.id,
                reference_number=transfer.transfer_number,
                created_by=dispatched_by,
            )

        # Update transfer
        transfer.status = TransferStatus.IN_TRANSIT.value
        transfer.dispatch_date = datetime.now(timezone.utc)
        transfer.dispatched_by = dispatched_by
        transfer.vehicle_number = vehicle_number
        transfer.driver_name = driver_name
        transfer.driver_phone = driver_phone
        transfer.challan_number = challan_number
        transfer.eway_bill_number = eway_bill_number

        if notes:
            transfer.notes = (transfer.notes or "") + f"\nDispatch: {notes}"

        await self.db.commit()
        await self.db.refresh(transfer)
        return transfer

    async def receive_transfer(
        self,
        transfer_id: uuid.UUID,
        received_by: uuid.UUID,
        item_receipts: List[dict],
        notes: Optional[str] = None,
    ) -> StockTransfer:
        """Receive a dispatched transfer."""
        transfer = await self.get_transfer_by_id(transfer_id, include_items=True)
        if not transfer:
            raise ValueError("Transfer not found")

        if transfer.status not in [TransferStatus.IN_TRANSIT, TransferStatus.PARTIALLY_RECEIVED]:
            raise ValueError("Transfer is not in transit")

        total_received = 0
        total_dispatched = 0

        for receipt in item_receipts:
            item_id = receipt["item_id"]
            received_qty = receipt["received_quantity"]
            damaged_qty = receipt.get("damaged_quantity", 0)

            # Find the transfer item
            for item in transfer.items:
                if str(item.id) == str(item_id):
                    item.received_quantity += received_qty
                    item.damaged_quantity += damaged_qty
                    total_received += received_qty
                    total_dispatched += item.dispatched_quantity or 0

                    # Get serial records and update stock items
                    serial_query = select(StockTransferSerial).where(
                        and_(
                            StockTransferSerial.transfer_item_id == item.id,
                            StockTransferSerial.is_received == False,
                        )
                    ).limit(received_qty + damaged_qty)
                    serial_result = await self.db.execute(serial_query)
                    serials = serial_result.scalars().all()

                    for i, serial in enumerate(serials):
                        serial.is_received = True
                        serial.received_at = datetime.now(timezone.utc)

                        # Update the stock item
                        stock_item = await self.db.get(StockItem, serial.stock_item_id)
                        if stock_item:
                            stock_item.warehouse_id = transfer.to_warehouse_id
                            stock_item.last_movement_date = datetime.now(timezone.utc)

                            if i < damaged_qty:
                                serial.is_damaged = True
                                serial.damage_notes = receipt.get("damage_notes")
                                stock_item.status = StockItemStatus.DAMAGED.value
                            else:
                                stock_item.status = StockItemStatus.AVAILABLE.value

                    # Update inventory at destination
                    await self.inventory_service._update_inventory_summary(
                        transfer.to_warehouse_id,
                        item.product_id,
                        item.variant_id,
                        quantity_change=received_qty,
                        damaged_change=damaged_qty,
                    )

                    # Update source warehouse (reduce in_transit)
                    await self.inventory_service._update_inventory_summary(
                        transfer.from_warehouse_id,
                        item.product_id,
                        item.variant_id,
                        in_transit_change=-(received_qty + damaged_qty),
                    )

                    # Create movement record at destination
                    await self.inventory_service._create_stock_movement(
                        movement_type=StockMovementType.TRANSFER_IN,
                        warehouse_id=transfer.to_warehouse_id,
                        product_id=item.product_id,
                        variant_id=item.variant_id,
                        quantity=received_qty,
                        reference_type="transfer",
                        reference_id=transfer.id,
                        reference_number=transfer.transfer_number,
                        created_by=received_by,
                    )
                    break

        # Update transfer status
        transfer.received_quantity = sum(item.received_quantity for item in transfer.items)
        transfer.received_by = received_by

        if notes:
            transfer.notes = (transfer.notes or "") + f"\nReceipt: {notes}"

        # Check if fully received
        all_received = all(
            (item.received_quantity + item.damaged_quantity) >= (item.dispatched_quantity or 0)
            for item in transfer.items
        )

        if all_received:
            transfer.status = TransferStatus.RECEIVED.value
            transfer.received_date = datetime.now(timezone.utc)
        else:
            transfer.status = TransferStatus.PARTIALLY_RECEIVED.value

        await self.db.commit()
        await self.db.refresh(transfer)

        # Auto-post GL entry for stock transfer
        if all_received:
            try:
                from decimal import Decimal
                from app.services.costing_service import CostingService
                from app.services.auto_journal_service import AutoJournalService

                costing = CostingService(self.db)
                total_value = Decimal("0")
                for item in transfer.items:
                    item_cost = await costing.get_cost_for_product(
                        product_id=item.product_id,
                        quantity=item.received_quantity,
                    )
                    total_value += item_cost

                if total_value > 0:
                    journal_svc = AutoJournalService(self.db)
                    await journal_svc.generate_for_stock_transfer(
                        transfer_id=transfer.id,
                        transfer_number=transfer.transfer_number,
                        total_value=total_value,
                        from_warehouse_name=str(transfer.from_warehouse_id),
                        to_warehouse_name=str(transfer.to_warehouse_id),
                        user_id=received_by,
                        auto_post=True,
                    )
                    await self.db.commit()
            except Exception as e:
                import logging
                logging.warning(
                    f"GL posting failed for transfer {transfer.transfer_number}: {e}"
                )

        return transfer

    async def cancel_transfer(
        self,
        transfer_id: uuid.UUID,
        cancelled_by: uuid.UUID,
        reason: str,
    ) -> StockTransfer:
        """Cancel a transfer."""
        transfer = await self.get_transfer_by_id(transfer_id)
        if not transfer:
            raise ValueError("Transfer not found")

        if transfer.status in [TransferStatus.IN_TRANSIT, TransferStatus.RECEIVED, TransferStatus.PARTIALLY_RECEIVED]:
            raise ValueError("Cannot cancel a transfer that is in transit or already received")

        transfer.status = TransferStatus.CANCELLED.value
        transfer.rejection_reason = reason
        transfer.approved_by = cancelled_by
        transfer.approved_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(transfer)
        return transfer

    async def _generate_transfer_number(self) -> str:
        """Generate unique transfer number."""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        query = select(func.count()).select_from(StockTransfer).where(
            StockTransfer.transfer_number.like(f"TRF-{date_part}%")
        )
        count = await self.db.scalar(query)
        return f"TRF-{date_part}-{(count or 0) + 1:04d}"
