"""Pydantic schemas for Fixed Assets module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema

from app.models.fixed_assets import (
    DepreciationMethod, AssetStatus, TransferStatus, MaintenanceStatus
)


# ==================== Asset Category Schemas ====================

class AssetCategoryBase(BaseModel):
    """Base schema for Asset Category."""
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    depreciation_method: DepreciationMethod = DepreciationMethod.SLM
    depreciation_rate: Decimal = Field(..., ge=0, le=100)
    useful_life_years: int = Field(..., ge=1)
    asset_account_id: Optional[UUID] = None
    depreciation_account_id: Optional[UUID] = None
    expense_account_id: Optional[UUID] = None


class AssetCategoryCreate(AssetCategoryBase):
    """Schema for creating Asset Category."""
    pass


class AssetCategoryUpdate(BaseModel):
    """Schema for updating Asset Category."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    depreciation_method: Optional[DepreciationMethod] = None
    depreciation_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    useful_life_years: Optional[int] = Field(None, ge=1)
    asset_account_id: Optional[UUID] = None
    depreciation_account_id: Optional[UUID] = None
    expense_account_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class AssetCategoryResponse(BaseResponseSchema):
    """Response schema for Asset Category."""
    id: UUID
    is_active: bool
    asset_count: int = 0
    created_at: datetime
    updated_at: datetime


