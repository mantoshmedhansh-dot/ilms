"""Storefront schemas for public D2C website API."""
from pydantic import BaseModel, Field, computed_field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List


# ==================== Product Sub-schemas ====================

class StorefrontProductImage(BaseResponseSchema):
    """Product image for storefront."""
    id: str = Field(..., description="Image ID")
    image_url: str = Field(..., description="Image URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    alt_text: Optional[str] = Field(None, description="Alt text for accessibility")
    is_primary: bool = Field(False, description="Whether this is the primary image")
    sort_order: int = Field(0, description="Display order")
class StorefrontProductVariant(BaseResponseSchema):
    """Product variant for storefront."""
    id: str = Field(..., description="Variant ID")
    name: str = Field(..., description="Variant name")
    sku: str = Field(..., description="Variant SKU")
    attributes: Optional[dict] = Field(None, description="Variant attributes")
    mrp: Optional[float] = Field(None, description="Variant MRP")
    selling_price: Optional[float] = Field(None, description="Variant selling price")
    stock_quantity: Optional[int] = Field(None, description="Stock quantity")
    image_url: Optional[str] = Field(None, description="Variant image URL")
    is_active: bool = Field(True, description="Whether variant is active")
class StorefrontProductSpecification(BaseResponseSchema):
    """Product specification for storefront."""
    id: str = Field(..., description="Specification ID")
    group_name: Optional[str] = Field(None, description="Specification group")
    key: str = Field(..., description="Specification key/name")
    value: str = Field(..., description="Specification value")
    sort_order: Optional[int] = Field(0, description="Display order")
class StorefrontProductDocument(BaseResponseSchema):
    """Product document for storefront."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    document_type: str = Field(..., description="Document type")
    file_url: str = Field(..., description="Document file URL")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
class StorefrontProductResponse(BaseResponseSchema):
    """Product response for storefront."""
    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    slug: str = Field(..., description="URL slug")
    sku: str = Field(..., description="SKU code")
    short_description: Optional[str] = Field(None, description="Short description")
    description: Optional[str] = Field(None, description="Full description")
    features: Optional[str] = Field(None, description="Product features")
    mrp: float = Field(..., description="Maximum retail price")
    selling_price: Optional[float] = Field(None, description="Selling price")
    discount_percentage: Optional[float] = Field(None, description="Discount percentage")
    gst_rate: Optional[float] = Field(None, description="GST rate")
    hsn_code: Optional[str] = Field(None, description="HSN code")
    category_id: Optional[str] = Field(None, description="Category ID")
    category_name: Optional[str] = Field(None, description="Category name")
    brand_id: Optional[str] = Field(None, description="Brand ID")
    brand_name: Optional[str] = Field(None, description="Brand name")
    warranty_months: int = Field(12, description="Warranty in months")
    warranty_type: Optional[str] = Field(None, description="Warranty type")
    is_featured: bool = Field(False, description="Featured product flag")
    is_bestseller: bool = Field(False, description="Bestseller flag")
    is_new_arrival: bool = Field(False, description="New arrival flag")
    images: List[StorefrontProductImage] = Field([], description="Product images")
    variants: List[StorefrontProductVariant] = Field([], description="Product variants")
    specifications: List[StorefrontProductSpecification] = Field([], description="Product specifications")
    documents: List[StorefrontProductDocument] = Field([], description="Product documents")
    # Stock information
    in_stock: bool = Field(True, description="Whether product is in stock")
    stock_quantity: int = Field(0, description="Available stock quantity")

class StorefrontCategoryResponse(BaseResponseSchema):
    """Category response for storefront."""
    id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    slug: str = Field(..., description="URL slug")
    description: Optional[str] = Field(None, description="Category description")
    image_url: Optional[str] = Field(None, description="Category image URL")
    icon: Optional[str] = Field(None, description="Category icon")
    parent_id: Optional[str] = Field(None, description="Parent category ID")
    is_active: bool = Field(True, description="Whether category is active")
    is_featured: Optional[bool] = Field(False, description="Featured category flag")
    product_count: int = Field(0, description="Number of products in this category")
    children: List["StorefrontCategoryResponse"] = Field([], description="Child categories")
# Enable forward reference resolution
StorefrontCategoryResponse.model_rebuild()


class StorefrontBrandResponse(BaseResponseSchema):
    """Brand response for storefront."""
    id: str = Field(..., description="Brand ID")
    name: str = Field(..., description="Brand name")
    slug: str = Field(..., description="URL slug")
    description: Optional[str] = Field(None, description="Brand description")
    logo_url: Optional[str] = Field(None, description="Brand logo URL")
    is_active: bool = Field(True, description="Whether brand is active")

    # Frontend compatibility - code is alias for slug
    @computed_field
    @property
    def code(self) -> str:
        """Alias for slug - frontend expects 'code' field."""
        return self.slug

class PaginatedProductsResponse(BaseModel):
    """Paginated products response."""
    items: List[StorefrontProductResponse] = Field(..., description="Product items")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total pages")


class StorefrontCompanyInfo(BaseResponseSchema):
    """Public company info for storefront."""
    name: str = Field(..., description="Company legal name")
    trade_name: Optional[str] = Field(None, description="Trade name")
    logo_url: Optional[str] = Field(None, description="Logo URL")
    logo_small_url: Optional[str] = Field(None, description="Small logo URL")
    favicon_url: Optional[str] = Field(None, description="Favicon URL")
    email: str = Field(..., description="Contact email")
    phone: str = Field(..., description="Contact phone")
    website: Optional[str] = Field(None, description="Website URL")
    address: str = Field(..., description="Address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    pincode: str = Field(..., description="Pincode")
# ==================== Search Suggestions ====================

class SearchProductSuggestion(BaseResponseSchema):
    """Product suggestion in search results."""
    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    slug: str = Field(..., description="URL slug")
    image_url: Optional[str] = Field(None, description="Primary image URL")
    price: float = Field(..., description="Selling price")
    mrp: float = Field(..., description="MRP")
class SearchCategorySuggestion(BaseResponseSchema):
    """Category suggestion in search results."""
    id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    slug: str = Field(..., description="URL slug")
    image_url: Optional[str] = Field(None, description="Category image")
    product_count: int = Field(0, description="Number of products in category")
class SearchBrandSuggestion(BaseResponseSchema):
    """Brand suggestion in search results."""
    id: str = Field(..., description="Brand ID")
    name: str = Field(..., description="Brand name")
    slug: str = Field(..., description="URL slug")
    logo_url: Optional[str] = Field(None, description="Brand logo")
class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response with products, categories, and brands."""
    products: List[SearchProductSuggestion] = Field([], description="Product suggestions")
    categories: List[SearchCategorySuggestion] = Field([], description="Category suggestions")
    brands: List[SearchBrandSuggestion] = Field([], description="Brand suggestions")
    query: str = Field(..., description="Original search query")


# ==================== Demo Booking Schemas ====================

class DemoBookingRequest(BaseModel):
    """Request to book a product demo."""
    product_name: str = Field(..., description="Product name for demo")
    product_id: Optional[str] = Field(None, description="Product ID if available")
    customer_name: str = Field(..., description="Customer's full name")
    phone: str = Field(..., description="Customer's phone number")
    email: Optional[str] = Field(None, description="Customer's email")
    address: Optional[str] = Field(None, description="Customer's address")
    pincode: Optional[str] = Field(None, description="Customer's pincode")
    demo_type: str = Field("VIDEO", description="Demo type: VIDEO or PHONE")
    preferred_date: Optional[str] = Field(None, description="Preferred date (YYYY-MM-DD)")
    preferred_time: Optional[str] = Field(None, description="Preferred time slot")
    notes: Optional[str] = Field(None, description="Questions or notes")


class DemoBookingResponse(BaseResponseSchema):
    """Response after booking a demo."""
    success: bool = Field(..., description="Whether booking was successful")
    booking_id: str = Field(..., description="Booking ID")
    booking_number: str = Field(..., description="Booking reference number")
    message: str = Field(..., description="Confirmation message")
    estimated_callback: Optional[str] = Field(None, description="Estimated callback time")
# ==================== Exchange Calculator Schemas ====================

class ExchangeCalculateRequest(BaseModel):
    """Request to calculate exchange value."""
    brand: str = Field(..., description="Brand of old purifier")
    age_years: float = Field(..., description="Age of purifier in years")
    condition: str = Field(..., description="Condition: excellent, good, fair, poor")
    purifier_type: Optional[str] = Field(None, description="Type: RO, UV, RO+UV, etc.")


class ExchangeCalculateResponse(BaseModel):
    """Response with calculated exchange value."""
    estimated_value: int = Field(..., description="Estimated exchange value in INR")
    min_value: int = Field(..., description="Minimum possible value")
    max_value: int = Field(..., description="Maximum possible value")
    factors: dict = Field(..., description="Factors used in calculation")
    terms: List[str] = Field([], description="Exchange terms and conditions")


# ==================== Video Guide Schemas ====================

class VideoGuideResponse(BaseResponseSchema):
    """Video guide response for storefront."""
    id: str = Field(..., description="Guide ID")
    title: str = Field(..., description="Guide title")
    slug: str = Field(..., description="URL slug")
    description: Optional[str] = Field(None, description="Guide description")
    thumbnail_url: str = Field(..., description="Thumbnail image URL")
    video_url: str = Field(..., description="Video URL")
    video_type: str = Field(..., description="Video source type: YOUTUBE, VIMEO, DIRECT")
    video_id: Optional[str] = Field(None, description="Video ID for YouTube/Vimeo")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")
    category: str = Field(..., description="Guide category")
    product_name: Optional[str] = Field(None, description="Associated product name")
    view_count: int = Field(0, description="Number of views")
    is_featured: bool = Field(False, description="Featured guide flag")

class VideoGuideListResponse(BaseModel):
    """Paginated video guides response."""
    items: List[VideoGuideResponse] = Field(..., description="Video guides")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total pages")
    categories: List[str] = Field([], description="Available categories")


# ==================== AWB Tracking Schemas ====================

class TrackingEventResponse(BaseModel):
    """Single tracking event in shipment history."""
    status: str = Field(..., description="Status code")
    status_message: str = Field(..., description="Human-readable status message")
    location: Optional[str] = Field(None, description="Event location")
    remarks: Optional[str] = Field(None, description="Additional remarks")
    timestamp: str = Field(..., description="Event timestamp (ISO format)")


class AWBTrackingResponse(BaseModel):
    """Public AWB/shipment tracking response."""
    awb_number: str = Field(..., description="AWB/tracking number")
    courier_name: Optional[str] = Field(None, description="Courier/transporter name")
    status: str = Field(..., description="Current shipment status")
    status_message: str = Field(..., description="Human-readable status")
    origin_city: Optional[str] = Field(None, description="Origin city")
    destination_city: Optional[str] = Field(None, description="Destination city")
    destination_pincode: Optional[str] = Field(None, description="Destination pincode")
    shipped_at: Optional[str] = Field(None, description="Shipping timestamp")
    estimated_delivery: Optional[str] = Field(None, description="Estimated delivery date")
    delivered_at: Optional[str] = Field(None, description="Actual delivery timestamp")
    current_location: Optional[str] = Field(None, description="Current shipment location")
    tracking_url: Optional[str] = Field(None, description="External tracking URL")
    tracking_events: List[TrackingEventResponse] = Field([], description="Tracking history")
    order_number: Optional[str] = Field(None, description="Associated order number")
    payment_mode: str = Field("PREPAID", description="Payment mode: PREPAID or COD")
    cod_amount: Optional[float] = Field(None, description="COD amount if applicable")
