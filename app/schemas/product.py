from pydantic import BaseModel, Field, field_validator, computed_field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List, Any, Union
from datetime import datetime
from decimal import Decimal
import uuid

from app.models.product import ProductStatus, ProductItemType, DocumentType


# ==================== IMAGE SCHEMAS ====================

class ProductImageCreate(BaseModel):
    """Product image creation."""
    image_url: str = Field(..., max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    alt_text: Optional[str] = Field(None, max_length=255)
    is_primary: bool = False
    sort_order: int = 0


class ProductImageResponse(BaseResponseSchema):
    """Product image response."""
    id: uuid.UUID
    image_url: str
    thumbnail_url: Optional[str] = None
    alt_text: Optional[str] = None
    is_primary: bool
    sort_order: int
# ==================== SPECIFICATION SCHEMAS ====================

class ProductSpecCreate(BaseModel):
    """Product specification creation."""
    group_name: str = Field(default="General", max_length=100)
    key: str = Field(..., max_length=100)
    value: str = Field(..., max_length=500)
    sort_order: int = 0


class ProductSpecResponse(BaseResponseSchema):
    """Product specification response."""
    id: uuid.UUID
    group_name: str
    key: str
    value: str
    sort_order: int
# ==================== VARIANT SCHEMAS ====================

class ProductVariantCreate(BaseModel):
    """Product variant creation."""
    name: str = Field(..., max_length=255)
    sku: str = Field(..., max_length=50)
    attributes: Optional[dict] = None
    mrp: Optional[Decimal] = Field(None, ge=0)
    selling_price: Optional[Decimal] = Field(None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    image_url: Optional[str] = Field(None, max_length=500)
    sort_order: int = 0


class ProductVariantUpdate(BaseModel):
    """Product variant update."""
    name: Optional[str] = Field(None, max_length=255)
    attributes: Optional[dict] = None
    mrp: Optional[Decimal] = Field(None, ge=0)
    selling_price: Optional[Decimal] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ProductVariantResponse(BaseResponseSchema):
    """Product variant response."""
    id: uuid.UUID
    name: str
    sku: str
    attributes: Optional[dict] = None
    mrp: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    stock_quantity: int
    image_url: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
# ==================== DOCUMENT SCHEMAS ====================

class ProductDocumentCreate(BaseModel):
    """Product document creation."""
    title: str = Field(..., max_length=255)
    document_type: DocumentType = DocumentType.OTHER
    file_url: str = Field(..., max_length=500)
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    sort_order: int = 0


class ProductDocumentResponse(BaseResponseSchema):
    """Product document response."""
    id: uuid.UUID
    title: str
    document_type: str  # VARCHAR in DB
    file_url: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    sort_order: int
    created_at: datetime
# ==================== PRODUCT SCHEMAS ====================

class ProductBase(BaseModel):
    """Base product schema."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=280)
    sku: str = Field(..., min_length=1, max_length=50)
    model_number: Optional[str] = Field(None, max_length=100)

    # Master Product File - FG/Item Code
    fg_code: Optional[str] = Field(None, max_length=20, description="Formal product code e.g., WPRAIEL001")
    model_code: Optional[str] = Field(None, max_length=10, description="3-letter model code for barcode e.g., IEL")
    item_type: ProductItemType = Field(default=ProductItemType.FINISHED_GOODS, description="FG, SP, CO, CN, AC")

    short_description: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    features: Optional[str] = None

    category_id: uuid.UUID
    brand_id: uuid.UUID

    mrp: Decimal = Field(..., ge=0, description="Maximum Retail Price")
    selling_price: Decimal = Field(..., ge=0, description="Selling price")
    dealer_price: Optional[Decimal] = Field(None, ge=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)

    hsn_code: Optional[str] = Field(None, max_length=20)
    gst_rate: Optional[Decimal] = Field(default=18.00, ge=0, le=100)

    warranty_months: int = Field(default=12, ge=0)
    extended_warranty_available: bool = False
    warranty_terms: Optional[str] = None

    # Physical Attributes - Dimensions & Weight
    dead_weight_kg: Optional[Decimal] = Field(None, ge=0, description="Actual physical weight in kg")
    length_cm: Optional[Decimal] = Field(None, ge=0, description="Length in centimeters")
    width_cm: Optional[Decimal] = Field(None, ge=0, description="Width in centimeters")
    height_cm: Optional[Decimal] = Field(None, ge=0, description="Height in centimeters")

    min_stock_level: int = Field(default=10, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)

    is_featured: bool = False
    is_bestseller: bool = False
    is_new_arrival: bool = False
    sort_order: int = 0

    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=255)

    # NOTE: Validators moved to ProductCreate/ProductUpdate per coding standards
    # (Rule 2: Never put validators on Base schemas - they affect GET responses)


class ProductCreate(ProductBase):
    """Product creation schema."""
    status: ProductStatus = ProductStatus.DRAFT
    images: Optional[List[ProductImageCreate]] = []
    specifications: Optional[List[ProductSpecCreate]] = []
    variants: Optional[List[ProductVariantCreate]] = []
    documents: Optional[List[ProductDocumentCreate]] = []
    extra_data: Optional[dict] = None

    @field_validator("selling_price")
    @classmethod
    def selling_price_less_than_mrp(cls, v, info):
        """Validate selling price is not greater than MRP."""
        mrp = info.data.get("mrp")
        if mrp is not None and v > mrp:
            raise ValueError("Selling price cannot be greater than MRP")
        return v

    @field_validator("model_code")
    @classmethod
    def validate_model_code(cls, v):
        """Model code should be uppercase letters only."""
        if v is not None:
            return v.upper()
        return v


class ProductUpdate(BaseModel):
    """Product update schema."""
    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=280)
    model_number: Optional[str] = Field(None, max_length=100)

    # Master Product File - FG/Item Code
    fg_code: Optional[str] = Field(None, max_length=20)
    model_code: Optional[str] = Field(None, max_length=10)
    item_type: Optional[ProductItemType] = None

    short_description: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    features: Optional[str] = None

    category_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None

    mrp: Optional[Decimal] = Field(None, ge=0)
    selling_price: Optional[Decimal] = Field(None, ge=0)
    dealer_price: Optional[Decimal] = Field(None, ge=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)

    hsn_code: Optional[str] = None
    gst_rate: Optional[Decimal] = Field(None, ge=0, le=100)

    warranty_months: Optional[int] = Field(None, ge=0)
    extended_warranty_available: Optional[bool] = None
    warranty_terms: Optional[str] = None

    # Physical Attributes - Dimensions & Weight
    dead_weight_kg: Optional[Decimal] = Field(None, ge=0)
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None

    min_stock_level: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)

    status: Optional[ProductStatus] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_bestseller: Optional[bool] = None
    is_new_arrival: Optional[bool] = None
    sort_order: Optional[int] = None

    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None

    extra_data: Optional[dict] = None

    @field_validator("selling_price")
    @classmethod
    def selling_price_less_than_mrp(cls, v, info):
        """Validate selling price is not greater than MRP."""
        if v is None:
            return v
        mrp = info.data.get("mrp")
        if mrp is not None and v > mrp:
            raise ValueError("Selling price cannot be greater than MRP")
        return v

    @field_validator("model_code")
    @classmethod
    def validate_model_code(cls, v):
        """Model code should be uppercase letters only."""
        if v is not None:
            return v.upper()
        return v


class CategoryBrief(BaseResponseSchema):
    """Brief category info for product response."""
    id: uuid.UUID
    name: str
    slug: str
class BrandBrief(BaseResponseSchema):
    """Brief brand info for product response."""
    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
class WeightInfo(BaseModel):
    """Weight information including calculated fields."""
    dead_weight_kg: Optional[float] = None
    volumetric_weight_kg: float = 0.0
    chargeable_weight_kg: float = 0.0
    dimensions: dict = {}


class ProductResponse(BaseResponseSchema):
    """Product response schema."""
    id: uuid.UUID
    name: str
    slug: str
    sku: str
    model_number: Optional[str] = None

    # Master Product File - FG/Item Code
    fg_code: Optional[str] = None
    model_code: Optional[str] = None
    item_type: str = "FG"  # VARCHAR in DB

    short_description: Optional[str] = None
    description: Optional[str] = None
    features: Optional[str] = None

    category: Optional[CategoryBrief] = None
    brand: Optional[BrandBrief] = None

    mrp: Decimal
    selling_price: Decimal
    dealer_price: Optional[Decimal] = None
    discount_percentage: float

    hsn_code: Optional[str] = None
    gst_rate: Optional[Decimal] = None

    warranty_months: int
    extended_warranty_available: bool
    warranty_terms: Optional[str] = None

    # Physical Attributes - Dimensions & Weight
    dead_weight_kg: Optional[Decimal] = None
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None

    # Computed weight fields (from model properties)
    volumetric_weight_kg: Optional[float] = None
    chargeable_weight_kg: Optional[float] = None

    status: str
    is_active: bool
    is_featured: bool
    is_bestseller: bool
    is_new_arrival: bool
    sort_order: int

    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None

    images: List[ProductImageResponse] = []

    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

    # Frontend compatibility aliases for weight and dimensions
    @computed_field
    @property
    def weight(self) -> Optional[float]:
        """Alias for dead_weight_kg - frontend expects 'weight'."""
        return float(self.dead_weight_kg) if self.dead_weight_kg else None

    @computed_field
    @property
    def length(self) -> Optional[float]:
        """Alias for length_cm - frontend expects 'length'."""
        return float(self.length_cm) if self.length_cm else None

    @computed_field
    @property
    def width(self) -> Optional[float]:
        """Alias for width_cm - frontend expects 'width'."""
        return float(self.width_cm) if self.width_cm else None

    @computed_field
    @property
    def height(self) -> Optional[float]:
        """Alias for height_cm - frontend expects 'height'."""
        return float(self.height_cm) if self.height_cm else None

    @computed_field
    @property
    def volumetric_weight(self) -> Optional[float]:
        """Alias for volumetric_weight_kg - frontend expects 'volumetric_weight'."""
        return self.volumetric_weight_kg

    @computed_field
    @property
    def chargeable_weight(self) -> Optional[float]:
        """Alias for chargeable_weight_kg - frontend expects 'chargeable_weight'."""
        return self.chargeable_weight_kg

class ProductDetailResponse(ProductResponse):
    """Detailed product response with all relations."""
    specifications: List[ProductSpecResponse] = []
    variants: List[ProductVariantResponse] = []
    documents: List[ProductDocumentResponse] = []
    extra_data: Optional[dict] = None


class ProductListResponse(BaseModel):
    """Paginated product list."""
    items: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int


class ProductBriefResponse(BaseResponseSchema):
    """Brief product response for lists/dropdowns."""
    id: uuid.UUID
    name: str
    sku: str
    slug: str
    fg_code: Optional[str] = None
    model_code: Optional[str] = None
    item_type: str = "FG"  # VARCHAR in DB
    mrp: Decimal
    selling_price: Decimal
    primary_image_url: Optional[str] = None
    category_name: str
    brand_name: str
    is_active: bool
    status: str
    chargeable_weight_kg: Optional[float] = None

class MasterProductFileResponse(BaseResponseSchema):
    """Master Product File response with complete identification and weight info."""
    id: uuid.UUID
    fg_code: Optional[str] = None
    model_code: Optional[str] = None
    name: str
    sku: str
    item_type: str  # VARCHAR in DB
    category_name: str
    brand_name: str
    # Dimensions
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    # Weights
    dead_weight_kg: Optional[float] = None
    volumetric_weight_kg: float = 0.0
    chargeable_weight_kg: float = 0.0
    # Pricing
    mrp: Decimal
    selling_price: Decimal
    hsn_code: Optional[str] = None
    gst_rate: Optional[Decimal] = None
    # Status
    status: str
    is_active: bool
