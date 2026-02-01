"""
Serialization Schemas for Barcode Generation in Procurement

Barcode Structure: APFSZAIEL000001 (15 characters)
- AP: Brand Prefix (Aquapurite)
- FS: Supplier Code (2 letters)
- Z: Year Code
- A: Month Code
- IEL: Model Code (3 letters)
- 000001: Serial Number (6 digits)
"""

from datetime import datetime
from typing import Optional, List, Union
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

from app.schemas.base import BaseResponseSchema


# ==================== Enums ====================

class SerialStatus(str, Enum):
    GENERATED = "generated"
    PRINTED = "printed"
    SENT_TO_VENDOR = "sent_to_vendor"
    RECEIVED = "received"
    ASSIGNED = "assigned"
    SOLD = "sold"
    RETURNED = "returned"
    DAMAGED = "damaged"
    CANCELLED = "cancelled"


class ItemType(str, Enum):
    FINISHED_GOODS = "FG"
    SPARE_PART = "SP"
    COMPONENT = "CO"


# ==================== Supplier Code Schemas ====================

class SupplierCodeCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=2, description="2-letter supplier code")
    name: str = Field(..., min_length=1, max_length=100)
    vendor_id: Optional[str] = None
    description: Optional[str] = None

    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        if not v.isalpha():
            raise ValueError('Supplier code must be 2 letters only')
        return v.upper()


class SupplierCodeUpdate(BaseModel):
    name: Optional[str] = None
    vendor_id: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierCodeResponse(BaseResponseSchema):
    """Response schema for supplier codes - inherits UUID serialization from base."""
    id: UUID
    code: str
    name: str
    vendor_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime


# ==================== Model Code Reference Schemas ====================

class ModelCodeCreate(BaseModel):
    product_id: Optional[str] = None
    product_sku: Optional[str] = None
    fg_code: str = Field(..., description="Full FG/Item code like WPRAIEL001")
    model_code: str = Field(..., min_length=2, max_length=10, description="3-letter model code for barcode")
    # item_type removed from database - ignored in creation, determined from fg_code prefix
    item_type: Optional[ItemType] = None
    description: Optional[str] = None

    @field_validator('model_code')
    @classmethod
    def validate_model_code(cls, v):
        if not v.isalpha():
            raise ValueError('Model code must be letters only')
        return v.upper()


class ModelCodeUpdate(BaseModel):
    product_id: Optional[str] = None
    product_sku: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ModelCodeResponse(BaseResponseSchema):
    """Response schema for model codes - inherits UUID serialization from base."""
    id: UUID
    product_id: Optional[UUID] = None
    product_sku: Optional[str] = None
    fg_code: str
    model_code: str
    # item_type removed from database - computed from fg_code prefix for backward compatibility
    item_type: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    @model_validator(mode='after')
    def compute_item_type(self):
        # Compute item_type from fg_code prefix if not set
        if not self.item_type:
            fg_code = self.fg_code or ''
            if fg_code.upper().startswith('SP'):
                self.item_type = 'SP'
            else:
                self.item_type = 'FG'  # Default to FG for water purifiers (WP prefix)
        return self


# ==================== Serial Generation Schemas ====================

class GenerateSerialsRequest(BaseModel):
    """Request to generate serial numbers for a PO"""
    po_id: Union[UUID, str] = Field(..., description="Purchase Order ID")
    supplier_code: str = Field(..., min_length=2, max_length=2, description="2-letter supplier code")
    items: List["GenerateSerialItem"] = Field(..., description="Items to generate serials for")

    @field_validator('supplier_code')
    @classmethod
    def validate_supplier_code(cls, v):
        return v.upper()


class GenerateSerialItem(BaseModel):
    """Individual item in serial generation request"""
    po_item_id: Optional[Union[UUID, str]] = None
    product_id: Optional[Union[UUID, str]] = None
    product_sku: Optional[str] = None
    model_code: str = Field(..., description="3-letter model code")
    quantity: int = Field(..., ge=1, le=10000, description="Number of serials to generate")
    item_type: ItemType = ItemType.FINISHED_GOODS

    @field_validator('model_code')
    @classmethod
    def validate_model_code(cls, v):
        return v.upper()


