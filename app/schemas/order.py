from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid

from app.models.order import OrderStatus, PaymentStatus, PaymentMethod, OrderSource
from app.schemas.customer import CustomerBrief, AddressResponse
from app.schemas.base import BaseResponseSchema


# ==================== ORDER ITEM SCHEMAS ====================

class OrderItemCreate(BaseModel):
    """Order item creation schema."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    quantity: int = Field(..., ge=1)
    unit_price: Optional[Decimal] = Field(None, ge=0)  # Override price if needed


class OrderItemResponse(BaseResponseSchema):
    """Order item response schema."""
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    product_name: str
    product_sku: str
    variant_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    unit_mrp: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    hsn_code: Optional[str] = None
    warranty_months: int
    serial_number: Optional[str] = None
    created_at: datetime

    # Frontend compatibility aliases
    @computed_field
    @property
    def discount(self) -> Decimal:
        """Alias for discount_amount - frontend expects 'discount'."""
        return self.discount_amount

    @computed_field
    @property
    def tax(self) -> Decimal:
        """Alias for tax_amount - frontend expects 'tax'."""
        return self.tax_amount

    @computed_field
    @property
    def total(self) -> Decimal:
        """Alias for total_amount - frontend expects 'total'."""
        return self.total_amount
# ==================== PAYMENT SCHEMAS ====================

class PaymentCreate(BaseModel):
    """Payment creation schema."""
    amount: Decimal = Field(..., ge=0)
    method: PaymentMethod
    transaction_id: Optional[str] = None
    gateway: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseResponseSchema):
    """Payment response schema."""
    id: uuid.UUID
    amount: Decimal
    method: str  # VARCHAR in DB
    status: str
    transaction_id: Optional[str] = None
    gateway: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
# ==================== STATUS HISTORY SCHEMAS ====================

class StatusHistoryResponse(BaseResponseSchema):
    """Order status history response."""
    id: uuid.UUID
    from_status: Optional[str] = None  # VARCHAR in DB
    to_status: str  # VARCHAR in DB
    changed_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime
# ==================== INVOICE SCHEMAS ====================

class InvoiceResponse(BaseResponseSchema):
    """Invoice response schema."""
    id: uuid.UUID
    invoice_number: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    pdf_url: Optional[str] = None
    invoice_date: datetime
    due_date: Optional[datetime] = None
    is_cancelled: bool
    created_at: datetime
# ==================== ORDER SCHEMAS ====================

class AddressInput(BaseModel):
    """Address input for order (can be existing address ID or new address data)."""
    address_id: Optional[uuid.UUID] = None
    # Or provide full address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class OrderCreate(BaseModel):
    """Order creation schema."""
    customer_id: uuid.UUID
    source: OrderSource = OrderSource.WEBSITE
    channel_id: Optional[uuid.UUID] = None  # Sales channel for channel-specific pricing
    items: List[OrderItemCreate] = Field(..., min_length=1)
    shipping_address: AddressInput
    billing_address: Optional[AddressInput] = None
    payment_method: PaymentMethod = PaymentMethod.COD
    discount_code: Optional[str] = None
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    region_id: Optional[uuid.UUID] = None
    customer_segment: Optional[str] = None  # For segment-based pricing (VIP, DEALER, etc.)
    partner_code: Optional[str] = None  # Community Partner referral code for commission attribution


class OrderUpdate(BaseModel):
    """Order update schema."""
    status: Optional[OrderStatus] = None
    payment_method: Optional[PaymentMethod] = None
    expected_delivery_date: Optional[datetime] = None
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Order status update schema."""
    status: OrderStatus
    notes: Optional[str] = None


class OrderResponse(BaseResponseSchema):
    """Order response schema."""
    id: uuid.UUID
    order_number: str
    customer: Optional[CustomerBrief] = None
    status: str
    source: str
    channel: Optional[str] = None  # Sales channel (D2C, B2B, etc.)
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    discount_code: Optional[str] = None
    payment_method: str  # VARCHAR in DB
    payment_status: str  # VARCHAR in DB
    amount_paid: Decimal
    balance_due: Decimal
    shipping_address: dict
    billing_address: Optional[dict] = None
    expected_delivery_date: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    customer_notes: Optional[str] = None
    item_count: int
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None

