"""
Mobile WMS Service - Phase 5: RF Scanner & Mobile Operations.

Business logic for mobile warehouse operations including:
- Device management and heartbeat
- Barcode validation and scanning
- Task queue management
- Pick confirmations
- Offline sync processing
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.mobile_wms import (
    MobileDevice, MobileScanLog, MobileTaskQueue, PickConfirmation,
    OfflineSyncQueue, DeviceStatus, ScanResult, ConfirmationStatus,
    OfflineSyncStatus
)
from app.models.product import Product
from app.models.wms import WarehouseBin
from app.schemas.mobile_wms import (
    MobileDeviceCreate, MobileDeviceUpdate, MobileDeviceHeartbeat,
    ScanLogCreate, ScanValidationRequest, ScanValidationResponse,
    TaskQueueCreate, TaskQueueUpdate, WorkerTaskQueue,
    PickConfirmationCreate, OfflineSyncCreate, OfflineSyncBatch,
    SyncResult, SyncBatchResult, MobileDashboard, DeviceStats,
    WarehouseDeviceStats
)


class MobileWMSService:
    """Service for mobile WMS operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    # ========================================================================
    # DEVICE MANAGEMENT
    # ========================================================================

    async def create_device(
        self,
        data: MobileDeviceCreate
    ) -> MobileDevice:
        """Register a new mobile device."""
        device = MobileDevice(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            device_code=data.device_code,
            device_name=data.device_name,
            device_type=data.device_type.value,
            status=DeviceStatus.ACTIVE.value,
            manufacturer=data.manufacturer,
            model=data.model,
            serial_number=data.serial_number,
            imei=data.imei,
            mac_address=data.mac_address,
            os_version=data.os_version,
            app_version=data.app_version,
            firmware_version=data.firmware_version,
            warehouse_id=data.warehouse_id,
            config=data.config,
            scan_settings=data.scan_settings,
            notes=data.notes,
            is_online=False,
            total_scans=0,
            scans_today=0,
        )
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def get_device(self, device_id: uuid.UUID) -> Optional[MobileDevice]:
        """Get device by ID."""
        result = await self.db.execute(
            select(MobileDevice)
            .where(
                MobileDevice.id == device_id,
                MobileDevice.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def get_device_by_code(self, device_code: str) -> Optional[MobileDevice]:
        """Get device by device code."""
        result = await self.db.execute(
            select(MobileDevice)
            .where(
                MobileDevice.device_code == device_code,
                MobileDevice.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_devices(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[DeviceStatus] = None,
        device_type: Optional[str] = None,
        is_online: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[MobileDevice], int]:
        """List devices with filters."""
        query = select(MobileDevice).where(
            MobileDevice.tenant_id == self.tenant_id
        )

        if warehouse_id:
            query = query.where(MobileDevice.warehouse_id == warehouse_id)
        if status:
            query = query.where(MobileDevice.status == status.value)
        if device_type:
            query = query.where(MobileDevice.device_type == device_type)
        if is_online is not None:
            query = query.where(MobileDevice.is_online == is_online)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(MobileDevice.device_code).offset(skip).limit(limit)
        result = await self.db.execute(query)
        devices = result.scalars().all()

        return list(devices), total

    async def update_device(
        self,
        device_id: uuid.UUID,
        data: MobileDeviceUpdate
    ) -> Optional[MobileDevice]:
        """Update device details."""
        device = await self.get_device(device_id)
        if not device:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(device, key):
                if key == 'status' and value:
                    setattr(device, key, value.value)
                elif key == 'device_type' and value:
                    setattr(device, key, value.value)
                else:
                    setattr(device, key, value)

        device.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def assign_device(
        self,
        device_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[MobileDevice]:
        """Assign device to a worker."""
        device = await self.get_device(device_id)
        if not device:
            return None

        device.assigned_to = user_id
        device.assigned_at = datetime.now(timezone.utc)
        device.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def unassign_device(self, device_id: uuid.UUID) -> Optional[MobileDevice]:
        """Unassign device from worker."""
        device = await self.get_device(device_id)
        if not device:
            return None

        device.assigned_to = None
        device.assigned_at = None
        device.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def update_heartbeat(
        self,
        device_id: uuid.UUID,
        data: MobileDeviceHeartbeat
    ) -> Optional[MobileDevice]:
        """Update device heartbeat."""
        device = await self.get_device(device_id)
        if not device:
            return None

        device.is_online = True
        device.last_heartbeat = datetime.now(timezone.utc)

        if data.battery_level is not None:
            device.battery_level = data.battery_level
            device.last_battery_update = datetime.now(timezone.utc)
        if data.ip_address:
            device.ip_address = data.ip_address
        if data.app_version:
            device.app_version = data.app_version

        device.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def mark_offline_devices(self, timeout_minutes: int = 5) -> int:
        """Mark devices as offline if no heartbeat in timeout period."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

        result = await self.db.execute(
            update(MobileDevice)
            .where(
                MobileDevice.tenant_id == self.tenant_id,
                MobileDevice.is_online == True,
                or_(
                    MobileDevice.last_heartbeat < cutoff,
                    MobileDevice.last_heartbeat == None
                )
            )
            .values(is_online=False)
        )
        await self.db.commit()
        return result.rowcount

    # ========================================================================
    # BARCODE SCANNING
    # ========================================================================

    async def log_scan(
        self,
        data: ScanLogCreate,
        user_id: uuid.UUID
    ) -> MobileScanLog:
        """Log a barcode scan."""
        # Validate the scan
        validation = await self.validate_scan(
            ScanValidationRequest(
                barcode=data.barcode,
                scan_type=data.scan_type,
                expected_value=data.expected_value,
                task_id=data.task_id,
                bin_id=data.bin_id
            )
        )

        scan_log = MobileScanLog(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            device_id=data.device_id,
            user_id=user_id,
            barcode=data.barcode,
            scan_type=data.scan_type.value,
            scan_result=validation.scan_result.value,
            warehouse_id=data.warehouse_id,
            zone_id=data.zone_id,
            bin_id=data.bin_id,
            task_id=data.task_id,
            picklist_id=data.picklist_id,
            product_id=data.product_id or validation.matched_entity_id,
            expected_value=data.expected_value,
            is_match=validation.is_valid,
            error_message=validation.message if not validation.is_valid else None,
            gps_latitude=data.gps_latitude,
            gps_longitude=data.gps_longitude,
            is_offline_scan=data.is_offline_scan,
            offline_created_at=data.offline_created_at,
            sync_status="SYNCED" if not data.is_offline_scan else OfflineSyncStatus.SYNCED.value
        )
        self.db.add(scan_log)

        # Update device scan counts
        await self.db.execute(
            update(MobileDevice)
            .where(MobileDevice.id == data.device_id)
            .values(
                total_scans=MobileDevice.total_scans + 1,
                scans_today=MobileDevice.scans_today + 1,
                last_scan_at=datetime.now(timezone.utc)
            )
        )

        await self.db.commit()
        await self.db.refresh(scan_log)
        return scan_log

    async def validate_scan(
        self,
        data: ScanValidationRequest
    ) -> ScanValidationResponse:
        """Validate a scanned barcode."""
        # If expected value provided, check match
        if data.expected_value:
            is_match = data.barcode == data.expected_value
            return ScanValidationResponse(
                is_valid=is_match,
                scan_result=ScanResult.VALID if is_match else ScanResult.MISMATCH,
                message=None if is_match else f"Expected {data.expected_value}, got {data.barcode}"
            )

        # Product scan validation
        if data.scan_type.value == "PRODUCT":
            result = await self.db.execute(
                select(Product)
                .where(
                    Product.tenant_id == self.tenant_id,
                    or_(
                        Product.sku == data.barcode,
                        Product.barcode == data.barcode
                    )
                )
            )
            product = result.scalar_one_or_none()
            if product:
                return ScanValidationResponse(
                    is_valid=True,
                    scan_result=ScanResult.VALID,
                    matched_entity_id=product.id,
                    matched_entity_type="product",
                    metadata={"sku": product.sku, "name": product.name}
                )
            return ScanValidationResponse(
                is_valid=False,
                scan_result=ScanResult.NOT_FOUND,
                message=f"Product not found: {data.barcode}"
            )

        # Bin scan validation
        if data.scan_type.value == "BIN":
            result = await self.db.execute(
                select(WarehouseBin)
                .where(
                    WarehouseBin.tenant_id == self.tenant_id,
                    WarehouseBin.bin_code == data.barcode
                )
            )
            bin_loc = result.scalar_one_or_none()
            if bin_loc:
                return ScanValidationResponse(
                    is_valid=True,
                    scan_result=ScanResult.VALID,
                    matched_entity_id=bin_loc.id,
                    matched_entity_type="bin",
                    metadata={"bin_code": bin_loc.bin_code}
                )
            return ScanValidationResponse(
                is_valid=False,
                scan_result=ScanResult.NOT_FOUND,
                message=f"Bin not found: {data.barcode}"
            )

        # Default - assume valid
        return ScanValidationResponse(
            is_valid=True,
            scan_result=ScanResult.VALID
        )

    async def get_scan_logs(
        self,
        device_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        scan_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[MobileScanLog], int]:
        """Get scan logs with filters."""
        query = select(MobileScanLog).where(
            MobileScanLog.tenant_id == self.tenant_id
        )

        if device_id:
            query = query.where(MobileScanLog.device_id == device_id)
        if user_id:
            query = query.where(MobileScanLog.user_id == user_id)
        if warehouse_id:
            query = query.where(MobileScanLog.warehouse_id == warehouse_id)
        if from_date:
            query = query.where(MobileScanLog.scanned_at >= from_date)
        if to_date:
            query = query.where(MobileScanLog.scanned_at <= to_date)
        if scan_type:
            query = query.where(MobileScanLog.scan_type == scan_type)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(MobileScanLog.scanned_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        logs = result.scalars().all()

        return list(logs), total

    # ========================================================================
    # TASK QUEUE MANAGEMENT
    # ========================================================================

    async def create_task_queue(
        self,
        data: TaskQueueCreate
    ) -> MobileTaskQueue:
        """Add task to worker's queue."""
        task_queue = MobileTaskQueue(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            worker_id=data.worker_id,
            device_id=data.device_id,
            warehouse_id=data.warehouse_id,
            task_id=data.task_id,
            task_type=data.task_type,
            priority=data.priority,
            sequence=data.sequence,
            status="QUEUED",
            task_summary=data.task_summary,
            source_bin_code=data.source_bin_code,
            destination_bin_code=data.destination_bin_code,
            sku=data.sku,
            product_name=data.product_name,
            quantity_required=data.quantity_required,
            quantity_completed=0,
            is_offline_task=False,
            sync_status="SYNCED"
        )
        self.db.add(task_queue)
        await self.db.commit()
        await self.db.refresh(task_queue)
        return task_queue

    async def get_worker_queue(
        self,
        worker_id: uuid.UUID,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        include_completed: bool = False
    ) -> WorkerTaskQueue:
        """Get worker's task queue."""
        query = select(MobileTaskQueue).where(
            MobileTaskQueue.tenant_id == self.tenant_id,
            MobileTaskQueue.worker_id == worker_id
        )

        if warehouse_id:
            query = query.where(MobileTaskQueue.warehouse_id == warehouse_id)
        if status:
            query = query.where(MobileTaskQueue.status == status)
        if not include_completed:
            query = query.where(MobileTaskQueue.status.notin_(["COMPLETED", "SKIPPED"]))

        query = query.order_by(MobileTaskQueue.priority, MobileTaskQueue.sequence)
        result = await self.db.execute(query)
        tasks = list(result.scalars().all())

        # Calculate stats
        pending = sum(1 for t in tasks if t.status == "QUEUED")
        active = sum(1 for t in tasks if t.status == "ACTIVE")
        completed = sum(1 for t in tasks if t.status == "COMPLETED")

        return WorkerTaskQueue(
            tasks=tasks,
            total_tasks=len(tasks),
            pending_count=pending,
            active_count=active,
            completed_count=completed
        )

    async def start_task(
        self,
        task_queue_id: uuid.UUID
    ) -> Optional[MobileTaskQueue]:
        """Start working on a task."""
        result = await self.db.execute(
            select(MobileTaskQueue)
            .where(
                MobileTaskQueue.id == task_queue_id,
                MobileTaskQueue.tenant_id == self.tenant_id
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return None

        task.status = "ACTIVE"
        task.started_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def complete_task(
        self,
        task_queue_id: uuid.UUID,
        quantity_completed: int
    ) -> Optional[MobileTaskQueue]:
        """Complete a task."""
        result = await self.db.execute(
            select(MobileTaskQueue)
            .where(
                MobileTaskQueue.id == task_queue_id,
                MobileTaskQueue.tenant_id == self.tenant_id
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return None

        task.status = "COMPLETED"
        task.quantity_completed = quantity_completed
        task.completed_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def skip_task(
        self,
        task_queue_id: uuid.UUID,
        skip_reason: str
    ) -> Optional[MobileTaskQueue]:
        """Skip a task."""
        result = await self.db.execute(
            select(MobileTaskQueue)
            .where(
                MobileTaskQueue.id == task_queue_id,
                MobileTaskQueue.tenant_id == self.tenant_id
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return None

        task.status = "SKIPPED"
        task.skip_reason = skip_reason
        task.skipped_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_next_task(
        self,
        worker_id: uuid.UUID,
        warehouse_id: uuid.UUID
    ) -> Optional[MobileTaskQueue]:
        """Get the next task for a worker."""
        result = await self.db.execute(
            select(MobileTaskQueue)
            .where(
                MobileTaskQueue.tenant_id == self.tenant_id,
                MobileTaskQueue.worker_id == worker_id,
                MobileTaskQueue.warehouse_id == warehouse_id,
                MobileTaskQueue.status == "QUEUED"
            )
            .order_by(MobileTaskQueue.priority, MobileTaskQueue.sequence)
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ========================================================================
    # PICK CONFIRMATIONS
    # ========================================================================

    async def create_pick_confirmation(
        self,
        data: PickConfirmationCreate,
        user_id: uuid.UUID
    ) -> PickConfirmation:
        """Create a pick confirmation."""
        # Determine status based on quantities
        status = ConfirmationStatus.CONFIRMED.value
        if data.quantity_short > 0:
            if data.quantity_confirmed == 0:
                status = ConfirmationStatus.SHORTED.value
            else:
                status = ConfirmationStatus.PARTIAL.value

        # Validate barcodes
        bin_scan_valid = True
        product_scan_valid = True

        if data.bin_barcode_scanned and data.bin_code:
            bin_scan_valid = data.bin_barcode_scanned == data.bin_code

        if data.product_barcode_scanned:
            # Check against product
            result = await self.db.execute(
                select(Product)
                .where(
                    Product.tenant_id == self.tenant_id,
                    or_(
                        Product.sku == data.sku,
                        Product.barcode == data.product_barcode_scanned
                    )
                )
            )
            product = result.scalar_one_or_none()
            product_scan_valid = product is not None

        confirmation = PickConfirmation(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            task_id=data.task_id,
            picklist_id=data.picklist_id,
            picklist_item_id=data.picklist_item_id,
            device_id=data.device_id,
            user_id=user_id,
            warehouse_id=data.warehouse_id,
            bin_id=data.bin_id,
            bin_code=data.bin_code,
            product_id=data.product_id,
            sku=data.sku,
            quantity_required=data.quantity_required,
            quantity_confirmed=data.quantity_confirmed,
            quantity_short=data.quantity_short,
            status=status,
            short_reason=data.short_reason,
            bin_barcode_scanned=data.bin_barcode_scanned,
            bin_scan_valid=bin_scan_valid,
            product_barcode_scanned=data.product_barcode_scanned,
            product_scan_valid=product_scan_valid,
            serial_numbers=data.serial_numbers,
            lot_numbers=data.lot_numbers,
            is_substitution=data.is_substitution,
            original_sku=data.original_sku,
            substitution_reason=data.substitution_reason,
            is_offline_confirmation=data.is_offline_confirmation,
            offline_created_at=data.offline_created_at,
            sync_status="SYNCED" if not data.is_offline_confirmation else OfflineSyncStatus.SYNCED.value,
            notes=data.notes
        )
        self.db.add(confirmation)
        await self.db.commit()
        await self.db.refresh(confirmation)
        return confirmation

    async def get_pick_confirmations(
        self,
        task_id: Optional[uuid.UUID] = None,
        picklist_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[PickConfirmation], int]:
        """Get pick confirmations with filters."""
        query = select(PickConfirmation).where(
            PickConfirmation.tenant_id == self.tenant_id
        )

        if task_id:
            query = query.where(PickConfirmation.task_id == task_id)
        if picklist_id:
            query = query.where(PickConfirmation.picklist_id == picklist_id)
        if user_id:
            query = query.where(PickConfirmation.user_id == user_id)
        if warehouse_id:
            query = query.where(PickConfirmation.warehouse_id == warehouse_id)
        if from_date:
            query = query.where(PickConfirmation.confirmed_at >= from_date)
        if to_date:
            query = query.where(PickConfirmation.confirmed_at <= to_date)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(PickConfirmation.confirmed_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        confirmations = result.scalars().all()

        return list(confirmations), total

    # ========================================================================
    # OFFLINE SYNC
    # ========================================================================

    async def process_offline_sync(
        self,
        data: OfflineSyncBatch,
        user_id: uuid.UUID
    ) -> SyncBatchResult:
        """Process a batch of offline sync items."""
        results: List[SyncResult] = []
        success_count = 0
        failed_count = 0

        for item in data.items:
            sync_entry = OfflineSyncQueue(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                device_id=data.device_id,
                user_id=user_id,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                operation=item.operation,
                payload=item.payload,
                status=OfflineSyncStatus.PENDING.value,
                offline_created_at=item.offline_created_at,
                retry_count=0,
                max_retries=3
            )
            self.db.add(sync_entry)
            await self.db.flush()

            # Process the sync item
            try:
                entity_id = await self._process_sync_item(sync_entry, user_id)
                sync_entry.status = OfflineSyncStatus.SYNCED.value
                sync_entry.entity_id = entity_id
                sync_entry.synced_at = datetime.now(timezone.utc)

                results.append(SyncResult(
                    sync_id=sync_entry.id,
                    success=True,
                    entity_type=item.entity_type,
                    entity_id=entity_id
                ))
                success_count += 1

            except Exception as e:
                sync_entry.status = OfflineSyncStatus.FAILED.value
                sync_entry.last_error = str(e)
                sync_entry.failed_at = datetime.now(timezone.utc)
                sync_entry.retry_count += 1

                results.append(SyncResult(
                    sync_id=sync_entry.id,
                    success=False,
                    entity_type=item.entity_type,
                    error=str(e)
                ))
                failed_count += 1

        await self.db.commit()

        return SyncBatchResult(
            total=len(data.items),
            success_count=success_count,
            failed_count=failed_count,
            results=results
        )

    async def _process_sync_item(
        self,
        sync_entry: OfflineSyncQueue,
        user_id: uuid.UUID
    ) -> Optional[uuid.UUID]:
        """Process a single sync item."""
        entity_type = sync_entry.entity_type
        operation = sync_entry.operation
        payload = sync_entry.payload

        if entity_type == "SCAN_LOG" and operation == "CREATE":
            scan_data = ScanLogCreate(**payload)
            scan_log = await self.log_scan(scan_data, user_id)
            return scan_log.id

        elif entity_type == "PICK_CONFIRMATION" and operation == "CREATE":
            pick_data = PickConfirmationCreate(**payload)
            confirmation = await self.create_pick_confirmation(pick_data, user_id)
            return confirmation.id

        elif entity_type == "TASK_UPDATE" and operation == "UPDATE":
            task_id = payload.get("task_queue_id")
            if task_id:
                task_id = uuid.UUID(task_id)
                status = payload.get("status")
                if status == "COMPLETED":
                    qty = payload.get("quantity_completed", 0)
                    await self.complete_task(task_id, qty)
                elif status == "SKIPPED":
                    reason = payload.get("skip_reason", "")
                    await self.skip_task(task_id, reason)
                return task_id

        return None

    async def get_pending_sync_items(
        self,
        device_id: uuid.UUID,
        limit: int = 100
    ) -> List[OfflineSyncQueue]:
        """Get pending sync items for retry."""
        result = await self.db.execute(
            select(OfflineSyncQueue)
            .where(
                OfflineSyncQueue.tenant_id == self.tenant_id,
                OfflineSyncQueue.device_id == device_id,
                OfflineSyncQueue.status == OfflineSyncStatus.PENDING.value,
                OfflineSyncQueue.retry_count < OfflineSyncQueue.max_retries
            )
            .order_by(OfflineSyncQueue.offline_created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ========================================================================
    # DASHBOARD & STATS
    # ========================================================================

    async def get_worker_dashboard(
        self,
        worker_id: uuid.UUID,
        warehouse_id: uuid.UUID
    ) -> MobileDashboard:
        """Get mobile dashboard for worker."""
        from app.models.user import User
        from app.models.warehouse import Warehouse

        # Get user info
        user_result = await self.db.execute(
            select(User).where(User.id == worker_id)
        )
        user = user_result.scalar_one_or_none()
        worker_name = user.full_name if user else "Unknown"

        # Get warehouse info
        wh_result = await self.db.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = wh_result.scalar_one_or_none()
        warehouse_name = warehouse.name if warehouse else "Unknown"

        # Get today's task stats
        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)

        task_result = await self.db.execute(
            select(
                func.count(MobileTaskQueue.id).label('total'),
                func.sum(func.case(
                    (MobileTaskQueue.status == 'COMPLETED', 1),
                    else_=0
                )).label('completed'),
                func.sum(func.case(
                    (MobileTaskQueue.status == 'QUEUED', 1),
                    else_=0
                )).label('pending')
            )
            .where(
                MobileTaskQueue.tenant_id == self.tenant_id,
                MobileTaskQueue.worker_id == worker_id,
                MobileTaskQueue.warehouse_id == warehouse_id,
                MobileTaskQueue.created_at >= today_start
            )
        )
        task_stats = task_result.one()

        # Get units picked today
        pick_result = await self.db.execute(
            select(func.sum(PickConfirmation.quantity_confirmed))
            .where(
                PickConfirmation.tenant_id == self.tenant_id,
                PickConfirmation.user_id == worker_id,
                PickConfirmation.warehouse_id == warehouse_id,
                PickConfirmation.confirmed_at >= today_start
            )
        )
        units_picked = pick_result.scalar() or 0

        # Calculate accuracy
        accuracy_result = await self.db.execute(
            select(
                func.count(MobileScanLog.id).filter(MobileScanLog.is_match == True).label('valid'),
                func.count(MobileScanLog.id).label('total')
            )
            .where(
                MobileScanLog.tenant_id == self.tenant_id,
                MobileScanLog.user_id == worker_id,
                MobileScanLog.scanned_at >= today_start
            )
        )
        accuracy_stats = accuracy_result.one()
        accuracy_rate = None
        if accuracy_stats.total and accuracy_stats.total > 0:
            accuracy_rate = Decimal(accuracy_stats.valid / accuracy_stats.total * 100).quantize(Decimal('0.01'))

        return MobileDashboard(
            worker_id=worker_id,
            worker_name=worker_name,
            warehouse_id=warehouse_id,
            warehouse_name=warehouse_name,
            tasks_assigned=task_stats.total or 0,
            tasks_completed=task_stats.completed or 0,
            tasks_pending=task_stats.pending or 0,
            units_picked=units_picked,
            accuracy_rate=accuracy_rate,
            alerts=[]
        )

    async def get_device_stats(
        self,
        device_id: uuid.UUID
    ) -> Optional[DeviceStats]:
        """Get statistics for a device."""
        device = await self.get_device(device_id)
        if not device:
            return None

        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)

        # Get scan stats
        scan_result = await self.db.execute(
            select(
                func.count(MobileScanLog.id).label('total'),
                func.count(MobileScanLog.id).filter(MobileScanLog.scan_result == 'VALID').label('valid'),
                func.count(MobileScanLog.id).filter(MobileScanLog.scan_result != 'VALID').label('invalid')
            )
            .where(
                MobileScanLog.tenant_id == self.tenant_id,
                MobileScanLog.device_id == device_id,
                MobileScanLog.scanned_at >= today_start
            )
        )
        scan_stats = scan_result.one()

        # Get task stats
        task_result = await self.db.execute(
            select(func.count(MobileTaskQueue.id))
            .where(
                MobileTaskQueue.tenant_id == self.tenant_id,
                MobileTaskQueue.device_id == device_id,
                MobileTaskQueue.status == 'COMPLETED',
                MobileTaskQueue.completed_at >= today_start
            )
        )
        tasks_completed = task_result.scalar() or 0

        return DeviceStats(
            device_id=device.id,
            device_code=device.device_code,
            total_scans_today=scan_stats.total or 0,
            valid_scans=scan_stats.valid or 0,
            invalid_scans=scan_stats.invalid or 0,
            tasks_completed=tasks_completed,
            last_activity=device.last_scan_at,
            battery_level=device.battery_level,
            is_online=device.is_online
        )

    async def get_warehouse_device_stats(
        self,
        warehouse_id: uuid.UUID
    ) -> WarehouseDeviceStats:
        """Get device statistics for a warehouse."""
        devices, _ = await self.list_devices(warehouse_id=warehouse_id, limit=1000)

        total = len(devices)
        online = sum(1 for d in devices if d.is_online)
        offline = total - online
        low_battery = sum(1 for d in devices if d.battery_level and d.battery_level < 20)

        device_stats_list = []
        for device in devices:
            stats = await self.get_device_stats(device.id)
            if stats:
                device_stats_list.append(stats)

        return WarehouseDeviceStats(
            warehouse_id=warehouse_id,
            total_devices=total,
            online_devices=online,
            offline_devices=offline,
            low_battery_devices=low_battery,
            devices=device_stats_list
        )

    async def reset_daily_scan_counts(self) -> int:
        """Reset daily scan counts for all devices (run at midnight)."""
        result = await self.db.execute(
            update(MobileDevice)
            .where(MobileDevice.tenant_id == self.tenant_id)
            .values(scans_today=0)
        )
        await self.db.commit()
        return result.rowcount
