"""GRN Service for serial validation and stock item creation.

This service handles the critical link between:
- PO Serials (generated at PO approval)
- GRN (goods receipt)
- Stock Items (individual serialized inventory)
- Inventory Summary (aggregate inventory)

Flow:
1. PO Created → Serials generated in po_serials
2. GRN Created → Serials scanned/entered
3. Serial Validation → Match against po_serials
4. GRN Accepted → Create stock_items, update inventory_summary
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase import GoodsReceiptNote, GRNItem, PurchaseOrder, PurchaseOrderItem
from app.models.serialization import POSerial, SerialStatus
from app.models.inventory import StockItem, StockItemStatus, InventorySummary, StockMovement, StockMovementType
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.user import User


class GRNService:
    """Service for GRN operations with serial validation and stock management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== SERIAL VALIDATION ====================

    async def validate_serials_for_grn(
        self,
        po_id: uuid.UUID,
        product_id: uuid.UUID,
        scanned_serials: List[str],
    ) -> Dict[str, Any]:
        """
        Validate scanned serial numbers against PO serials.

        Args:
            po_id: Purchase Order ID
            product_id: Product ID
            scanned_serials: List of serial numbers scanned during GRN

        Returns:
            {
                "is_valid": bool,
                "matched": ["serial1", "serial2"],
                "not_in_po": ["serial3"],  # Scanned but not in PO
                "missing_from_scan": ["serial4"],  # In PO but not scanned
                "already_received": ["serial5"],  # Already received in another GRN
                "wrong_product": ["serial6"],  # Serial belongs to different product
            }
        """
        result = {
            "is_valid": True,
            "matched": [],
            "not_in_po": [],
            "missing_from_scan": [],
            "already_received": [],
            "wrong_product": [],
            "total_expected": 0,
            "total_scanned": len(scanned_serials),
        }

        # Get all PO serials for this PO and product that are ready to receive
        po_serials_query = select(POSerial).where(
            and_(
                POSerial.po_id == po_id,
                POSerial.product_id == product_id,
                POSerial.status.in_(["GENERATED", "PRINTED", "SENT_TO_VENDOR"]),
            )
        )
        po_serials_result = await self.db.execute(po_serials_query)
        po_serials = po_serials_result.scalars().all()

        # Build lookup sets
        po_serial_barcodes = {s.barcode for s in po_serials}
        scanned_set = set(scanned_serials)

        result["total_expected"] = len(po_serial_barcodes)

        # Check for already received serials (same barcode, status RECEIVED/ASSIGNED)
        already_received_query = select(POSerial.barcode).where(
            and_(
                POSerial.barcode.in_(scanned_serials),
                POSerial.status.in_(["RECEIVED", "ASSIGNED", "SOLD"]),
            )
        )
        already_received_result = await self.db.execute(already_received_query)
        already_received = {row[0] for row in already_received_result.all()}

        # Check for serials belonging to different products
        wrong_product_query = select(POSerial.barcode).where(
            and_(
                POSerial.barcode.in_(scanned_serials),
                POSerial.product_id != product_id,
            )
        )
        wrong_product_result = await self.db.execute(wrong_product_query)
        wrong_product = {row[0] for row in wrong_product_result.all()}

        # Calculate matches and mismatches
        result["matched"] = list(scanned_set & po_serial_barcodes - already_received - wrong_product)
        result["not_in_po"] = list(scanned_set - po_serial_barcodes - already_received - wrong_product)
        result["missing_from_scan"] = list(po_serial_barcodes - scanned_set)
        result["already_received"] = list(already_received & scanned_set)
        result["wrong_product"] = list(wrong_product & scanned_set)

        # Determine validity
        if result["not_in_po"] or result["already_received"] or result["wrong_product"]:
            result["is_valid"] = False

        return result

    async def validate_grn_serials(
        self,
        grn_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Validate all serials in a GRN against PO serials.

        Args:
            grn_id: GRN ID

        Returns:
            Overall validation result with per-item breakdown
        """
        # Get GRN with items
        grn_query = select(GoodsReceiptNote).options(
            selectinload(GoodsReceiptNote.items)
        ).where(GoodsReceiptNote.id == grn_id)
        grn_result = await self.db.execute(grn_query)
        grn = grn_result.scalar_one_or_none()

        if not grn:
            raise ValueError(f"GRN {grn_id} not found")

        overall_result = {
            "grn_id": str(grn_id),
            "grn_number": grn.grn_number,
            "is_valid": True,
            "items": [],
            "total_matched": 0,
            "total_not_in_po": 0,
            "total_already_received": 0,
            "requires_force": False,
        }

        for item in grn.items:
            if not item.serial_numbers:
                # No serials provided for this item
                overall_result["items"].append({
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "serial_validation": "NO_SERIALS",
                    "quantity_received": item.quantity_received,
                })
                continue

            validation = await self.validate_serials_for_grn(
                po_id=grn.purchase_order_id,
                product_id=item.product_id,
                scanned_serials=item.serial_numbers,
            )

            overall_result["items"].append({
                "product_id": str(item.product_id),
                "product_name": item.product_name,
                "sku": item.sku,
                "serial_validation": validation,
            })

            overall_result["total_matched"] += len(validation["matched"])
            overall_result["total_not_in_po"] += len(validation["not_in_po"])
            overall_result["total_already_received"] += len(validation["already_received"])

            if not validation["is_valid"]:
                overall_result["is_valid"] = False
                overall_result["requires_force"] = True

        return overall_result

    # ==================== STOCK ITEM CREATION ====================

    async def create_stock_items_from_grn(
        self,
        grn_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Create stock_items from GRN items and update po_serials.

        This is the critical function that:
        1. Creates individual stock_items for each serial
        2. Updates po_serials status to RECEIVED and links to stock_item
        3. Updates inventory_summary (aggregate counts)
        4. Creates stock_movements for audit trail

        Args:
            grn_id: GRN ID (must be in ACCEPTED status)
            user_id: User performing the operation

        Returns:
            Summary of created stock items
        """
        # Get GRN with items
        grn_query = select(GoodsReceiptNote).options(
            selectinload(GoodsReceiptNote.items),
            selectinload(GoodsReceiptNote.purchase_order),
        ).where(GoodsReceiptNote.id == grn_id)
        grn_result = await self.db.execute(grn_query)
        grn = grn_result.scalar_one_or_none()

        if not grn:
            raise ValueError(f"GRN {grn_id} not found")

        if grn.status not in ["ACCEPTED", "QC_PASSED", "PARTIALLY_ACCEPTED"]:
            raise ValueError(f"GRN must be in ACCEPTED status. Current: {grn.status}")

        if grn.stock_items_created:
            raise ValueError(f"Stock items already created for GRN {grn.grn_number}")

        result = {
            "grn_id": str(grn_id),
            "grn_number": grn.grn_number,
            "items_created": 0,
            "items_by_product": [],
            "inventory_updated": [],
        }

        now = datetime.now(timezone.utc)

        for grn_item in grn.items:
            if grn_item.quantity_accepted <= 0:
                continue

            product_items_created = 0

            # Get product for item_type
            product = await self.db.get(Product, grn_item.product_id)
            if not product:
                continue

            # If serials are provided, create stock_items from serials
            if grn_item.serial_numbers:
                for barcode in grn_item.serial_numbers[:grn_item.quantity_accepted]:
                    # Get the PO serial
                    po_serial_query = select(POSerial).where(
                        and_(
                            POSerial.barcode == barcode,
                            POSerial.po_id == grn.purchase_order_id,
                        )
                    )
                    po_serial_result = await self.db.execute(po_serial_query)
                    po_serial = po_serial_result.scalar_one_or_none()

                    # Create stock item
                    stock_item = StockItem(
                        product_id=grn_item.product_id,
                        variant_id=grn_item.variant_id,
                        warehouse_id=grn.warehouse_id,
                        serial_number=barcode,
                        batch_number=grn_item.batch_number,
                        barcode=barcode,
                        status="AVAILABLE",
                        purchase_order_id=grn.purchase_order_id,
                        grn_number=grn.grn_number,
                        vendor_id=grn.vendor_id,
                        purchase_price=grn_item.unit_price,
                        landed_cost=grn_item.unit_price,  # Can be updated later
                        manufacturing_date=grn_item.manufacturing_date,
                        expiry_date=grn_item.expiry_date,
                        received_date=now,
                        bin_id=grn_item.bin_id,
                        rack_location=grn_item.bin_location,
                    )

                    # Set warranty dates if product has warranty
                    if product.warranty_months:
                        from dateutil.relativedelta import relativedelta
                        stock_item.warranty_start_date = now.date()
                        stock_item.warranty_end_date = (now + relativedelta(months=product.warranty_months)).date()

                    self.db.add(stock_item)
                    await self.db.flush()  # Get the stock_item.id

                    # Update PO serial
                    if po_serial:
                        po_serial.status = "RECEIVED"
                        po_serial.grn_id = grn.id
                        po_serial.grn_item_id = grn_item.id
                        po_serial.received_at = now
                        po_serial.received_by = user_id
                        po_serial.stock_item_id = stock_item.id
                        po_serial.assigned_at = now

                    product_items_created += 1

            else:
                # No serials - create stock items without serial numbers (for spare parts without serial tracking)
                # This handles cases where serials were not provided or forced GRN
                for i in range(grn_item.quantity_accepted):
                    stock_item = StockItem(
                        product_id=grn_item.product_id,
                        variant_id=grn_item.variant_id,
                        warehouse_id=grn.warehouse_id,
                        batch_number=grn_item.batch_number,
                        status="AVAILABLE",
                        purchase_order_id=grn.purchase_order_id,
                        grn_number=grn.grn_number,
                        vendor_id=grn.vendor_id,
                        purchase_price=grn_item.unit_price,
                        landed_cost=grn_item.unit_price,
                        manufacturing_date=grn_item.manufacturing_date,
                        expiry_date=grn_item.expiry_date,
                        received_date=now,
                        bin_id=grn_item.bin_id,
                        rack_location=grn_item.bin_location,
                    )
                    self.db.add(stock_item)
                    product_items_created += 1

            result["items_by_product"].append({
                "product_id": str(grn_item.product_id),
                "product_name": grn_item.product_name,
                "sku": grn_item.sku,
                "items_created": product_items_created,
            })
            result["items_created"] += product_items_created

            # Update inventory summary
            inv_update = await self._update_inventory_summary(
                warehouse_id=grn.warehouse_id,
                product_id=grn_item.product_id,
                variant_id=grn_item.variant_id,
                quantity_change=grn_item.quantity_accepted,
                unit_cost=float(grn_item.unit_price),
                movement_type="RECEIPT",
                reference_type="GRN",
                reference_id=grn.id,
                reference_number=grn.grn_number,
                user_id=user_id,
            )
            result["inventory_updated"].append(inv_update)

        # Mark GRN as having stock items created
        grn.stock_items_created = True
        await self.db.commit()

        return result

    async def _update_inventory_summary(
        self,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID],
        quantity_change: int,
        unit_cost: float,
        movement_type: str,
        reference_type: str,
        reference_id: uuid.UUID,
        reference_number: str,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Update inventory_summary for a product/warehouse combination.

        Creates the record if it doesn't exist.
        Creates a stock_movement record for audit trail.
        """
        # Find or create inventory summary
        inv_query = select(InventorySummary).where(
            and_(
                InventorySummary.warehouse_id == warehouse_id,
                InventorySummary.product_id == product_id,
                InventorySummary.variant_id == variant_id if variant_id else InventorySummary.variant_id.is_(None),
            )
        )
        inv_result = await self.db.execute(inv_query)
        inventory = inv_result.scalar_one_or_none()

        balance_before = 0
        balance_after = quantity_change

        if inventory:
            balance_before = inventory.total_quantity
            # Update with weighted average cost
            if quantity_change > 0:
                # Receiving stock - calculate weighted average
                total_value = (inventory.total_quantity * inventory.average_cost) + (quantity_change * unit_cost)
                new_total = inventory.total_quantity + quantity_change
                inventory.average_cost = total_value / new_total if new_total > 0 else unit_cost
                inventory.total_value = total_value

            inventory.total_quantity += quantity_change
            inventory.available_quantity += quantity_change
            inventory.last_stock_in_date = datetime.now(timezone.utc)
            balance_after = inventory.total_quantity
        else:
            # Create new inventory summary
            inventory = InventorySummary(
                warehouse_id=warehouse_id,
                product_id=product_id,
                variant_id=variant_id,
                total_quantity=quantity_change,
                available_quantity=quantity_change,
                reserved_quantity=0,
                allocated_quantity=0,
                damaged_quantity=0,
                in_transit_quantity=0,
                average_cost=unit_cost,
                total_value=quantity_change * unit_cost,
                reorder_level=10,  # Default
                minimum_stock=5,
                maximum_stock=1000,
                last_stock_in_date=datetime.now(timezone.utc),
            )
            self.db.add(inventory)
            balance_after = quantity_change

        # Create stock movement for audit trail
        movement_number = await self._generate_movement_number()
        movement = StockMovement(
            movement_number=movement_number,
            movement_type=movement_type,
            movement_date=datetime.now(timezone.utc),
            warehouse_id=warehouse_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity_change,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_number=reference_number,
            unit_cost=unit_cost,
            total_cost=unit_cost * quantity_change,
            created_by=user_id,
        )
        self.db.add(movement)

        return {
            "product_id": str(product_id),
            "warehouse_id": str(warehouse_id),
            "balance_before": balance_before,
            "balance_after": balance_after,
            "quantity_added": quantity_change,
            "movement_number": movement_number,
        }

    async def _generate_movement_number(self) -> str:
        """Generate unique stock movement number."""
        now = datetime.now(timezone.utc)
        prefix = f"SM-{now.strftime('%Y%m%d')}"

        # Get max sequence for today
        query = select(func.max(StockMovement.movement_number)).where(
            StockMovement.movement_number.like(f"{prefix}%")
        )
        result = await self.db.scalar(query)

        if result:
            try:
                seq = int(result.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f"{prefix}-{seq:04d}"

    # ==================== FORCED GRN ====================

    async def force_grn_receive(
        self,
        grn_id: uuid.UUID,
        force_reason: str,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Force receive a GRN when serials don't match.

        Only users with 'grn:force_receive' permission can do this.
        Creates stock items without linking to po_serials.

        Args:
            grn_id: GRN ID
            force_reason: Reason for forcing (required)
            user_id: User forcing the GRN (must have grn:force_receive permission)

        Returns:
            Result summary
        """
        if not force_reason or len(force_reason.strip()) < 10:
            raise ValueError("Force reason must be at least 10 characters")

        grn = await self.db.get(GoodsReceiptNote, grn_id)
        if not grn:
            raise ValueError(f"GRN {grn_id} not found")

        # Mark as forced
        grn.is_forced = True
        grn.force_reason = force_reason.strip()
        grn.forced_by = user_id
        grn.serial_validation_status = "SKIPPED"

        await self.db.commit()

        return {
            "grn_id": str(grn_id),
            "grn_number": grn.grn_number,
            "is_forced": True,
            "force_reason": force_reason,
            "message": "GRN marked as forced. Proceed with acceptance.",
        }

    # ==================== CHECK USER PERMISSION ====================

    async def check_force_permission(self, user_id: uuid.UUID) -> bool:
        """
        Check if user has permission to force GRN.

        Returns True if user has 'grn:force_receive' permission.
        """
        from app.models.user import UserRole
        from app.models.permission import Permission, RolePermission

        query = select(Permission.code).select_from(Permission).join(
            RolePermission, Permission.id == RolePermission.permission_id
        ).join(
            UserRole, RolePermission.role_id == UserRole.role_id
        ).where(
            and_(
                UserRole.user_id == user_id,
                Permission.code == "grn:force_receive",
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    # ==================== GET GRN WITH SERIAL STATUS ====================

    async def get_grn_with_serial_status(self, grn_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get GRN details with serial validation status for each item.
        """
        grn_query = select(GoodsReceiptNote).options(
            selectinload(GoodsReceiptNote.items),
            selectinload(GoodsReceiptNote.vendor),
            selectinload(GoodsReceiptNote.warehouse),
            selectinload(GoodsReceiptNote.purchase_order),
        ).where(GoodsReceiptNote.id == grn_id)

        grn_result = await self.db.execute(grn_query)
        grn = grn_result.scalar_one_or_none()

        if not grn:
            return None

        items_with_serial_status = []
        for item in grn.items:
            item_data = {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "product_name": item.product_name,
                "sku": item.sku,
                "quantity_received": item.quantity_received,
                "quantity_accepted": item.quantity_accepted,
                "serial_numbers": item.serial_numbers or [],
                "serial_count": len(item.serial_numbers) if item.serial_numbers else 0,
            }

            # Get serial validation status
            if item.serial_numbers:
                validation = await self.validate_serials_for_grn(
                    po_id=grn.purchase_order_id,
                    product_id=item.product_id,
                    scanned_serials=item.serial_numbers,
                )
                item_data["serial_validation"] = validation
            else:
                item_data["serial_validation"] = {"status": "NO_SERIALS_PROVIDED"}

            items_with_serial_status.append(item_data)

        return {
            "id": str(grn.id),
            "grn_number": grn.grn_number,
            "status": grn.status,
            "is_forced": grn.is_forced,
            "force_reason": grn.force_reason,
            "serial_validation_status": grn.serial_validation_status,
            "stock_items_created": grn.stock_items_created,
            "purchase_order_id": str(grn.purchase_order_id),
            "po_number": grn.purchase_order.po_number if grn.purchase_order else None,
            "warehouse": {
                "id": str(grn.warehouse_id),
                "name": grn.warehouse.name if grn.warehouse else None,
            },
            "items": items_with_serial_status,
        }
