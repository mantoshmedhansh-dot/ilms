"""
D2C Customer Authentication Schemas

Request/response models for OTP-based customer authentication.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseResponseSchema
import re


class SendOTPRequest(BaseModel):
    """Request to send OTP."""
    phone: str = Field(..., description="Customer phone number (10 digits)")
    captcha_token: Optional[str] = Field(None, description="Cloudflare Turnstile CAPTCHA token")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove any spaces or dashes
        phone = re.sub(r"[\s\-]", "", v)
        # Remove country code if present
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) > 10:
            phone = phone[2:]
        # Validate length
        if not re.match(r"^[6-9]\d{9}$", phone):
            raise ValueError("Enter valid 10-digit Indian mobile number")
        return phone


class SendOTPResponse(BaseModel):
    """Response after sending OTP."""
    success: bool
    message: str
    expires_in_seconds: int = 600  # 10 minutes
    resend_in_seconds: int = 30


class VerifyOTPRequest(BaseModel):
    """Request to verify OTP."""
    phone: str = Field(..., description="Customer phone number")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        phone = re.sub(r"[\s\-]", "", v)
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) > 10:
            phone = phone[2:]
        if not re.match(r"^[6-9]\d{9}$", phone):
            raise ValueError("Enter valid 10-digit Indian mobile number")
        return phone

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        return v


class VerifyOTPResponse(BaseModel):
    """Response after OTP verification."""
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    customer: Optional["CustomerProfile"] = None
    is_new_customer: bool = False


class CustomerProfile(BaseResponseSchema):
    """Customer profile information."""
    id: str
    phone: str
    email: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    is_verified: bool = True
class CustomerAddress(BaseResponseSchema):
    """Customer address."""
    id: str
    address_type: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str = "India"
    is_default: bool = False
class UpdateProfileRequest(BaseModel):
    """Request to update customer profile."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Enter a valid email address")
        return v


class AddAddressRequest(BaseModel):
    """Request to add a new address."""
    address_type: str = "HOME"
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    address_line1: str = Field(..., min_length=5, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    landmark: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., min_length=6, max_length=6)
    country: str = "India"
    is_default: bool = False

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: str) -> str:
        if not re.match(r"^\d{6}$", v):
            raise ValueError("Enter valid 6-digit pincode")
        return v


class CustomerOrderSummary(BaseResponseSchema):
    """Summary of a customer order."""
    id: str
    order_number: str
    status: str
    total_amount: float
    created_at: datetime
    items_count: int
class CustomerOrdersResponse(BaseModel):
    """Response with customer orders."""
    orders: List[CustomerOrderSummary]
    total: int
    page: int
    size: int


class WishlistItemResponse(BaseResponseSchema):
    """Wishlist item response."""
    id: str
    product_id: str
    product_name: str
    product_slug: str
    product_image: Optional[str] = None
    product_price: float
    product_mrp: float
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    price_when_added: Optional[float] = None
    is_in_stock: bool = True
    price_dropped: bool = False
    created_at: datetime

class WishlistResponse(BaseModel):
    """Wishlist response with all items."""
    items: List[WishlistItemResponse]
    total: int


class AddToWishlistRequest(BaseModel):
    """Request to add product to wishlist."""
    product_id: str
    variant_id: Optional[str] = None


class ChangePhoneRequest(BaseModel):
    """Request to change phone number - Step 1: Send OTP to new phone."""
    new_phone: str = Field(..., description="New phone number (10 digits)")

    @field_validator("new_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        phone = re.sub(r"[\s\-]", "", v)
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) > 10:
            phone = phone[2:]
        if not re.match(r"^[6-9]\d{9}$", phone):
            raise ValueError("Enter valid 10-digit Indian mobile number")
        return phone


class VerifyPhoneChangeRequest(BaseModel):
    """Request to verify phone change - Step 2: Verify OTP for new phone."""
    new_phone: str = Field(..., description="New phone number")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")

    @field_validator("new_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        phone = re.sub(r"[\s\-]", "", v)
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) > 10:
            phone = phone[2:]
        if not re.match(r"^[6-9]\d{9}$", phone):
            raise ValueError("Enter valid 10-digit Indian mobile number")
        return phone

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        return v


# Update forward references
VerifyOTPResponse.model_rebuild()