class GenerateSerialsResponse(BaseResponseSchema):
    """Response after generating serials - inherits UUID serialization from base."""
    po_id: UUID
    supplier_code: str
    total_generated: int
    items: List["GeneratedSerialSummary"]
    barcodes: List[str]


class GeneratedSerialSummary(BaseModel):
    """Summary of generated serials per item"""
    model_code: str
    quantity: int
    start_serial: int
    end_serial: int
    start_barcode: str
    end_barcode: str


# ==================== PO Serial Schemas ====================

class POSerialResponse(BaseResponseSchema):
    """Response schema for PO serials - inherits UUID serialization from base."""
    id: UUID
    po_id: UUID
    po_item_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    product_sku: Optional[str] = None
    model_code: str
    item_type: ItemType
    brand_prefix: str
    supplier_code: str
    year_code: str
    month_code: str
    serial_number: int
    barcode: str
    status: str
    grn_id: Optional[UUID] = None
    received_at: Optional[datetime] = None
    stock_item_id: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    order_id: Optional[UUID] = None
    sold_at: Optional[datetime] = None
    warranty_start_date: Optional[datetime] = None
    warranty_end_date: Optional[datetime] = None
    created_at: datetime


class POSerialsListResponse(BaseResponseSchema):
    """List of serials for a PO - inherits UUID serialization from base."""
    po_id: UUID
    total: int
    by_status: dict
    serials: List[POSerialResponse]


# ==================== Serial Scan/Validation Schemas ====================

class ScanSerialRequest(BaseModel):
    """Request to scan/validate a barcode during GRN"""
    barcode: str = Field(..., min_length=14, max_length=20)
    grn_id: str
    grn_item_id: Optional[str] = None


class ScanSerialResponse(BaseModel):
    """Response after scanning a serial"""
    barcode: str
    is_valid: bool
    status: str
    message: str
    serial_details: Optional[POSerialResponse] = None


class BulkScanRequest(BaseModel):
    """Bulk scan multiple barcodes"""
    grn_id: str
    barcodes: List[str]


class BulkScanResponse(BaseModel):
    """Response for bulk scan"""
    grn_id: str
    total_scanned: int
    valid_count: int
    invalid_count: int
    results: List[ScanSerialResponse]


# ==================== Serial Lookup Schemas ====================

class SerialLookupResponse(BaseModel):
    """Full details of a serial by barcode"""
    barcode: str
    found: bool
    serial: Optional[POSerialResponse] = None
    po_number: Optional[str] = None
    vendor_name: Optional[str] = None
    product_name: Optional[str] = None
    current_location: Optional[str] = None  # Warehouse name if in stock
    customer_name: Optional[str] = None  # If sold
    warranty_status: Optional[str] = None


# ==================== Sequence Status Schemas ====================

class SequenceStatusRequest(BaseModel):
    """Request to check sequence status"""
    model_code: str
    supplier_code: str
    year_code: Optional[str] = None  # If not provided, uses current year
    month_code: Optional[str] = None  # If not provided, uses current month


class SequenceStatusResponse(BaseModel):
    """Current status of a serial sequence"""
    model_code: str
    supplier_code: str
    year_code: str
    month_code: str
    last_serial: int
    next_serial: int
    total_generated: int
    next_barcode_preview: str


# ==================== Export Schemas ====================

class ExportSerialsRequest(BaseModel):
    """Request to export serials"""
    po_id: str
    format: str = Field(default="csv", pattern="^(csv|pdf|xlsx)$")
    include_qr: bool = False


class ExportSerialsResponse(BaseModel):
    """Response with export file info"""
    po_id: str
    format: str
    total_serials: int
    file_url: str
    generated_at: datetime


# ==================== Code Generation Preview ====================