class AssetCategoryListResponse(BaseModel):
    """Response for listing Asset Categories."""
    items: List[AssetCategoryResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Asset Schemas ====================

class AssetBase(BaseModel):
    """Base schema for Asset."""
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category_id: UUID

    # Serial/Model
    serial_number: Optional[str] = Field(None, max_length=100)
    model_number: Optional[str] = Field(None, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)

    # Location
    warehouse_id: Optional[UUID] = None
    location_details: Optional[str] = Field(None, max_length=200)
    custodian_employee_id: Optional[UUID] = None
    department_id: Optional[UUID] = None

    # Purchase
    purchase_date: date
    purchase_price: Decimal = Field(..., ge=0)
    purchase_invoice_no: Optional[str] = Field(None, max_length=50)
    vendor_id: Optional[UUID] = None
    po_number: Optional[str] = Field(None, max_length=50)

    # Capitalization
    capitalization_date: date
    installation_cost: Decimal = Field(Decimal("0"), ge=0)
    other_costs: Decimal = Field(Decimal("0"), ge=0)

    # Depreciation (optional overrides)
    depreciation_method: Optional[DepreciationMethod] = None
    depreciation_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    useful_life_years: Optional[int] = Field(None, ge=1)
    salvage_value: Decimal = Field(Decimal("0"), ge=0)

    # Warranty
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    warranty_details: Optional[str] = None

    # Insurance
    insured: bool = False
    insurance_policy_no: Optional[str] = Field(None, max_length=50)
    insurance_value: Optional[Decimal] = Field(None, ge=0)
    insurance_expiry: Optional[date] = None

    notes: Optional[str] = None


class AssetCreate(AssetBase):
    """Schema for creating Asset."""
    pass


class AssetUpdate(BaseModel):
    """Schema for updating Asset."""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None

    serial_number: Optional[str] = Field(None, max_length=100)
    model_number: Optional[str] = Field(None, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)

    warehouse_id: Optional[UUID] = None
    location_details: Optional[str] = Field(None, max_length=200)
    custodian_employee_id: Optional[UUID] = None
    department_id: Optional[UUID] = None

    depreciation_method: Optional[DepreciationMethod] = None
    depreciation_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    useful_life_years: Optional[int] = Field(None, ge=1)
    salvage_value: Optional[Decimal] = Field(None, ge=0)

    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    warranty_details: Optional[str] = None

    insured: Optional[bool] = None
    insurance_policy_no: Optional[str] = Field(None, max_length=50)
    insurance_value: Optional[Decimal] = Field(None, ge=0)
    insurance_expiry: Optional[date] = None

    notes: Optional[str] = None


class AssetResponse(BaseResponseSchema):
    """Response schema for Asset (list view)."""
    id: UUID
    asset_code: str
    name: str
    description: Optional[str] = None
    category_id: UUID
    category_name: Optional[str] = None

    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None

    warehouse_name: Optional[str] = None
    department_name: Optional[str] = None
    custodian_name: Optional[str] = None

    purchase_date: date
    purchase_price: Decimal
    capitalized_value: Decimal
    accumulated_depreciation: Decimal
    current_book_value: Decimal

    status: str
    created_at: datetime
    updated_at: datetime


class AssetDetailResponse(AssetResponse):
    """Detailed response schema for Asset."""
    model_number: Optional[str] = None
    warehouse_id: Optional[UUID] = None
    location_details: Optional[str] = None
    custodian_employee_id: Optional[UUID] = None
    department_id: Optional[UUID] = None

    purchase_invoice_no: Optional[str] = None
    vendor_id: Optional[UUID] = None
    vendor_name: Optional[str] = None
    po_number: Optional[str] = None

    capitalization_date: date
    installation_cost: Decimal
    other_costs: Decimal

    depreciation_method: Optional[DepreciationMethod] = None
    depreciation_rate: Optional[Decimal] = None
    useful_life_years: Optional[int] = None
    salvage_value: Decimal
    last_depreciation_date: Optional[date] = None

    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    warranty_details: Optional[str] = None

    insured: bool
    insurance_policy_no: Optional[str] = None
    insurance_value: Optional[Decimal] = None
    insurance_expiry: Optional[date] = None

    disposal_date: Optional[date] = None
    disposal_price: Optional[Decimal] = None
    disposal_reason: Optional[str] = None
    gain_loss_on_disposal: Optional[Decimal] = None

    documents: Optional[dict] = None
    images: Optional[dict] = None
    notes: Optional[str] = None


class AssetListResponse(BaseModel):
    """Response for listing Assets."""
    items: List[AssetResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Depreciation Schemas ====================

class DepreciationRunRequest(BaseModel):
    """Request to run depreciation for a period."""
    period_date: date
    financial_year: str = Field(..., max_length=10)
    asset_ids: Optional[List[UUID]] = None  # If None, process all active assets


class DepreciationEntryResponse(BaseResponseSchema):
    """Response schema for Depreciation Entry."""
    id: UUID
    asset_id: UUID
    asset_code: Optional[str] = None
    asset_name: Optional[str] = None

    period_date: date
    financial_year: str

    opening_book_value: Decimal
    depreciation_method: DepreciationMethod
    depreciation_rate: Decimal
    depreciation_amount: Decimal
    closing_book_value: Decimal
    accumulated_depreciation: Decimal

    is_posted: bool
    journal_entry_id: Optional[UUID] = None
    processed_by_name: Optional[str] = None
    processed_at: Optional[datetime] = None

    created_at: datetime


class DepreciationListResponse(BaseModel):
    """Response for listing Depreciation Entries."""
    items: List[DepreciationEntryResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Asset Transfer Schemas ====================

class AssetTransferCreate(BaseModel):
    """Schema for creating Asset Transfer."""
    asset_id: UUID
    to_warehouse_id: Optional[UUID] = None
    to_department_id: Optional[UUID] = None
    to_custodian_id: Optional[UUID] = None
    to_location_details: Optional[str] = Field(None, max_length=200)
    transfer_date: date
    reason: Optional[str] = None


class AssetTransferResponse(BaseResponseSchema):
    """Response schema for Asset Transfer."""
    id: UUID
    transfer_number: str
    asset_id: UUID
    asset_code: Optional[str] = None
    asset_name: Optional[str] = None

    from_warehouse_name: Optional[str] = None
    from_department_name: Optional[str] = None
    from_custodian_name: Optional[str] = None
    from_location_details: Optional[str] = None

    to_warehouse_name: Optional[str] = None
    to_department_name: Optional[str] = None
    to_custodian_name: Optional[str] = None
    to_location_details: Optional[str] = None

    transfer_date: date
    reason: Optional[str] = None
    status: str

    requested_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime


class AssetTransferListResponse(BaseModel):
    """Response for listing Asset Transfers."""
    items: List[AssetTransferResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Asset Maintenance Schemas ====================

class AssetMaintenanceCreate(BaseModel):
    """Schema for creating Asset Maintenance."""
    asset_id: UUID
    maintenance_type: str = Field(..., max_length=50)
    description: str
    scheduled_date: date
    estimated_cost: Decimal = Field(Decimal("0"), ge=0)
    vendor_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None


class AssetMaintenanceUpdate(BaseModel):
    """Schema for updating Asset Maintenance."""
    description: Optional[str] = None
    scheduled_date: Optional[date] = None
    started_date: Optional[date] = None
    completed_date: Optional[date] = None
    estimated_cost: Optional[Decimal] = Field(None, ge=0)
    actual_cost: Optional[Decimal] = Field(None, ge=0)
    vendor_id: Optional[UUID] = None
    vendor_invoice_no: Optional[str] = Field(None, max_length=50)
    status: Optional[MaintenanceStatus] = None
    findings: Optional[str] = None
    parts_replaced: Optional[str] = None
    recommendations: Optional[str] = None
    assigned_to: Optional[UUID] = None


class AssetMaintenanceResponse(BaseResponseSchema):
    """Response schema for Asset Maintenance."""
    id: UUID
    maintenance_number: str
    asset_id: UUID
    asset_code: Optional[str] = None
    asset_name: Optional[str] = None

    maintenance_type: str
    description: str

    scheduled_date: date
    started_date: Optional[date] = None
    completed_date: Optional[date] = None

    estimated_cost: Decimal
    actual_cost: Decimal

    vendor_name: Optional[str] = None
    vendor_invoice_no: Optional[str] = None

    status: str

    findings: Optional[str] = None
    parts_replaced: Optional[str] = None
    recommendations: Optional[str] = None

    assigned_to_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class AssetMaintenanceListResponse(BaseModel):
    """Response for listing Asset Maintenance."""
    items: List[AssetMaintenanceResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Asset Disposal Schemas ====================

class AssetDisposeRequest(BaseModel):
    """Request to dispose an asset."""
    disposal_date: date
    disposal_price: Decimal = Field(Decimal("0"), ge=0)
    disposal_reason: str


# ==================== Dashboard Schemas ====================

class FixedAssetsDashboard(BaseModel):
    """Fixed Assets Dashboard statistics."""
    total_assets: int
    active_assets: int
    disposed_assets: int
    under_maintenance: int

    total_capitalized_value: Decimal
    total_accumulated_depreciation: Decimal
    total_current_book_value: Decimal

    monthly_depreciation: Decimal
    ytd_depreciation: Decimal

    pending_maintenance: int
    pending_transfers: int

    # By category
    category_wise: List[dict]

    # Assets expiring warranty
    warranty_expiring_soon: int

    # Insurance expiring
    insurance_expiring_soon: int


# ==================== Report Schemas ====================

class DepreciationScheduleReport(BaseModel):
    """Depreciation schedule report for an asset."""
    asset_id: UUID
    asset_code: str
    asset_name: str
    category_name: str

    capitalized_value: Decimal
    salvage_value: Decimal
    depreciable_amount: Decimal

    depreciation_method: DepreciationMethod
    depreciation_rate: Decimal
    useful_life_years: int

    schedule: List[dict]  # [{year, opening, depreciation, closing}]


class AssetRegisterReport(BaseModel):
    """Asset register report entry."""
    asset_code: str
    asset_name: str
    category_name: str

    purchase_date: date
    capitalization_date: date
    purchase_price: Decimal
    capitalized_value: Decimal

    depreciation_method: str
    depreciation_rate: Decimal

    accumulated_depreciation: Decimal
    current_book_value: Decimal

    location: Optional[str] = None
    department: Optional[str] = None
    custodian: Optional[str] = None

    status: AssetStatus
