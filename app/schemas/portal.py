"""Customer Portal schemas for API requests/responses."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID


class CustomerAuth(BaseModel):
    """Customer authentication (for demo - in production use proper auth)."""
    customer_id: UUID = Field(..., description="Customer ID for authentication")


class ProfileUpdateRequest(BaseModel):
    """Request to update customer profile."""
    name: Optional[str] = Field(None, description="Customer name")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    mobile: Optional[str] = Field(None, description="Mobile number")
    address_line1: Optional[str] = Field(None, description="Address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    pincode: Optional[str] = Field(None, description="Pincode")


class ServiceRequestCreate(BaseModel):
    """Request to create a service request."""
    request_type: str = Field(
        ...,
        description="Request type: REPAIR, INSTALLATION, WARRANTY, GENERAL, COMPLAINT"
    )
    subject: str = Field(..., min_length=5, max_length=200, description="Subject")
    description: str = Field(..., min_length=10, max_length=2000, description="Description")
    product_id: Optional[UUID] = Field(None, description="Related product ID")
    order_id: Optional[UUID] = Field(None, description="Related order ID")
    priority: str = Field(
        default="NORMAL",
        description="Priority: LOW, NORMAL, HIGH, URGENT"
    )
    attachments: Optional[List[str]] = Field(None, description="Attachment URLs")


class ServiceRequestComment(BaseModel):
    """Request to add a comment to a service request."""
    comment: str = Field(..., min_length=1, max_length=1000, description="Comment text")


class FeedbackSubmit(BaseModel):
    """Request to submit feedback."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    comments: Optional[str] = Field(None, description="Optional comments")
