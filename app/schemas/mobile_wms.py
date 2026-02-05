"""
Mobile WMS Schemas - Phase 5: RF Scanner & Mobile Operations.

Pydantic schemas for mobile warehouse operations including:
- Device management
- Barcode scanning
- Task queues
- Pick confirmations
- Offline sync
"""
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.mobile_wms import (
    DeviceType, DeviceStatus, ScanType, ScanResult,
    ConfirmationStatus, OfflineSyncStatus
)


# ============================================================================
# MOBILE DEVICE SCHEMAS
# ============================================================================

class MobileDeviceBase(BaseModel):
    """Base schema for mobile device."""
    device_code: str = Field(..., max_length=50, description="Unique device ID e.g., RF-001")
    device_name: str = Field(..., max_length=100)
    device_type: DeviceType = DeviceType.RF_SCANNER
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    imei: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=50)
    app_version: Optional[str] = Field(None, max_length=50)
    firmware_version: Optional[str] = Field(None, max_length=50)
    warehouse_id: Optional[UUID] = None
    config: Optional[Dict[str, Any]] = None
    scan_settings: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class MobileDeviceCreate(MobileDeviceBase):
    """Schema for creating a mobile device."""
    pass


class MobileDeviceUpdate(BaseModel):
    """Schema for updating a mobile device."""
    device_name: Optional[str] = Field(None, max_length=100)
    device_type: Optional[DeviceType] = None
    status: Optional[DeviceStatus] = None
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    os_version: Optional[str] = Field(None, max_length=50)
    app_version: Optional[str] = Field(None, max_length=50)
    firmware_version: Optional[str] = Field(None, max_length=50)
    warehouse_id: Optional[UUID] = None
    config: Optional[Dict[str, Any]] = None
    scan_settings: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class MobileDeviceAssign(BaseModel):
    """Schema for assigning device to worker."""
    user_id: UUID


class MobileDeviceHeartbeat(BaseModel):
    """Schema for device heartbeat update."""
    battery_level: Optional[int] = Field(None, ge=0, le=100)
    ip_address: Optional[str] = Field(None, max_length=50)
    app_version: Optional[str] = Field(None, max_length=50)


class MobileDeviceResponse(MobileDeviceBase):
    """Response schema for mobile device."""
    id: UUID
    tenant_id: UUID
    status: DeviceStatus
    assigned_to: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    battery_level: Optional[int] = None
    last_battery_update: Optional[datetime] = None
    is_online: bool
    last_heartbeat: Optional[datetime] = None
    ip_address: Optional[str] = None
    total_scans: int
    scans_today: int
    last_scan_at: Optional[datetime] = None
    last_maintenance_date: Optional[date] = None
    next_maintenance_date: Optional[date] = None
    registered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# SCAN LOG SCHEMAS
# ============================================================================

class ScanLogCreate(BaseModel):
    """Schema for creating a scan log entry."""
    device_id: UUID
    barcode: str = Field(..., max_length=255)
    scan_type: ScanType
    warehouse_id: Optional[UUID] = None
    zone_id: Optional[UUID] = None
    bin_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    picklist_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    expected_value: Optional[str] = Field(None, max_length=255)
    gps_latitude: Optional[Decimal] = None
    gps_longitude: Optional[Decimal] = None
    is_offline_scan: bool = False
    offline_created_at: Optional[datetime] = None


class ScanLogResponse(BaseModel):
    """Response schema for scan log."""
    id: UUID
    tenant_id: UUID
    device_id: UUID
    user_id: Optional[UUID] = None
    barcode: str
    scan_type: str
    scan_result: str
    warehouse_id: Optional[UUID] = None
    zone_id: Optional[UUID] = None
    bin_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    picklist_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    expected_value: Optional[str] = None
    is_match: Optional[bool] = None
    error_message: Optional[str] = None
    is_offline_scan: bool
    sync_status: str
    scanned_at: datetime

    class Config:
        from_attributes = True


class ScanValidationRequest(BaseModel):
    """Request to validate a scanned barcode."""
    barcode: str = Field(..., max_length=255)
    scan_type: ScanType
    expected_value: Optional[str] = None
    task_id: Optional[UUID] = None
    bin_id: Optional[UUID] = None


