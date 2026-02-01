"""Payment schemas for Razorpay API requests/responses."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid


class CreatePaymentOrderRequest(BaseModel):
    """API request to create a payment order."""
    order_id: uuid.UUID = Field(..., description="Internal order ID")
    amount: float = Field(..., gt=0, description="Amount in INR")
    customer_name: str = Field(..., min_length=1, description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email (optional)")
    customer_phone: str = Field(..., min_length=10, description="Customer phone")
    notes: Optional[dict] = Field(None, description="Additional notes for Razorpay")


class VerifyPaymentRequest(BaseModel):
    """API request to verify payment."""
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="Razorpay signature for verification")
    order_id: uuid.UUID = Field(..., description="Internal order ID")


class InitiateRefundRequest(BaseModel):
    """API request to initiate a refund."""
    payment_id: str = Field(..., description="Razorpay payment ID")
    order_id: uuid.UUID = Field(..., description="Internal order ID")
    amount: Optional[float] = Field(None, gt=0, description="Refund amount (for partial refund)")
    reason: Optional[str] = Field(None, description="Reason for refund")