class OrderDetailResponse(OrderResponse):
    """Detailed order response with items and history."""
    items: List[OrderItemResponse] = []
    status_history: List[StatusHistoryResponse] = []
    payments: List[PaymentResponse] = []
    invoice: Optional[InvoiceResponse] = None
    internal_notes: Optional[str] = None


class OrderListResponse(BaseModel):
    """Paginated order list."""
    items: List[OrderResponse]
    total: int
    page: int
    size: int
    pages: int


class OrderSummary(BaseModel):
    """Order summary statistics."""
    total_orders: int
    total_customers: int = 0
    pending_orders: int
    processing_orders: int
    shipped_orders: int = 0
    delivered_orders: int
    cancelled_orders: int
    shipments_in_transit: int = 0
    total_revenue: Decimal
    average_order_value: Decimal
    orders_change: float = 0
    revenue_change: float = 0
    customers_change: float = 0


# ==================== D2C ORDER SCHEMAS ====================

class D2CAddressInfo(BaseModel):
    """Address info for D2C orders - matches frontend ShippingAddress type."""
    full_name: str = Field(..., description="Contact full name")
    phone: str = Field(..., description="Contact phone")
    email: Optional[str] = Field(None, description="Contact email")
    address_line1: str = Field(..., description="Address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    pincode: str = Field(..., pattern=r"^\d{6}$", description="6-digit pincode")
    country: str = Field("India", description="Country")


class D2COrderItem(BaseModel):
    """Item for D2C order - matches frontend D2COrderItem type."""
    product_id: uuid.UUID = Field(..., description="Product ID")
    sku: str = Field(..., description="Product SKU")
    name: str = Field(..., description="Product name")
    quantity: int = Field(..., ge=1, description="Quantity")
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    mrp: Optional[Decimal] = Field(None, ge=0, description="MRP - defaults to unit_price if not provided")
    tax_rate: Optional[Decimal] = Field(Decimal("18"), ge=0, le=100, description="Tax rate percentage")
    discount: Optional[Decimal] = Field(Decimal("0"), ge=0, description="Discount amount")


class D2COrderCreate(BaseModel):
    """D2C order creation - matches frontend D2COrderRequest type."""
    # Customer info (flat fields from frontend)
    customer_name: str = Field(..., min_length=2, description="Customer full name")
    customer_phone: str = Field(..., pattern=r"^\d{10}$", description="10-digit phone number")
    customer_email: Optional[str] = Field(None, description="Customer email")

    # Address
    shipping_address: D2CAddressInfo = Field(..., description="Shipping address")

    # Order items
    items: List[D2COrderItem] = Field(..., min_length=1, description="Order items")

    # Payment
    payment_method: str = Field("COD", description="Payment method: RAZORPAY or COD")

    # Amounts
    subtotal: Decimal = Field(..., description="Subtotal before tax/shipping")
    tax_amount: Optional[Decimal] = Field(Decimal("0"), description="Tax amount")
    shipping_amount: Decimal = Field(Decimal("0"), description="Shipping amount")
    discount_amount: Decimal = Field(Decimal("0"), description="Discount amount")
    coupon_code: Optional[str] = Field(None, description="Applied coupon code")
    total_amount: Decimal = Field(..., description="Total amount")

    # Optional
    notes: Optional[str] = Field(None, description="Order notes")

    # Community Partner Attribution
    partner_code: Optional[str] = Field(None, description="Partner referral code for attribution")


class D2COrderResponse(BaseModel):
    """Simple response for D2C order."""
    id: uuid.UUID = Field(..., description="Order ID")
    order_number: str = Field(..., description="Order number")
    total_amount: Decimal = Field(..., description="Total amount")
    status: str = Field(..., description="Order status")
    # Debug field - remove after troubleshooting
    allocation_failure_reason: Optional[str] = Field(None, description="DEBUG: Reason allocation failed")