class ScanValidationResponse(BaseModel):
    """Response for scan validation."""
    is_valid: bool
    scan_result: ScanResult
    matched_entity_id: Optional[UUID] = None
    matched_entity_type: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# TASK QUEUE SCHEMAS
# ============================================================================

class TaskQueueCreate(BaseModel):
    """Schema for creating a task queue entry."""
    worker_id: UUID
    warehouse_id: UUID
    task_id: UUID
    task_type: str = Field(..., max_length=30)
    priority: int = Field(50, ge=0, le=100, description="Lower = higher priority")
    sequence: int = 0
    task_summary: Optional[Dict[str, Any]] = None
    source_bin_code: Optional[str] = Field(None, max_length=100)
    destination_bin_code: Optional[str] = Field(None, max_length=100)
    sku: Optional[str] = Field(None, max_length=100)
    product_name: Optional[str] = Field(None, max_length=255)
    quantity_required: int = 0
    device_id: Optional[UUID] = None


class TaskQueueUpdate(BaseModel):
    """Schema for updating a task queue entry."""
    status: Optional[str] = Field(None, max_length=30)
    priority: Optional[int] = Field(None, ge=0, le=100)
    sequence: Optional[int] = None
    quantity_completed: Optional[int] = None
    skip_reason: Optional[str] = Field(None, max_length=200)


class TaskQueueResponse(BaseModel):
    """Response schema for task queue entry."""
    id: UUID
    tenant_id: UUID
    worker_id: UUID
    device_id: Optional[UUID] = None
    warehouse_id: UUID
    task_id: UUID
    task_type: str
    priority: int
    sequence: int
    status: str
    task_summary: Optional[Dict[str, Any]] = None
    source_bin_code: Optional[str] = None
    destination_bin_code: Optional[str] = None
    sku: Optional[str] = None
    product_name: Optional[str] = None
    quantity_required: int
    quantity_completed: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    skipped_at: Optional[datetime] = None
    skip_reason: Optional[str] = None
    is_offline_task: bool
    sync_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkerTaskQueue(BaseModel):
    """Lightweight task queue for mobile workers."""
    tasks: List[TaskQueueResponse]
    total_tasks: int
    pending_count: int
    active_count: int
    completed_count: int


# ============================================================================
# PICK CONFIRMATION SCHEMAS
# ============================================================================

class PickConfirmationCreate(BaseModel):
    """Schema for creating a pick confirmation."""
    task_id: UUID
    picklist_id: Optional[UUID] = None
    picklist_item_id: Optional[UUID] = None
    device_id: Optional[UUID] = None
    warehouse_id: UUID
    bin_id: Optional[UUID] = None
    bin_code: Optional[str] = Field(None, max_length=100)
    product_id: Optional[UUID] = None
    sku: str = Field(..., max_length=100)
    quantity_required: int = Field(..., ge=0)
    quantity_confirmed: int = Field(..., ge=0)
    quantity_short: int = Field(0, ge=0)
    short_reason: Optional[str] = Field(None, max_length=200)
    bin_barcode_scanned: Optional[str] = Field(None, max_length=255)
    product_barcode_scanned: Optional[str] = Field(None, max_length=255)
    serial_numbers: Optional[List[str]] = None
    lot_numbers: Optional[List[str]] = None
    is_substitution: bool = False
    original_sku: Optional[str] = Field(None, max_length=100)
    substitution_reason: Optional[str] = Field(None, max_length=200)
    is_offline_confirmation: bool = False
    offline_created_at: Optional[datetime] = None
    notes: Optional[str] = None