class CodePreviewRequest(BaseModel):
    """Request to preview generated codes without saving"""
    supplier_code: str = Field(..., min_length=2, max_length=2)
    model_code: str = Field(..., min_length=2, max_length=10)
    quantity: int = Field(default=5, ge=1, le=100)

    @field_validator('supplier_code', 'model_code')
    @classmethod
    def validate_codes(cls, v):
        return v.upper()


class CodePreviewResponse(BaseModel):
    """Preview of codes that would be generated"""
    supplier_code: str
    model_code: str
    year_code: str
    month_code: str
    current_last_serial: int
    preview_barcodes: List[str]


# ==================== FG Code Generation ====================

class FGCodeGenerateRequest(BaseModel):
    """Generate a new FG Code for a product"""
    category_code: str = Field(..., min_length=2, max_length=2, description="WP=Water Purifier")
    subcategory_code: str = Field(..., min_length=1, max_length=1, description="R=RO")
    brand_code: str = Field(..., min_length=1, max_length=1, description="A=Aquapurite")
    model_name: str = Field(..., min_length=2, max_length=10, description="Model name like IELITZ")

    @field_validator('category_code', 'subcategory_code', 'brand_code')
    @classmethod
    def validate_codes(cls, v):
        return v.upper()


class FGCodeGenerateResponse(BaseModel):
    """Generated FG Code"""
    fg_code: str  # WPRAIEL001
    model_code: str  # IEL (extracted for barcode)
    description: str
    next_available_number: int


# ==================== Create Product with Codes ====================

class CreateProductWithCodeRequest(BaseModel):
    """
    Create a new product with auto-generated codes from Serialization section.
    This is the master product creation flow where codes are generated first.
    """
    # Item Type
    item_type: ItemType = Field(..., description="FG=Finished Goods, SP=Spare Parts")

    # Code Components for FG Code generation
    category_code: str = Field(..., min_length=2, max_length=2, description="Category code (e.g., WP=Water Purifier, SP=Spare Parts)")
    subcategory_code: str = Field(..., min_length=1, max_length=2, description="Subcategory code (e.g., R=RO, SD=Sediment)")
    brand_code: str = Field(..., min_length=1, max_length=1, description="Brand code (e.g., A=Aquapurite)")
    model_code: str = Field(..., min_length=3, max_length=3, description="3-char model code for barcode (e.g., IEL)")

    # Product Details
    name: str = Field(..., min_length=2, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")

    # Category and Brand (existing IDs from database)
    category_id: str = Field(..., description="Category ID from categories table")
    brand_id: str = Field(..., description="Brand ID from brands table")

    # Pricing
    mrp: float = Field(..., gt=0, description="Maximum Retail Price")
    selling_price: Optional[float] = Field(None, description="Selling price (defaults to MRP)")
    cost_price: Optional[float] = Field(None, description="Cost price")

    # Tax
    hsn_code: Optional[str] = Field(None, description="HSN code for GST")
    gst_rate: float = Field(default=18.0, description="GST rate percentage")

    # Warranty
    warranty_months: int = Field(default=12, description="Warranty period in months")

    @field_validator('category_code', 'subcategory_code', 'brand_code', 'model_code')
    @classmethod
    def validate_codes(cls, v):
        if not v.isalpha():
            raise ValueError('Code must contain only letters')
        return v.upper()


class CreateProductWithCodeResponse(BaseModel):
    """Response after creating product with auto-generated codes"""
    success: bool
    message: str

    # Generated Codes
    fg_code: str  # Full FG/Item code: WPRAIEL001 or SPSDFSD001
    model_code: str  # 3-char code: IEL or SDF
    product_sku: str  # Same as fg_code

    # Product Details
    product_id: str
    product_name: str
    item_type: ItemType

    # Model Code Reference
    model_code_reference_id: str

    # Barcode Preview
    barcode_format: str  # Shows what barcode will look like
    barcode_example: str  # Example: APFSAAIEL00000001


# Forward references
GenerateSerialsRequest.model_rebuild()
GenerateSerialsResponse.model_rebuild()
