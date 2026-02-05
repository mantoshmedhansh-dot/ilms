"""
Mobile WMS Models - Phase 5: RF Scanner & Mobile Operations.

This module implements mobile warehouse operations:
- MobileDevice: RF scanner and mobile device registration
- MobileScanLog: Barcode scan logging for audit
- MobileTaskQueue: Worker-specific task queues
- PickConfirmation: Mobile pick confirmations with validation
"""
import uuid
from datetime import datetime, timezone, date, time
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Integer, Text,
    Numeric, Date, Time, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.wms import WarehouseZone, WarehouseBin
    from app.models.user import User
    from app.models.product import Product


# ============================================================================
# ENUMS
# ============================================================================

class DeviceType(str, Enum):
    """Mobile device types."""
    RF_SCANNER = "RF_SCANNER"           # Traditional RF gun
    MOBILE_PHONE = "MOBILE_PHONE"       # Smartphone with app
    TABLET = "TABLET"                   # Tablet device
    WEARABLE = "WEARABLE"               # Smart watch/ring scanner
    VOICE_TERMINAL = "VOICE_TERMINAL"   # Voice-directed picking device


class DeviceStatus(str, Enum):
    """Device operational status."""
    ACTIVE = "ACTIVE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    LOST = "LOST"
    RETIRED = "RETIRED"


class ScanType(str, Enum):
    """Types of barcode scans."""
    PRODUCT = "PRODUCT"                 # Product barcode scan
    BIN = "BIN"                         # Bin location scan
    PALLET = "PALLET"                   # Pallet barcode
    SERIAL = "SERIAL"                   # Serial number scan
    LICENSE_PLATE = "LICENSE_PLATE"     # LPN scan
    ORDER = "ORDER"                     # Order barcode
    SHIPMENT = "SHIPMENT"               # Shipment label
    LOGIN = "LOGIN"                     # Worker badge scan
    VALIDATION = "VALIDATION"           # Validation scan


class ScanResult(str, Enum):
    """Result of scan validation."""
    VALID = "VALID"
    INVALID = "INVALID"
    MISMATCH = "MISMATCH"
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE = "DUPLICATE"


