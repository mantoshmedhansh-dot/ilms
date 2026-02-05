"""
Returns Management Service - Phase 9: Reverse Logistics & Return Processing.

Business logic for returns management operations.
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.returns_management import (
    ReturnAuthorization, ReturnAuthorizationItem,
    ReturnReceipt, ReturnReceiptItem,
    ReturnInspection, RefurbishmentOrder, DispositionRecord,
    ReturnType, ReturnReason, RMAStatus, ReturnReceiptStatus,
    InspectionGrade, InspectionStatus, DispositionAction,
    RefurbishmentStatus, RefundType, RefundStatus
)
from app.schemas.returns_management import (
    ReturnAuthorizationCreate, ReturnAuthorizationUpdate, RMAApproval,
    ReturnReceiptCreate, ReturnReceiptUpdate, ReceiveItems,
    ReturnInspectionCreate, ReturnInspectionUpdate,
    InspectionComplete, InspectionDisposition,
    RefurbishmentOrderCreate, RefurbishmentOrderUpdate,
    RefurbishmentComplete, RefurbishmentQC,
    DispositionRecordCreate, DispositionApproval, DispositionExecute,
    ReturnsDashboard
)


class ReturnsManagementService:
    """Service for returns management operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    # =========================================================================
    # RETURN AUTHORIZATION (RMA)
    # =========================================================================

    async def _generate_rma_number(self) -> str:
        """Generate unique RMA number."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"RMA-{today}"

        query = select(func.count(ReturnAuthorization.id)).where(
            ReturnAuthorization.rma_number.like(f"{prefix}%")
        )
        count = await self.db.scalar(query) or 0
        return f"{prefix}-{count + 1:04d}"

    async def create_rma(
        self,
        data: ReturnAuthorizationCreate,
        user_id: Optional[uuid.UUID] = None
    ) -> ReturnAuthorization:
        """Create a return authorization."""
        # Calculate totals
        total_items = sum(item.requested_quantity for item in data.items)
        return_value = sum(item.total_value for item in data.items)

        rma = ReturnAuthorization(
            tenant_id=self.tenant_id,
            rma_number=await self._generate_rma_number(),
            return_type=data.return_type.value,
            status=RMAStatus.PENDING.value,
            order_id=data.order_id,
            order_number=data.order_number,
            invoice_number=data.invoice_number,
            customer_id=data.customer_id,
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            warehouse_id=data.warehouse_id,
            return_reason=data.return_reason.value,
            reason_detail=data.reason_detail,
            total_items=total_items,
            return_value=return_value,
            refund_type=data.refund_type.value if data.refund_type else None,
            return_shipping_method=data.return_shipping_method,
            shipping_paid_by=data.shipping_paid_by,
            pickup_required=data.pickup_required,
            pickup_address=data.pickup_address,
            pickup_scheduled_date=data.pickup_scheduled_date,
            request_date=date.today(),
            photos=data.photos,
            documents=data.documents,
            notes=data.notes,
            created_by=user_id
        )
        self.db.add(rma)
        await self.db.flush()

        # Add items
        for item_data in data.items:
            item = ReturnAuthorizationItem(
                tenant_id=self.tenant_id,
                rma_id=rma.id,
                product_id=item_data.product_id,
                sku=item_data.sku,
                product_name=item_data.product_name,
                ordered_quantity=item_data.ordered_quantity,
                requested_quantity=item_data.requested_quantity,
                unit_price=item_data.unit_price,
                total_value=item_data.total_value,
                return_reason=item_data.return_reason.value,
                reason_detail=item_data.reason_detail,
                serial_numbers=item_data.serial_numbers,
                lot_number=item_data.lot_number,
                photos=item_data.photos,
                notes=item_data.notes
            )
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(rma)
        return rma

    async def get_rma(
        self,
        rma_id: uuid.UUID,
        include_items: bool = True
    ) -> Optional[ReturnAuthorization]:
        """Get RMA by ID."""
        query = select(ReturnAuthorization).where(
            and_(
                ReturnAuthorization.id == rma_id,
                ReturnAuthorization.tenant_id == self.tenant_id
            )
        )
        if include_items:
            query = query.options(selectinload(ReturnAuthorization.items))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_rmas(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        return_type: Optional[ReturnType] = None,
        status: Optional[RMAStatus] = None,
        customer_id: Optional[uuid.UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ReturnAuthorization], int]:
        """List RMAs with filters."""
        query = select(ReturnAuthorization).where(
            ReturnAuthorization.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(ReturnAuthorization.warehouse_id == warehouse_id)
        if return_type:
            query = query.where(ReturnAuthorization.return_type == return_type.value)
        if status:
            query = query.where(ReturnAuthorization.status == status.value)
        if customer_id:
            query = query.where(ReturnAuthorization.customer_id == customer_id)
        if from_date:
            query = query.where(ReturnAuthorization.request_date >= from_date)
        if to_date:
            query = query.where(ReturnAuthorization.request_date <= to_date)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Fetch
        query = query.options(selectinload(ReturnAuthorization.items))
        query = query.order_by(ReturnAuthorization.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_rma(
        self,
        rma_id: uuid.UUID,
        data: ReturnAuthorizationUpdate
    ) -> Optional[ReturnAuthorization]:
        """Update RMA."""
        rma = await self.get_rma(rma_id)
        if not rma:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "return_reason" and value:
                value = value.value
            setattr(rma, field, value)

        rma.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(rma)
        return rma

    async def approve_rma(
        self,
        rma_id: uuid.UUID,
        data: RMAApproval,
        user_id: uuid.UUID
    ) -> Optional[ReturnAuthorization]:
        """Approve or reject RMA."""
        rma = await self.get_rma(rma_id, include_items=True)
        if not rma or rma.status != RMAStatus.PENDING.value:
            return None

        if data.approved:
            rma.status = RMAStatus.APPROVED.value
            rma.approval_date = date.today()
            rma.expiry_date = date.today() + timedelta(days=data.expiry_days)
            rma.approved_by = user_id

            # Process item approvals
            if data.item_approvals:
                for item_approval in data.item_approvals:
                    item_id = item_approval.get("item_id")
                    approved_qty = item_approval.get("approved_quantity", 0)
                    for item in rma.items:
                        if str(item.id) == str(item_id):
                            item.approved_quantity = approved_qty
                            item.status = "APPROVED" if approved_qty > 0 else "REJECTED"
                            item.refund_amount = item.unit_price * approved_qty
                            break
            else:
                # Approve all requested quantities
                for item in rma.items:
                    item.approved_quantity = item.requested_quantity
                    item.status = "APPROVED"
                    item.refund_amount = item.total_value

            rma.approved_items = sum(item.approved_quantity for item in rma.items)
            rma.refund_amount = sum(item.refund_amount for item in rma.items)
        else:
            rma.status = RMAStatus.REJECTED.value
            rma.rejection_reason = data.rejection_reason
            for item in rma.items:
                item.status = "REJECTED"

        if data.notes:
            rma.internal_notes = data.notes

        rma.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(rma)
        return rma

    async def cancel_rma(
        self,
        rma_id: uuid.UUID,
        reason: str
    ) -> Optional[ReturnAuthorization]:
        """Cancel RMA."""
        rma = await self.get_rma(rma_id)
        if not rma or rma.status in [RMAStatus.RECEIVED.value, RMAStatus.CLOSED.value]:
            return None

        rma.status = RMAStatus.CANCELLED.value
        rma.internal_notes = f"Cancelled: {reason}"
        rma.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(rma)
        return rma

    # =========================================================================
    # RETURN RECEIPT
    # =========================================================================

    async def _generate_receipt_number(self) -> str:
        """Generate unique receipt number."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"RR-{today}"

        query = select(func.count(ReturnReceipt.id)).where(
            ReturnReceipt.receipt_number.like(f"{prefix}%")
        )
        count = await self.db.scalar(query) or 0
        return f"{prefix}-{count + 1:04d}"

    async def create_receipt(
        self,
        data: ReturnReceiptCreate,
        user_id: Optional[uuid.UUID] = None
    ) -> ReturnReceipt:
        """Create a return receipt."""
        receipt = ReturnReceipt(
            tenant_id=self.tenant_id,
            receipt_number=await self._generate_receipt_number(),
            status=ReturnReceiptStatus.PENDING.value,
            rma_id=data.rma_id,
            warehouse_id=data.warehouse_id,
            receiving_zone_id=data.receiving_zone_id,
            receiving_bin_id=data.receiving_bin_id,
            carrier=data.carrier,
            tracking_number=data.tracking_number,
            expected_date=data.expected_date,
            receipt_date=data.receipt_date,
            expected_quantity=sum(item.expected_quantity for item in data.items),
            package_condition=data.package_condition,
            condition_notes=data.condition_notes,
            package_photos=data.package_photos,
            notes=data.notes
        )
        self.db.add(receipt)
        await self.db.flush()

        # Add items
        for item_data in data.items:
            item = ReturnReceiptItem(
                tenant_id=self.tenant_id,
                receipt_id=receipt.id,
                rma_item_id=item_data.rma_item_id,
                product_id=item_data.product_id,
                sku=item_data.sku,
                expected_quantity=item_data.expected_quantity,
                received_quantity=item_data.received_quantity,
                damaged_quantity=item_data.damaged_quantity,
                serial_numbers=item_data.serial_numbers,
                lot_number=item_data.lot_number,
                initial_condition=item_data.initial_condition,
                condition_notes=item_data.condition_notes,
                needs_inspection=item_data.needs_inspection,
                notes=item_data.notes
            )
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(receipt)
        return receipt

    async def get_receipt(
        self,
        receipt_id: uuid.UUID,
        include_items: bool = True
    ) -> Optional[ReturnReceipt]:
        """Get receipt by ID."""
        query = select(ReturnReceipt).where(
            and_(
                ReturnReceipt.id == receipt_id,
                ReturnReceipt.tenant_id == self.tenant_id
            )
        )
        if include_items:
            query = query.options(selectinload(ReturnReceipt.items))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_receipts(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[ReturnReceiptStatus] = None,
        rma_id: Optional[uuid.UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ReturnReceipt], int]:
        """List receipts with filters."""
        query = select(ReturnReceipt).where(
            ReturnReceipt.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(ReturnReceipt.warehouse_id == warehouse_id)
        if status:
            query = query.where(ReturnReceipt.status == status.value)
        if rma_id:
            query = query.where(ReturnReceipt.rma_id == rma_id)
        if from_date:
            query = query.where(ReturnReceipt.receipt_date >= from_date)
        if to_date:
            query = query.where(ReturnReceipt.receipt_date <= to_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.options(selectinload(ReturnReceipt.items))
        query = query.order_by(ReturnReceipt.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def receive_items(
        self,
        receipt_id: uuid.UUID,
        data: ReceiveItems,
        user_id: uuid.UUID
    ) -> Optional[ReturnReceipt]:
        """Receive items for a receipt."""
        receipt = await self.get_receipt(receipt_id, include_items=True)
        if not receipt:
            return None

        for item_data in data.items:
            item_id = item_data.get("item_id")
            received_qty = item_data.get("received_quantity", 0)
            damaged_qty = item_data.get("damaged_quantity", 0)

            for item in receipt.items:
                if str(item.id) == str(item_id):
                    item.received_quantity = received_qty
                    item.damaged_quantity = damaged_qty
                    item.initial_condition = item_data.get("condition")
                    item.condition_notes = item_data.get("notes")
                    break

        receipt.received_quantity = sum(item.received_quantity for item in receipt.items)
        receipt.damaged_quantity = sum(item.damaged_quantity for item in receipt.items)
        receipt.missing_quantity = receipt.expected_quantity - receipt.received_quantity
        receipt.status = ReturnReceiptStatus.RECEIVED.value
        receipt.received_by = user_id
        receipt.updated_at = datetime.now(timezone.utc)

        # Update RMA
        rma = await self.get_rma(receipt.rma_id, include_items=False)
        if rma:
            rma.received_items += receipt.received_quantity
            if rma.received_items >= rma.approved_items:
                rma.status = RMAStatus.RECEIVED.value

        await self.db.commit()
        await self.db.refresh(receipt)
        return receipt

    async def complete_receipt(
        self,
        receipt_id: uuid.UUID
    ) -> Optional[ReturnReceipt]:
        """Complete a receipt."""
        receipt = await self.get_receipt(receipt_id)
        if not receipt or receipt.status != ReturnReceiptStatus.RECEIVED.value:
            return None

        receipt.status = ReturnReceiptStatus.COMPLETED.value
        receipt.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(receipt)
        return receipt

    # =========================================================================
    # RETURN INSPECTION
    # =========================================================================

    async def _generate_inspection_number(self) -> str:
        """Generate unique inspection number."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"RI-{today}"

        query = select(func.count(ReturnInspection.id)).where(
            ReturnInspection.inspection_number.like(f"{prefix}%")
        )
        count = await self.db.scalar(query) or 0
        return f"{prefix}-{count + 1:04d}"

    async def create_inspection(
        self,
        data: ReturnInspectionCreate
    ) -> ReturnInspection:
        """Create a return inspection."""
        inspection = ReturnInspection(
            tenant_id=self.tenant_id,
            inspection_number=await self._generate_inspection_number(),
            status=InspectionStatus.PENDING.value,
            receipt_item_id=data.receipt_item_id,
            rma_id=data.rma_id,
            warehouse_id=data.warehouse_id,
            product_id=data.product_id,
            sku=data.sku,
            product_name=data.product_name,
            serial_number=data.serial_number,
            lot_number=data.lot_number,
            inspection_date=data.inspection_date
        )
        self.db.add(inspection)
        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def get_inspection(
        self,
        inspection_id: uuid.UUID
    ) -> Optional[ReturnInspection]:
        """Get inspection by ID."""
        query = select(ReturnInspection).where(
            and_(
                ReturnInspection.id == inspection_id,
                ReturnInspection.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_inspections(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[InspectionStatus] = None,
        grade: Optional[InspectionGrade] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ReturnInspection], int]:
        """List inspections with filters."""
        query = select(ReturnInspection).where(
            ReturnInspection.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(ReturnInspection.warehouse_id == warehouse_id)
        if status:
            query = query.where(ReturnInspection.status == status.value)
        if grade:
            query = query.where(ReturnInspection.grade == grade.value)
        if from_date:
            query = query.where(ReturnInspection.inspection_date >= from_date)
        if to_date:
            query = query.where(ReturnInspection.inspection_date <= to_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(ReturnInspection.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def start_inspection(
        self,
        inspection_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ReturnInspection]:
        """Start an inspection."""
        inspection = await self.get_inspection(inspection_id)
        if not inspection or inspection.status != InspectionStatus.PENDING.value:
            return None

        inspection.status = InspectionStatus.IN_PROGRESS.value
        inspection.inspector_id = user_id
        inspection.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def complete_inspection(
        self,
        inspection_id: uuid.UUID,
        data: InspectionComplete,
        user_id: uuid.UUID
    ) -> Optional[ReturnInspection]:
        """Complete an inspection."""
        inspection = await self.get_inspection(inspection_id)
        if not inspection or inspection.status != InspectionStatus.IN_PROGRESS.value:
            return None

        inspection.status = InspectionStatus.COMPLETED.value
        inspection.grade = data.grade.value
        inspection.checklist_results = data.checklist_results
        inspection.defects_found = data.defects_found
        inspection.defect_count = len(data.defects_found) if data.defects_found else 0
        inspection.claim_verified = data.claim_verified
        inspection.functional_test_passed = data.functional_test_passed
        inspection.cosmetic_condition = data.cosmetic_condition
        inspection.original_packaging = data.original_packaging
        inspection.accessories_complete = data.accessories_complete
        inspection.missing_accessories = data.missing_accessories
        inspection.recommended_disposition = data.recommended_disposition.value
        inspection.refund_eligible = data.refund_eligible
        inspection.refund_deduction = data.refund_deduction
        inspection.photos = data.photos
        inspection.notes = data.notes
        inspection.inspector_id = user_id
        inspection.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def set_inspection_disposition(
        self,
        inspection_id: uuid.UUID,
        data: InspectionDisposition,
        user_id: uuid.UUID
    ) -> Optional[ReturnInspection]:
        """Set final disposition for an inspection."""
        inspection = await self.get_inspection(inspection_id)
        if not inspection or inspection.status != InspectionStatus.COMPLETED.value:
            return None

        inspection.final_disposition = data.disposition.value
        inspection.disposition_notes = data.notes
        inspection.disposition_by = user_id
        inspection.disposition_at = datetime.now(timezone.utc)
        inspection.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    # =========================================================================
    # REFURBISHMENT
    # =========================================================================

    async def _generate_refurb_number(self) -> str:
        """Generate unique refurbishment order number."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"REF-{today}"

        query = select(func.count(RefurbishmentOrder.id)).where(
            RefurbishmentOrder.order_number.like(f"{prefix}%")
        )
        count = await self.db.scalar(query) or 0
        return f"{prefix}-{count + 1:04d}"

    async def create_refurbishment(
        self,
        data: RefurbishmentOrderCreate,
        user_id: Optional[uuid.UUID] = None
    ) -> RefurbishmentOrder:
        """Create a refurbishment order."""
        order = RefurbishmentOrder(
            tenant_id=self.tenant_id,
            order_number=await self._generate_refurb_number(),
            status=RefurbishmentStatus.PENDING.value,
            inspection_id=data.inspection_id,
            warehouse_id=data.warehouse_id,
            product_id=data.product_id,
            sku=data.sku,
            serial_number=data.serial_number,
            refurbishment_type=data.refurbishment_type,
            work_description=data.work_description,
            work_items=data.work_items,
            parts_required=data.parts_required,
            estimated_labor_hours=data.estimated_labor_hours,
            created_date=date.today(),
            due_date=data.due_date,
            vendor_id=data.vendor_id,
            qc_required=data.qc_required,
            notes=data.notes,
            created_by=user_id
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_refurbishment(
        self,
        order_id: uuid.UUID
    ) -> Optional[RefurbishmentOrder]:
        """Get refurbishment order by ID."""
        query = select(RefurbishmentOrder).where(
            and_(
                RefurbishmentOrder.id == order_id,
                RefurbishmentOrder.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_refurbishments(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[RefurbishmentStatus] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[RefurbishmentOrder], int]:
        """List refurbishment orders."""
        query = select(RefurbishmentOrder).where(
            RefurbishmentOrder.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(RefurbishmentOrder.warehouse_id == warehouse_id)
        if status:
            query = query.where(RefurbishmentOrder.status == status.value)
        if from_date:
            query = query.where(RefurbishmentOrder.created_date >= from_date)
        if to_date:
            query = query.where(RefurbishmentOrder.created_date <= to_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(RefurbishmentOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def start_refurbishment(
        self,
        order_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[RefurbishmentOrder]:
        """Start a refurbishment order."""
        order = await self.get_refurbishment(order_id)
        if not order or order.status != RefurbishmentStatus.PENDING.value:
            return None

        order.status = RefurbishmentStatus.IN_PROGRESS.value
        order.started_at = datetime.now(timezone.utc)
        order.assigned_to = user_id
        order.assigned_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def complete_refurbishment(
        self,
        order_id: uuid.UUID,
        data: RefurbishmentComplete,
        user_id: uuid.UUID
    ) -> Optional[RefurbishmentOrder]:
        """Complete a refurbishment order."""
        order = await self.get_refurbishment(order_id)
        if not order or order.status != RefurbishmentStatus.IN_PROGRESS.value:
            return None

        order.result_grade = data.result_grade.value
        order.actual_labor_hours = data.actual_labor_hours
        order.parts_cost = data.parts_cost
        order.labor_cost = data.actual_labor_hours * Decimal("25")  # Assuming $25/hour
        order.total_cost = order.parts_cost + order.labor_cost
        order.result_notes = data.result_notes
        order.destination_bin_id = data.destination_bin_id
        order.after_photos = data.after_photos
        order.completed_at = datetime.now(timezone.utc)

        if order.qc_required:
            order.status = RefurbishmentStatus.IN_PROGRESS.value  # Awaiting QC
        else:
            order.status = RefurbishmentStatus.COMPLETED.value

        order.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def qc_refurbishment(
        self,
        order_id: uuid.UUID,
        data: RefurbishmentQC,
        user_id: uuid.UUID
    ) -> Optional[RefurbishmentOrder]:
        """QC a refurbishment order."""
        order = await self.get_refurbishment(order_id)
        if not order:
            return None

        order.qc_passed = data.passed
        order.qc_by = user_id
        order.qc_at = datetime.now(timezone.utc)
        order.qc_notes = data.notes

        if data.passed:
            order.status = RefurbishmentStatus.COMPLETED.value
        else:
            order.status = RefurbishmentStatus.FAILED.value

        order.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(order)
        return order

    # =========================================================================
    # DISPOSITION
    # =========================================================================

    async def _generate_disposition_number(self) -> str:
        """Generate unique disposition number."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"DSP-{today}"

        query = select(func.count(DispositionRecord.id)).where(
            DispositionRecord.disposition_number.like(f"{prefix}%")
        )
        count = await self.db.scalar(query) or 0
        return f"{prefix}-{count + 1:04d}"

    async def create_disposition(
        self,
        data: DispositionRecordCreate,
        user_id: Optional[uuid.UUID] = None
    ) -> DispositionRecord:
        """Create a disposition record."""
        loss_value = data.original_value - data.recovered_value

        record = DispositionRecord(
            tenant_id=self.tenant_id,
            disposition_number=await self._generate_disposition_number(),
            inspection_id=data.inspection_id,
            refurbishment_id=data.refurbishment_id,
            warehouse_id=data.warehouse_id,
            product_id=data.product_id,
            sku=data.sku,
            serial_number=data.serial_number,
            lot_number=data.lot_number,
            quantity=data.quantity,
            disposition_action=data.disposition_action.value,
            disposition_date=date.today(),
            grade=data.grade.value if data.grade else None,
            original_value=data.original_value,
            recovered_value=data.recovered_value,
            loss_value=loss_value,
            destination_bin_id=data.destination_bin_id,
            vendor_id=data.vendor_id,
            vendor_rma_number=data.vendor_rma_number,
            vendor_credit_amount=data.vendor_credit_amount,
            donation_recipient=data.donation_recipient,
            donation_reference=data.donation_reference,
            destruction_method=data.destruction_method,
            destruction_certificate=data.destruction_certificate,
            environmental_compliance=data.environmental_compliance,
            requires_approval=data.requires_approval,
            reason=data.reason,
            notes=data.notes,
            photos=data.photos,
            created_by=user_id
        )

        # Auto-execute if no approval required
        if not data.requires_approval:
            record.executed_by = user_id
            record.executed_at = datetime.now(timezone.utc)

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_disposition(
        self,
        disposition_id: uuid.UUID
    ) -> Optional[DispositionRecord]:
        """Get disposition by ID."""
        query = select(DispositionRecord).where(
            and_(
                DispositionRecord.id == disposition_id,
                DispositionRecord.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_dispositions(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        disposition_action: Optional[DispositionAction] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[DispositionRecord], int]:
        """List disposition records."""
        query = select(DispositionRecord).where(
            DispositionRecord.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(DispositionRecord.warehouse_id == warehouse_id)
        if disposition_action:
            query = query.where(DispositionRecord.disposition_action == disposition_action.value)
        if from_date:
            query = query.where(DispositionRecord.disposition_date >= from_date)
        if to_date:
            query = query.where(DispositionRecord.disposition_date <= to_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(DispositionRecord.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def approve_disposition(
        self,
        disposition_id: uuid.UUID,
        data: DispositionApproval,
        user_id: uuid.UUID
    ) -> Optional[DispositionRecord]:
        """Approve a disposition."""
        record = await self.get_disposition(disposition_id)
        if not record or not record.requires_approval or record.approved_by:
            return None

        if data.approved:
            record.approved_by = user_id
            record.approved_at = datetime.now(timezone.utc)
        else:
            record.notes = f"Rejected: {data.notes}" if data.notes else "Rejected"

        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def execute_disposition(
        self,
        disposition_id: uuid.UUID,
        data: DispositionExecute,
        user_id: uuid.UUID
    ) -> Optional[DispositionRecord]:
        """Execute a disposition."""
        record = await self.get_disposition(disposition_id)
        if not record or (record.requires_approval and not record.approved_by):
            return None

        if data.destination_bin_id:
            record.destination_bin_id = data.destination_bin_id
        if data.photos:
            record.photos = (record.photos or []) + data.photos
        if data.notes:
            record.notes = f"{record.notes}\n{data.notes}" if record.notes else data.notes

        record.executed_by = user_id
        record.executed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(record)
        return record

    # =========================================================================
    # DASHBOARD
    # =========================================================================

    async def get_dashboard(
        self,
        warehouse_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> ReturnsDashboard:
        """Get returns dashboard statistics."""
        if not from_date:
            from_date = date.today().replace(day=1)
        if not to_date:
            to_date = date.today()

        # RMA Stats
        pending_rmas = await self.db.scalar(
            select(func.count(ReturnAuthorization.id)).where(
                and_(
                    ReturnAuthorization.tenant_id == self.tenant_id,
                    ReturnAuthorization.warehouse_id == warehouse_id,
                    ReturnAuthorization.status == RMAStatus.PENDING.value
                )
            )
        ) or 0

        approved_rmas = await self.db.scalar(
            select(func.count(ReturnAuthorization.id)).where(
                and_(
                    ReturnAuthorization.tenant_id == self.tenant_id,
                    ReturnAuthorization.warehouse_id == warehouse_id,
                    ReturnAuthorization.status == RMAStatus.APPROVED.value
                )
            )
        ) or 0

        total_rmas_mtd = await self.db.scalar(
            select(func.count(ReturnAuthorization.id)).where(
                and_(
                    ReturnAuthorization.tenant_id == self.tenant_id,
                    ReturnAuthorization.warehouse_id == warehouse_id,
                    ReturnAuthorization.request_date >= from_date,
                    ReturnAuthorization.request_date <= to_date
                )
            )
        ) or 0

        total_items_returned_mtd = await self.db.scalar(
            select(func.sum(ReturnAuthorization.received_items)).where(
                and_(
                    ReturnAuthorization.tenant_id == self.tenant_id,
                    ReturnAuthorization.warehouse_id == warehouse_id,
                    ReturnAuthorization.request_date >= from_date,
                    ReturnAuthorization.request_date <= to_date
                )
            )
        ) or 0

        # Receipt Stats
        pending_receipts = await self.db.scalar(
            select(func.count(ReturnReceipt.id)).where(
                and_(
                    ReturnReceipt.tenant_id == self.tenant_id,
                    ReturnReceipt.warehouse_id == warehouse_id,
                    ReturnReceipt.status == ReturnReceiptStatus.PENDING.value
                )
            )
        ) or 0

        received_today = await self.db.scalar(
            select(func.count(ReturnReceipt.id)).where(
                and_(
                    ReturnReceipt.tenant_id == self.tenant_id,
                    ReturnReceipt.warehouse_id == warehouse_id,
                    ReturnReceipt.receipt_date == date.today()
                )
            )
        ) or 0

        # Inspection Stats
        pending_inspections = await self.db.scalar(
            select(func.count(ReturnInspection.id)).where(
                and_(
                    ReturnInspection.tenant_id == self.tenant_id,
                    ReturnInspection.warehouse_id == warehouse_id,
                    ReturnInspection.status == InspectionStatus.PENDING.value
                )
            )
        ) or 0

        completed_inspections_mtd = await self.db.scalar(
            select(func.count(ReturnInspection.id)).where(
                and_(
                    ReturnInspection.tenant_id == self.tenant_id,
                    ReturnInspection.warehouse_id == warehouse_id,
                    ReturnInspection.status == InspectionStatus.COMPLETED.value,
                    ReturnInspection.inspection_date >= from_date,
                    ReturnInspection.inspection_date <= to_date
                )
            )
        ) or 0

        # Grade Distribution
        async def count_by_grade(grade: str) -> int:
            return await self.db.scalar(
                select(func.count(ReturnInspection.id)).where(
                    and_(
                        ReturnInspection.tenant_id == self.tenant_id,
                        ReturnInspection.warehouse_id == warehouse_id,
                        ReturnInspection.grade == grade,
                        ReturnInspection.inspection_date >= from_date,
                        ReturnInspection.inspection_date <= to_date
                    )
                )
            ) or 0

        grade_a_count = await count_by_grade(InspectionGrade.A_NEW.value)
        grade_b_count = await count_by_grade(InspectionGrade.B_GOOD.value)
        grade_c_count = await count_by_grade(InspectionGrade.C_FAIR.value)
        grade_d_count = await count_by_grade(InspectionGrade.D_POOR.value)
        grade_f_count = await count_by_grade(InspectionGrade.F_SCRAP.value)

        # Disposition Stats
        async def count_disposition(action: str) -> int:
            return await self.db.scalar(
                select(func.count(DispositionRecord.id)).where(
                    and_(
                        DispositionRecord.tenant_id == self.tenant_id,
                        DispositionRecord.warehouse_id == warehouse_id,
                        DispositionRecord.disposition_action == action,
                        DispositionRecord.disposition_date >= from_date,
                        DispositionRecord.disposition_date <= to_date
                    )
                )
            ) or 0

        restocked_count = await count_disposition(DispositionAction.RESTOCK.value)
        refurbished_count = await count_disposition(DispositionAction.REFURBISH.value)
        scrapped_count = await count_disposition(DispositionAction.SCRAP.value)
        vendor_returned_count = await count_disposition(DispositionAction.RETURN_TO_VENDOR.value)

        # Financial
        total_return_value_mtd = await self.db.scalar(
            select(func.sum(ReturnAuthorization.return_value)).where(
                and_(
                    ReturnAuthorization.tenant_id == self.tenant_id,
                    ReturnAuthorization.warehouse_id == warehouse_id,
                    ReturnAuthorization.request_date >= from_date,
                    ReturnAuthorization.request_date <= to_date
                )
            )
        ) or Decimal("0")

        total_refund_amount_mtd = await self.db.scalar(
            select(func.sum(ReturnAuthorization.refund_amount)).where(
                and_(
                    ReturnAuthorization.tenant_id == self.tenant_id,
                    ReturnAuthorization.warehouse_id == warehouse_id,
                    ReturnAuthorization.request_date >= from_date,
                    ReturnAuthorization.request_date <= to_date
                )
            )
        ) or Decimal("0")

        total_recovered = await self.db.scalar(
            select(func.sum(DispositionRecord.recovered_value)).where(
                and_(
                    DispositionRecord.tenant_id == self.tenant_id,
                    DispositionRecord.warehouse_id == warehouse_id,
                    DispositionRecord.disposition_date >= from_date,
                    DispositionRecord.disposition_date <= to_date
                )
            )
        ) or Decimal("0")

        total_original = await self.db.scalar(
            select(func.sum(DispositionRecord.original_value)).where(
                and_(
                    DispositionRecord.tenant_id == self.tenant_id,
                    DispositionRecord.warehouse_id == warehouse_id,
                    DispositionRecord.disposition_date >= from_date,
                    DispositionRecord.disposition_date <= to_date
                )
            )
        ) or Decimal("0")

        recovery_rate = (total_recovered / total_original * 100) if total_original > 0 else None

        # Recent Activity
        recent_rmas_query = select(ReturnAuthorization).where(
            and_(
                ReturnAuthorization.tenant_id == self.tenant_id,
                ReturnAuthorization.warehouse_id == warehouse_id
            )
        ).order_by(ReturnAuthorization.created_at.desc()).limit(5)
        recent_rmas_result = await self.db.execute(recent_rmas_query)
        recent_rmas = list(recent_rmas_result.scalars().all())

        recent_inspections_query = select(ReturnInspection).where(
            and_(
                ReturnInspection.tenant_id == self.tenant_id,
                ReturnInspection.warehouse_id == warehouse_id
            )
        ).order_by(ReturnInspection.created_at.desc()).limit(10)
        recent_inspections_result = await self.db.execute(recent_inspections_query)
        recent_inspections = list(recent_inspections_result.scalars().all())

        return ReturnsDashboard(
            pending_rmas=pending_rmas,
            approved_rmas=approved_rmas,
            total_rmas_mtd=total_rmas_mtd,
            total_items_returned_mtd=total_items_returned_mtd,
            pending_receipts=pending_receipts,
            received_today=received_today,
            pending_inspections=pending_inspections,
            completed_inspections_mtd=completed_inspections_mtd,
            grade_a_count=grade_a_count,
            grade_b_count=grade_b_count,
            grade_c_count=grade_c_count,
            grade_d_count=grade_d_count,
            grade_f_count=grade_f_count,
            restocked_count=restocked_count,
            refurbished_count=refurbished_count,
            scrapped_count=scrapped_count,
            vendor_returned_count=vendor_returned_count,
            total_return_value_mtd=total_return_value_mtd,
            total_refund_amount_mtd=total_refund_amount_mtd,
            recovery_rate=recovery_rate,
            recent_rmas=recent_rmas,
            recent_inspections=recent_inspections
        )
