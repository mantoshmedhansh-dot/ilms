"""
Quality Control Service - Phase 7: Inspection & Quality Management.

Business logic for quality control including:
- QC configuration management
- Inspection workflow
- Defect recording
- Hold management
- Sampling operations
"""
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quality_control import (
    QCConfiguration, QCInspection, QCDefect, QCHoldArea, QCSampling,
    InspectionType, InspectionStatus, DefectSeverity, DefectCategory,
    HoldReason, HoldStatus, SamplingPlan, DispositionAction
)
from app.schemas.quality_control import (
    QCConfigurationCreate, QCConfigurationUpdate,
    QCInspectionCreate, QCInspectionUpdate, InspectionStart,
    InspectionResult, InspectionDisposition,
    QCDefectCreate, QCHoldAreaCreate, QCHoldAreaUpdate, HoldRelease,
    QCSamplingCreate, QCSamplingResult,
    QCDashboard
)


class QualityControlService:
    """Service for quality control operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    # ========================================================================
    # QC CONFIGURATION MANAGEMENT
    # ========================================================================

    async def create_config(
        self,
        data: QCConfigurationCreate
    ) -> QCConfiguration:
        """Create QC configuration."""
        config = QCConfiguration(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            config_code=data.config_code,
            config_name=data.config_name,
            description=data.description,
            warehouse_id=data.warehouse_id,
            product_id=data.product_id,
            category_id=data.category_id,
            vendor_id=data.vendor_id,
            inspection_type=data.inspection_type.value,
            sampling_plan=data.sampling_plan.value,
            sample_size_percent=data.sample_size_percent,
            sample_size_quantity=data.sample_size_quantity,
            aql_level=data.aql_level,
            max_defect_percent=data.max_defect_percent,
            max_critical_defects=data.max_critical_defects,
            max_major_defects=data.max_major_defects,
            max_minor_defects=data.max_minor_defects,
            checkpoints=[c.model_dump() for c in data.checkpoints] if data.checkpoints else None,
            measurements=[m.model_dump() for m in data.measurements] if data.measurements else None,
            auto_release_on_pass=data.auto_release_on_pass,
            auto_hold_on_fail=data.auto_hold_on_fail,
            require_supervisor_approval=data.require_supervisor_approval,
            is_receiving_required=data.is_receiving_required,
            is_shipping_required=data.is_shipping_required,
            notes=data.notes,
            is_active=True
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_config(
        self,
        config_id: uuid.UUID
    ) -> Optional[QCConfiguration]:
        """Get QC configuration by ID."""
        result = await self.db.execute(
            select(QCConfiguration)
            .where(
                QCConfiguration.id == config_id,
                QCConfiguration.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_configs(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        vendor_id: Optional[uuid.UUID] = None,
        inspection_type: Optional[InspectionType] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[QCConfiguration], int]:
        """List QC configurations."""
        query = select(QCConfiguration).where(
            QCConfiguration.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(QCConfiguration.warehouse_id == warehouse_id)
        if product_id:
            query = query.where(QCConfiguration.product_id == product_id)
        if vendor_id:
            query = query.where(QCConfiguration.vendor_id == vendor_id)
        if inspection_type:
            query = query.where(QCConfiguration.inspection_type == inspection_type.value)
        if is_active is not None:
            query = query.where(QCConfiguration.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(QCConfiguration.config_code).offset(skip).limit(limit)
        result = await self.db.execute(query)
        configs = result.scalars().all()

        return list(configs), total

    async def update_config(
        self,
        config_id: uuid.UUID,
        data: QCConfigurationUpdate
    ) -> Optional[QCConfiguration]:
        """Update QC configuration."""
        config = await self.get_config(config_id)
        if not config:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(config, key):
                if key == 'sampling_plan' and value:
                    setattr(config, key, value.value)
                elif key == 'checkpoints' and value:
                    setattr(config, key, [c.model_dump() for c in value])
                elif key == 'measurements' and value:
                    setattr(config, key, [m.model_dump() for m in value])
                else:
                    setattr(config, key, value)

        config.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_applicable_config(
        self,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        inspection_type: InspectionType,
        vendor_id: Optional[uuid.UUID] = None
    ) -> Optional[QCConfiguration]:
        """Get applicable QC config for a product."""
        # Try product-specific first
        result = await self.db.execute(
            select(QCConfiguration)
            .where(
                QCConfiguration.tenant_id == self.tenant_id,
                QCConfiguration.product_id == product_id,
                QCConfiguration.inspection_type == inspection_type.value,
                QCConfiguration.is_active == True
            )
            .limit(1)
        )
        config = result.scalar_one_or_none()
        if config:
            return config

        # Try vendor-specific
        if vendor_id:
            result = await self.db.execute(
                select(QCConfiguration)
                .where(
                    QCConfiguration.tenant_id == self.tenant_id,
                    QCConfiguration.vendor_id == vendor_id,
                    QCConfiguration.inspection_type == inspection_type.value,
                    QCConfiguration.is_active == True
                )
                .limit(1)
            )
            config = result.scalar_one_or_none()
            if config:
                return config

        # Try warehouse default
        result = await self.db.execute(
            select(QCConfiguration)
            .where(
                QCConfiguration.tenant_id == self.tenant_id,
                QCConfiguration.warehouse_id == warehouse_id,
                QCConfiguration.product_id == None,
                QCConfiguration.vendor_id == None,
                QCConfiguration.inspection_type == inspection_type.value,
                QCConfiguration.is_active == True
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ========================================================================
    # INSPECTION MANAGEMENT
    # ========================================================================

    async def _generate_inspection_number(self) -> str:
        """Generate unique inspection number."""
        today = date.today()
        prefix = f"QC-{today.strftime('%Y%m%d')}"

        result = await self.db.execute(
            select(func.count(QCInspection.id))
            .where(
                QCInspection.tenant_id == self.tenant_id,
                QCInspection.inspection_number.like(f"{prefix}%")
            )
        )
        count = (result.scalar() or 0) + 1
        return f"{prefix}-{count:04d}"

    async def create_inspection(
        self,
        data: QCInspectionCreate
    ) -> QCInspection:
        """Create QC inspection."""
        inspection_number = await self._generate_inspection_number()

        # Get applicable config
        config = None
        if data.config_id:
            config = await self.get_config(data.config_id)
        else:
            config = await self.get_applicable_config(
                data.product_id,
                data.warehouse_id,
                data.inspection_type,
                data.vendor_id
            )

        # Calculate sample quantity
        sample_qty = data.sample_quantity or data.total_quantity
        if config:
            if config.sampling_plan == SamplingPlan.FULL.value:
                sample_qty = data.total_quantity
            elif config.sample_size_percent:
                sample_qty = int(data.total_quantity * config.sample_size_percent / 100)
            elif config.sample_size_quantity:
                sample_qty = min(config.sample_size_quantity, data.total_quantity)

        inspection = QCInspection(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            inspection_number=inspection_number,
            inspection_type=data.inspection_type.value,
            status=InspectionStatus.PENDING.value,
            warehouse_id=data.warehouse_id,
            zone_id=data.zone_id,
            config_id=config.id if config else None,
            grn_id=data.grn_id,
            shipment_id=data.shipment_id,
            order_id=data.order_id,
            return_order_id=data.return_order_id,
            product_id=data.product_id,
            sku=data.sku,
            product_name=data.product_name,
            vendor_id=data.vendor_id,
            total_quantity=data.total_quantity,
            sample_quantity=sample_qty,
            passed_quantity=0,
            failed_quantity=0,
            pending_quantity=sample_qty,
            lot_number=data.lot_number,
            batch_number=data.batch_number,
            manufacture_date=data.manufacture_date,
            expiry_date=data.expiry_date,
            defect_count=0,
            critical_defects=0,
            major_defects=0,
            minor_defects=0,
            requires_approval=config.require_supervisor_approval if config else False,
            notes=data.notes
        )
        self.db.add(inspection)
        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def get_inspection(
        self,
        inspection_id: uuid.UUID
    ) -> Optional[QCInspection]:
        """Get inspection by ID."""
        result = await self.db.execute(
            select(QCInspection)
            .where(
                QCInspection.id == inspection_id,
                QCInspection.tenant_id == self.tenant_id
            )
            .options(selectinload(QCInspection.defects))
        )
        return result.scalar_one_or_none()

    async def list_inspections(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        inspection_type: Optional[InspectionType] = None,
        status: Optional[InspectionStatus] = None,
        product_id: Optional[uuid.UUID] = None,
        vendor_id: Optional[uuid.UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[QCInspection], int]:
        """List inspections with filters."""
        query = select(QCInspection).where(
            QCInspection.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(QCInspection.warehouse_id == warehouse_id)
        if inspection_type:
            query = query.where(QCInspection.inspection_type == inspection_type.value)
        if status:
            query = query.where(QCInspection.status == status.value)
        if product_id:
            query = query.where(QCInspection.product_id == product_id)
        if vendor_id:
            query = query.where(QCInspection.vendor_id == vendor_id)
        if from_date:
            query = query.where(QCInspection.inspection_date >= from_date)
        if to_date:
            query = query.where(QCInspection.inspection_date <= to_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(QCInspection.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        inspections = result.scalars().all()

        return list(inspections), total

    async def start_inspection(
        self,
        inspection_id: uuid.UUID,
        inspector_id: uuid.UUID,
        data: Optional[InspectionStart] = None
    ) -> Optional[QCInspection]:
        """Start an inspection."""
        inspection = await self.get_inspection(inspection_id)
        if not inspection:
            return None

        inspection.status = InspectionStatus.IN_PROGRESS.value
        inspection.started_at = datetime.now(timezone.utc)
        inspection.inspector_id = inspector_id

        if data and data.sample_quantity:
            inspection.sample_quantity = data.sample_quantity
            inspection.pending_quantity = data.sample_quantity

        inspection.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def record_results(
        self,
        inspection_id: uuid.UUID,
        data: InspectionResult
    ) -> Optional[QCInspection]:
        """Record inspection results."""
        inspection = await self.get_inspection(inspection_id)
        if not inspection:
            return None

        inspection.passed_quantity = data.passed_quantity
        inspection.failed_quantity = data.failed_quantity
        inspection.pending_quantity = max(0,
            inspection.sample_quantity - data.passed_quantity - data.failed_quantity
        )

        if data.checkpoint_results:
            inspection.checkpoint_results = [r.model_dump() for r in data.checkpoint_results]
        if data.measurement_results:
            inspection.measurement_results = [r.model_dump() for r in data.measurement_results]
        if data.photos:
            inspection.photos = data.photos
        if data.notes:
            inspection.notes = data.notes

        # Calculate defect rate
        if inspection.sample_quantity > 0:
            inspection.defect_rate = Decimal(
                inspection.failed_quantity / inspection.sample_quantity * 100
            ).quantize(Decimal('0.01'))

        inspection.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def complete_inspection(
        self,
        inspection_id: uuid.UUID
    ) -> Optional[QCInspection]:
        """Complete an inspection and determine status."""
        inspection = await self.get_inspection(inspection_id)
        if not inspection:
            return None

        now = datetime.now(timezone.utc)
        inspection.completed_at = now

        # Get config for pass/fail criteria
        config = None
        if inspection.config_id:
            config = await self.get_config(inspection.config_id)

        # Determine status based on defects and config
        if inspection.failed_quantity == 0:
            inspection.status = InspectionStatus.PASSED.value
        elif inspection.passed_quantity == 0:
            inspection.status = InspectionStatus.FAILED.value
        else:
            # Check against config limits
            if config:
                if inspection.critical_defects > config.max_critical_defects:
                    inspection.status = InspectionStatus.FAILED.value
                elif inspection.major_defects > config.max_major_defects:
                    inspection.status = InspectionStatus.FAILED.value
                elif config.max_defect_percent and inspection.defect_rate > config.max_defect_percent:
                    inspection.status = InspectionStatus.FAILED.value
                else:
                    inspection.status = InspectionStatus.PARTIAL_PASS.value
            else:
                inspection.status = InspectionStatus.PARTIAL_PASS.value

        inspection.updated_at = now
        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def set_disposition(
        self,
        inspection_id: uuid.UUID,
        data: InspectionDisposition,
        user_id: uuid.UUID
    ) -> Optional[QCInspection]:
        """Set inspection disposition."""
        inspection = await self.get_inspection(inspection_id)
        if not inspection:
            return None

        now = datetime.now(timezone.utc)
        inspection.disposition = data.disposition.value
        inspection.disposition_notes = data.disposition_notes
        inspection.disposition_by = user_id
        inspection.disposition_at = now
        inspection.updated_at = now

        # Create hold if needed
        if data.disposition == DispositionAction.HOLD and inspection.failed_quantity > 0:
            await self.create_hold(
                QCHoldAreaCreate(
                    warehouse_id=inspection.warehouse_id,
                    hold_bin_id=data.hold_bin_id,
                    inspection_id=inspection.id,
                    hold_reason=HoldReason.FAILED_QC,
                    reason_detail=f"QC Failed: {inspection.inspection_number}",
                    product_id=inspection.product_id,
                    sku=inspection.sku,
                    hold_quantity=inspection.failed_quantity,
                    lot_number=inspection.lot_number,
                    vendor_id=inspection.vendor_id
                ),
                user_id
            )

        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    # ========================================================================
    # DEFECT MANAGEMENT
    # ========================================================================

    async def create_defect(
        self,
        data: QCDefectCreate,
        user_id: uuid.UUID
    ) -> QCDefect:
        """Record a defect."""
        defect = QCDefect(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            inspection_id=data.inspection_id,
            defect_code=data.defect_code,
            defect_name=data.defect_name,
            category=data.category.value,
            severity=data.severity.value,
            description=data.description,
            defect_quantity=data.defect_quantity,
            defect_location=data.defect_location,
            serial_numbers=data.serial_numbers,
            root_cause=data.root_cause,
            is_vendor_related=data.is_vendor_related,
            photos=data.photos,
            recorded_by=user_id,
            notes=data.notes
        )
        self.db.add(defect)

        # Update inspection defect counts
        inspection = await self.get_inspection(data.inspection_id)
        if inspection:
            inspection.defect_count += data.defect_quantity
            if data.severity == DefectSeverity.CRITICAL:
                inspection.critical_defects += data.defect_quantity
            elif data.severity == DefectSeverity.MAJOR:
                inspection.major_defects += data.defect_quantity
            elif data.severity == DefectSeverity.MINOR:
                inspection.minor_defects += data.defect_quantity

        await self.db.commit()
        await self.db.refresh(defect)
        return defect

    async def list_defects(
        self,
        inspection_id: Optional[uuid.UUID] = None,
        severity: Optional[DefectSeverity] = None,
        category: Optional[DefectCategory] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[QCDefect], int]:
        """List defects with filters."""
        query = select(QCDefect).where(
            QCDefect.tenant_id == self.tenant_id
        )

        if inspection_id:
            query = query.where(QCDefect.inspection_id == inspection_id)
        if severity:
            query = query.where(QCDefect.severity == severity.value)
        if category:
            query = query.where(QCDefect.category == category.value)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(QCDefect.recorded_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        defects = result.scalars().all()

        return list(defects), total

    # ========================================================================
    # HOLD MANAGEMENT
    # ========================================================================

    async def _generate_hold_number(self) -> str:
        """Generate unique hold number."""
        today = date.today()
        prefix = f"HOLD-{today.strftime('%Y%m%d')}"

        result = await self.db.execute(
            select(func.count(QCHoldArea.id))
            .where(
                QCHoldArea.tenant_id == self.tenant_id,
                QCHoldArea.hold_number.like(f"{prefix}%")
            )
        )
        count = (result.scalar() or 0) + 1
        return f"{prefix}-{count:04d}"

    async def create_hold(
        self,
        data: QCHoldAreaCreate,
        user_id: uuid.UUID
    ) -> QCHoldArea:
        """Create QC hold."""
        hold_number = await self._generate_hold_number()

        hold = QCHoldArea(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            hold_number=hold_number,
            status=HoldStatus.ACTIVE.value,
            warehouse_id=data.warehouse_id,
            hold_bin_id=data.hold_bin_id,
            hold_reason=data.hold_reason.value,
            reason_detail=data.reason_detail,
            inspection_id=data.inspection_id,
            grn_id=data.grn_id,
            return_order_id=data.return_order_id,
            product_id=data.product_id,
            sku=data.sku,
            hold_quantity=data.hold_quantity,
            remaining_quantity=data.hold_quantity,
            released_quantity=0,
            scrapped_quantity=0,
            returned_quantity=0,
            lot_number=data.lot_number,
            serial_numbers=data.serial_numbers,
            vendor_id=data.vendor_id,
            target_resolution_date=data.target_resolution_date,
            created_by=user_id,
            notes=data.notes
        )
        self.db.add(hold)
        await self.db.commit()
        await self.db.refresh(hold)
        return hold

    async def get_hold(
        self,
        hold_id: uuid.UUID
    ) -> Optional[QCHoldArea]:
        """Get hold by ID."""
        result = await self.db.execute(
            select(QCHoldArea)
            .where(
                QCHoldArea.id == hold_id,
                QCHoldArea.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_holds(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[HoldStatus] = None,
        product_id: Optional[uuid.UUID] = None,
        hold_reason: Optional[HoldReason] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[QCHoldArea], int]:
        """List holds with filters."""
        query = select(QCHoldArea).where(
            QCHoldArea.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(QCHoldArea.warehouse_id == warehouse_id)
        if status:
            query = query.where(QCHoldArea.status == status.value)
        if product_id:
            query = query.where(QCHoldArea.product_id == product_id)
        if hold_reason:
            query = query.where(QCHoldArea.hold_reason == hold_reason.value)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(QCHoldArea.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        holds = result.scalars().all()

        return list(holds), total

    async def release_hold(
        self,
        hold_id: uuid.UUID,
        data: HoldRelease,
        user_id: uuid.UUID
    ) -> Optional[QCHoldArea]:
        """Release items from hold."""
        hold = await self.get_hold(hold_id)
        if not hold:
            return None
        if data.release_quantity > hold.remaining_quantity:
            return None

        now = datetime.now(timezone.utc)

        # Update quantities based on action
        if data.resolution_action == DispositionAction.ACCEPT:
            hold.released_quantity += data.release_quantity
        elif data.resolution_action == DispositionAction.SCRAP:
            hold.scrapped_quantity += data.release_quantity
        elif data.resolution_action == DispositionAction.RETURN_TO_VENDOR:
            hold.returned_quantity += data.release_quantity
        else:
            hold.released_quantity += data.release_quantity

        hold.remaining_quantity -= data.release_quantity
        hold.resolution_action = data.resolution_action.value
        hold.resolution_notes = data.resolution_notes
        hold.resolved_by = user_id

        # Check if fully resolved
        if hold.remaining_quantity == 0:
            hold.status = HoldStatus.RELEASED.value
            hold.resolved_date = date.today()

        hold.updated_at = now
        await self.db.commit()
        await self.db.refresh(hold)
        return hold

    # ========================================================================
    # DASHBOARD
    # ========================================================================

    async def get_dashboard(
        self,
        warehouse_id: uuid.UUID,
        from_date: date,
        to_date: date
    ) -> QCDashboard:
        """Get QC dashboard statistics."""
        # Inspection counts
        insp_result = await self.db.execute(
            select(
                func.count(QCInspection.id).label('total'),
                func.count(QCInspection.id).filter(
                    QCInspection.status == InspectionStatus.PENDING.value
                ).label('pending'),
                func.count(QCInspection.id).filter(
                    QCInspection.status == InspectionStatus.IN_PROGRESS.value
                ).label('in_progress'),
                func.count(QCInspection.id).filter(
                    QCInspection.status.notin_([
                        InspectionStatus.PENDING.value,
                        InspectionStatus.IN_PROGRESS.value
                    ])
                ).label('completed'),
                func.count(QCInspection.id).filter(
                    QCInspection.status == InspectionStatus.PASSED.value
                ).label('passed'),
                func.count(QCInspection.id).filter(
                    QCInspection.status == InspectionStatus.FAILED.value
                ).label('failed'),
                func.count(QCInspection.id).filter(
                    QCInspection.status == InspectionStatus.PARTIAL_PASS.value
                ).label('partial'),
                func.sum(QCInspection.defect_count).label('total_defects'),
                func.sum(QCInspection.critical_defects).label('critical'),
                func.sum(QCInspection.major_defects).label('major'),
                func.sum(QCInspection.minor_defects).label('minor')
            )
            .where(
                QCInspection.tenant_id == self.tenant_id,
                QCInspection.warehouse_id == warehouse_id,
                QCInspection.inspection_date >= from_date,
                QCInspection.inspection_date <= to_date
            )
        )
        stats = insp_result.one()

        # Hold stats
        hold_result = await self.db.execute(
            select(
                func.count(QCHoldArea.id).label('count'),
                func.sum(QCHoldArea.remaining_quantity).label('qty')
            )
            .where(
                QCHoldArea.tenant_id == self.tenant_id,
                QCHoldArea.warehouse_id == warehouse_id,
                QCHoldArea.status == HoldStatus.ACTIVE.value
            )
        )
        hold_stats = hold_result.one()

        # Calculate pass rate
        pass_rate = None
        completed = stats.completed or 0
        if completed > 0:
            pass_rate = Decimal((stats.passed or 0) / completed * 100).quantize(Decimal('0.01'))

        return QCDashboard(
            warehouse_id=warehouse_id,
            date_range_start=from_date,
            date_range_end=to_date,
            total_inspections=stats.total or 0,
            completed_inspections=completed,
            pending_inspections=stats.pending or 0,
            in_progress_inspections=stats.in_progress or 0,
            passed_inspections=stats.passed or 0,
            failed_inspections=stats.failed or 0,
            partial_pass_inspections=stats.partial or 0,
            pass_rate=pass_rate,
            total_defects=stats.total_defects or 0,
            critical_defects=stats.critical or 0,
            major_defects=stats.major or 0,
            minor_defects=stats.minor or 0,
            avg_defect_rate=None,
            items_on_hold=hold_stats.count or 0,
            hold_quantity=hold_stats.qty or 0,
            by_inspection_type={},
            by_defect_category={}
        )