class PickConfirmationResponse(BaseModel):
    """Response schema for pick confirmation."""
    id: UUID
    tenant_id: UUID
    task_id: UUID
    picklist_id: Optional[UUID] = None
    picklist_item_id: Optional[UUID] = None
    device_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    warehouse_id: UUID
    bin_id: Optional[UUID] = None
    bin_code: Optional[str] = None
    product_id: Optional[UUID] = None
    sku: str
    quantity_required: int
    quantity_confirmed: int
    quantity_short: int
    status: str
    short_reason: Optional[str] = None
    bin_barcode_scanned: Optional[str] = None
    bin_scan_valid: bool
    product_barcode_scanned: Optional[str] = None
    product_scan_valid: bool
    serial_numbers: Optional[List[str]] = None
    lot_numbers: Optional[List[str]] = None
    is_substitution: bool
    original_sku: Optional[str] = None
    substitution_reason: Optional[str] = None
    is_offline_confirmation: bool
    sync_status: str
    confirmed_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# OFFLINE SYNC SCHEMAS
# ============================================================================

class OfflineSyncCreate(BaseModel):
    """Schema for creating offline sync entry."""
    device_id: UUID
    entity_type: str = Field(..., max_length=50, description="SCAN_LOG, PICK_CONFIRMATION, TASK_UPDATE")
    entity_id: Optional[UUID] = None
    operation: str = Field(..., max_length=20, description="CREATE, UPDATE, DELETE")
    payload: Dict[str, Any]
    offline_created_at: datetime


class OfflineSyncBatch(BaseModel):
    """Batch of offline sync items."""
    device_id: UUID
    items: List[OfflineSyncCreate]


class OfflineSyncResponse(BaseModel):
    """Response schema for offline sync entry."""
    id: UUID
    tenant_id: UUID
    device_id: UUID
    user_id: Optional[UUID] = None
    entity_type: str
    entity_id: Optional[UUID] = None
    operation: str
    payload: Dict[str, Any]
    status: str
    retry_count: int
    max_retries: int
    last_error: Optional[str] = None
    offline_created_at: datetime
    created_at: datetime
    synced_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SyncResult(BaseModel):
    """Result of sync operation."""
    sync_id: UUID
    success: bool
    entity_type: str
    entity_id: Optional[UUID] = None
    error: Optional[str] = None


class SyncBatchResult(BaseModel):
    """Result of batch sync operation."""
    total: int
    success_count: int
    failed_count: int
    results: List[SyncResult]


# ============================================================================
# MOBILE SESSION SCHEMAS
# ============================================================================

class MobileLoginRequest(BaseModel):
    """Mobile device login request."""
    device_code: str = Field(..., max_length=50)
    username: str
    password: str
    warehouse_id: Optional[UUID] = None


class MobileLoginResponse(BaseModel):
    """Mobile login response."""
    access_token: str
    token_type: str = "bearer"
    device_id: UUID
    user_id: UUID
    warehouse_id: UUID
    worker_name: str
    permissions: List[str]
    config: Optional[Dict[str, Any]] = None


class MobileLogoutRequest(BaseModel):
    """Mobile device logout request."""
    device_id: UUID


# ============================================================================
# MOBILE DASHBOARD SCHEMAS
# ============================================================================

class MobileDashboard(BaseModel):
    """Dashboard data for mobile worker."""
    worker_id: UUID
    worker_name: str
    warehouse_id: UUID
    warehouse_name: str
    shift_status: Optional[str] = None
    clock_in_time: Optional[datetime] = None

    # Today's stats
    tasks_assigned: int = 0
    tasks_completed: int = 0
    tasks_pending: int = 0
    units_picked: int = 0
    accuracy_rate: Optional[Decimal] = None

    # Performance
    productivity_percentage: Optional[Decimal] = None

    # Alerts
    alerts: List[Dict[str, Any]] = []


# ============================================================================
# DEVICE STATS SCHEMAS
# ============================================================================

class DeviceStats(BaseModel):
    """Statistics for a mobile device."""
    device_id: UUID
    device_code: str
    total_scans_today: int
    valid_scans: int
    invalid_scans: int
    tasks_completed: int
    avg_task_time_seconds: Optional[float] = None
    last_activity: Optional[datetime] = None
    battery_level: Optional[int] = None
    is_online: bool


class WarehouseDeviceStats(BaseModel):
    """Device statistics for a warehouse."""
    warehouse_id: UUID
    total_devices: int
    online_devices: int
    offline_devices: int
    low_battery_devices: int
    devices: List[DeviceStats]
