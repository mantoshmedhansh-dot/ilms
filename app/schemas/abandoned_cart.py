"""
Abandoned Cart Pydantic Schemas

Request/Response schemas for cart persistence and recovery APIs.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema


# ==================== Enums ====================

class CartStatus(str, Enum):
    """Cart status enumeration."""
    ACTIVE = "ACTIVE"
    ABANDONED = "ABANDONED"
    RECOVERED = "RECOVERED"
    CONVERTED = "CONVERTED"
    EXPIRED = "EXPIRED"


class RecoveryChannel(str, Enum):
    """Recovery notification channel."""
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"


class RecoveryStatus(str, Enum):
    """Recovery attempt status."""
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    CONVERTED = "CONVERTED"
    FAILED = "FAILED"
    BOUNCED = "BOUNCED"


# ==================== Cart Item Schemas ====================

class CartItemSync(BaseModel):
    """Cart item for syncing."""
    product_id: str
    product_name: str
    sku: str
    quantity: int = Field(ge=1)
    price: Decimal = Field(ge=0)
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    image_url: Optional[str] = None


# ==================== Request Schemas ====================

class CartSyncRequest(BaseModel):
    """Request to sync cart to backend."""
    session_id: str = Field(..., description="Browser session ID")
    items: List[CartItemSync]
    subtotal: Decimal = Field(ge=0)
    tax_amount: Decimal = Field(ge=0, default=Decimal("0"))
    shipping_amount: Decimal = Field(ge=0, default=Decimal("0"))
    discount_amount: Decimal = Field(ge=0, default=Decimal("0"))
    total_amount: Decimal = Field(ge=0)
    coupon_code: Optional[str] = None

    # Contact info (optional, captured during checkout)
    email: Optional[str] = None
    phone: Optional[str] = None
    customer_name: Optional[str] = None

    # Checkout progress
    checkout_step: Optional[str] = None
    shipping_address: Optional[dict] = None
    selected_payment_method: Optional[str] = None

    # Analytics
    source: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer_url: Optional[str] = None

    # Device info
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    device_fingerprint: Optional[str] = None


class CartRecoverRequest(BaseModel):
    """Request to recover an abandoned cart."""
    token: str = Field(..., description="Recovery token from email link")


class RecoveryEmailTriggerRequest(BaseModel):
    """Request to manually trigger recovery emails (admin)."""
    cart_id: UUID
    channel: RecoveryChannel = RecoveryChannel.EMAIL
    discount_code: Optional[str] = None
    discount_value: Optional[Decimal] = None


# ==================== Response Schemas ====================

class CartSyncResponse(BaseResponseSchema):
    """Response after syncing cart."""
    cart_id: UUID
    session_id: str
    status: str
    items_count: int
    total_amount: Decimal
    recovery_token: Optional[str] = None
    message: str = "Cart synced successfully"


class CartItemResponse(BaseResponseSchema):
    """Cart item in response."""
    product_id: str
    product_name: str
    sku: str
    quantity: int
    price: Decimal
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    image_url: Optional[str] = None


class RecoveredCartResponse(BaseResponseSchema):
    """Response when recovering a cart."""
    cart_id: UUID
    items: List[CartItemResponse]
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    coupon_code: Optional[str] = None
    shipping_address: Optional[dict] = None
    message: str = "Cart recovered successfully"


class AbandonedCartSummary(BaseResponseSchema):
    """Summary of abandoned cart for admin list."""
    id: UUID
    customer_id: Optional[UUID]
    customer_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    status: str
    items_count: int
    total_amount: Decimal
    checkout_step: Optional[str]
    created_at: datetime
    last_activity_at: datetime
    abandoned_at: Optional[datetime]
    recovery_attempts: int
    source: Optional[str]
    device_type: Optional[str]


class AbandonedCartDetail(AbandonedCartSummary):
    """Detailed abandoned cart for admin."""
    session_id: Optional[str]
    items: List[dict]
    shipping_address: Optional[dict]
    coupon_code: Optional[str]
    utm_source: Optional[str]
    utm_medium: Optional[str]
    utm_campaign: Optional[str]
    referrer_url: Optional[str]
    converted_order_id: Optional[UUID]
    converted_at: Optional[datetime]
    recovery_emails: List["RecoveryEmailResponse"]


class RecoveryEmailResponse(BaseResponseSchema):
    """Recovery email/notification record."""
    id: UUID
    sequence_number: int
    channel: str
    status: str
    recipient: str
    template_used: str
    subject: Optional[str]
    discount_code: Optional[str]
    scheduled_at: datetime
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]


# ==================== Analytics Schemas ====================

class AbandonedCartStats(BaseModel):
    """Abandoned cart analytics."""
    total_abandoned: int
    total_recovered: int
    total_converted: int
    recovery_rate: float
    conversion_rate: float
    total_value_abandoned: Decimal
    total_value_recovered: Decimal
    avg_cart_value: Decimal
    avg_items_per_cart: float
    top_abandoned_products: List[dict]
    abandonment_by_checkout_step: dict
    abandonment_by_device: dict
    abandonment_by_source: dict
    period_start: datetime
    period_end: datetime


class RecoveryPerformance(BaseModel):
    """Recovery email performance metrics."""
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_converted: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    conversion_rate: float
    revenue_recovered: Decimal
    by_sequence: List[dict]
    by_channel: dict


# Update forward references
AbandonedCartDetail.model_rebuild()