class ConfirmationStatus(str, Enum):
    """Pick confirmation status."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    SHORTED = "SHORTED"


class OfflineSyncStatus(str, Enum):
    """Offline data sync status."""
    PENDING = "PENDING"
    SYNCED = "SYNCED"
    CONFLICT = "CONFLICT"
    FAILED = "FAILED"


# ============================================================================
# MODELS
# ============================================================================

class MobileDevice(Base):
    """
    Mobile device registration for warehouse operations.

    Tracks RF scanners, mobile phones, tablets, and wearables.
    """
    __tablename__ = "mobile_devices"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'device_code', name='uq_device_code'),
        Index('ix_mobile_devices_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Device Identification
    device_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Unique device ID e.g., RF-001"
    )
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(
        String(30),
        default="RF_SCANNER",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
        nullable=False,
        index=True
    )

    # Hardware Info
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    imei: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mac_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Software Info
    os_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    app_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Assignment
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Currently assigned worker"
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Configuration
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Device-specific configuration"
    )
    scan_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Barcode scan settings"
    )

    # Battery
    battery_level: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Last known battery %"
    )
    last_battery_update: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Connectivity
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Usage Stats
    total_scans: Mapped[int] = mapped_column(Integer, default=0)
    scans_today: Mapped[int] = mapped_column(Integer, default=0)
    last_scan_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Maintenance
    last_maintenance_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_maintenance_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    maintenance_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    assigned_user: Mapped[Optional["User"]] = relationship("User")
    scan_logs: Mapped[List["MobileScanLog"]] = relationship(
        "MobileScanLog",
        back_populates="device"
    )


class MobileScanLog(Base):
    """
    Barcode scan log for audit and troubleshooting.

    Records every scan for compliance and debugging.
    """
    __tablename__ = "mobile_scan_logs"
    __table_args__ = (
        Index('ix_mobile_scan_logs_timestamp', 'scanned_at'),
        Index('ix_mobile_scan_logs_device', 'device_id', 'scanned_at'),
        Index('ix_mobile_scan_logs_barcode', 'barcode'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Device
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mobile_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # User
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Scan Details
    barcode: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    scan_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="PRODUCT, BIN, PALLET, etc."
    )
    scan_result: Mapped[str] = mapped_column(
        String(30),
        default="VALID",
        nullable=False
    )

    # Context
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_zones.id", ondelete="SET NULL"),
        nullable=True
    )
    bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )

    # Referenced Entities
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Associated task"
    )
    picklist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )

    # Expected vs Actual
    expected_value: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Expected barcode value"
    )
    is_match: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Did scan match expected?"
    )

    # Location
    gps_latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True
    )
    gps_longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True
    )

    # Error Details
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Offline Handling
    is_offline_scan: Mapped[bool] = mapped_column(Boolean, default=False)
    offline_created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    sync_status: Mapped[str] = mapped_column(
        String(30),
        default="SYNCED",
        nullable=False
    )
    synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamp
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    device: Mapped["MobileDevice"] = relationship(
        "MobileDevice",
        back_populates="scan_logs"
    )
    user: Mapped[Optional["User"]] = relationship("User")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone")
    bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
    product: Mapped[Optional["Product"]] = relationship("Product")


class MobileTaskQueue(Base):
    """
    Worker-specific mobile task queue.

    Queues tasks for mobile workers with priority ordering.
    """
    __tablename__ = "mobile_task_queues"
    __table_args__ = (
        Index('ix_mobile_task_queue_worker', 'worker_id', 'status'),
        Index('ix_mobile_task_queue_priority', 'priority', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Worker
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Device
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mobile_devices.id", ondelete="SET NULL"),
        nullable=True
    )

    # Warehouse
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Task Reference
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to warehouse_tasks"
    )
    task_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="PICK, PUTAWAY, COUNT, etc."
    )

    # Priority and Order
    priority: Mapped[int] = mapped_column(
        Integer,
        default=50,
        index=True,
        comment="Lower = higher priority"
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Order in queue"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="QUEUED",
        nullable=False,
        index=True,
        comment="QUEUED, ACTIVE, COMPLETED, SKIPPED"
    )

    # Task Details (denormalized for mobile efficiency)
    task_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Lightweight task data for offline"
    )

    # Location
    source_bin_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_bin_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Product (for pick tasks)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quantity_required: Mapped[int] = mapped_column(Integer, default=0)
    quantity_completed: Mapped[int] = mapped_column(Integer, default=0)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    skipped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    skip_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Offline Handling
    is_offline_task: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_status: Mapped[str] = mapped_column(
        String(30),
        default="SYNCED",
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    worker: Mapped["User"] = relationship("User", foreign_keys=[worker_id])
    device: Mapped[Optional["MobileDevice"]] = relationship("MobileDevice")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class PickConfirmation(Base):
    """
    Mobile pick confirmation with validation.

    Records pick confirmations from mobile devices with barcode validation.
    """
    __tablename__ = "pick_confirmations"
    __table_args__ = (
        Index('ix_pick_confirmations_task', 'task_id'),
        Index('ix_pick_confirmations_time', 'confirmed_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Task Reference
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    picklist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    picklist_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Device and User
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mobile_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Location
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_bins.id", ondelete="SET NULL"),
        nullable=True
    )
    bin_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Product
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)

    # Quantities
    quantity_required: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_confirmed: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_short: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="CONFIRMED",
        nullable=False
    )
    short_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Barcode Validation
    bin_barcode_scanned: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bin_scan_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    product_barcode_scanned: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_scan_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    # Serial Numbers (if applicable)
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Picked serial numbers"
    )
    lot_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Picked lot numbers"
    )

    # Substitution
    is_substitution: Mapped[bool] = mapped_column(Boolean, default=False)
    original_sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    substitution_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Offline Handling
    is_offline_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    offline_created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    sync_status: Mapped[str] = mapped_column(
        String(30),
        default="SYNCED",
        nullable=False
    )

    # Timestamps
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    device: Mapped[Optional["MobileDevice"]] = relationship("MobileDevice")
    user: Mapped[Optional["User"]] = relationship("User")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    bin: Mapped[Optional["WarehouseBin"]] = relationship("WarehouseBin")
    product: Mapped[Optional["Product"]] = relationship("Product")


class OfflineSyncQueue(Base):
    """
    Queue for offline data synchronization.

    Tracks pending sync items when device comes back online.
    """
    __tablename__ = "offline_sync_queue"
    __table_args__ = (
        Index('ix_offline_sync_device', 'device_id', 'status'),
        Index('ix_offline_sync_created', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Device
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mobile_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Sync Item
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="SCAN_LOG, PICK_CONFIRMATION, TASK_UPDATE"
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="CREATE, UPDATE, DELETE"
    )

    # Payload
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Offline data to sync"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    offline_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When created on device"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        comment="When received by server"
    )
    synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    device: Mapped["MobileDevice"] = relationship("MobileDevice")
    user: Mapped[Optional["User"]] = relationship("User")
