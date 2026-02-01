"""Credentials management schemas for API requests/responses."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional
from uuid import UUID
from datetime import datetime


class GSTCredentialsUpdate(BaseModel):
    """Update GST E-Invoice/E-Way Bill credentials."""
    einvoice_username: Optional[str] = Field(None, description="E-Invoice portal username")
    einvoice_password: Optional[str] = Field(None, description="E-Invoice portal password (will be encrypted)")
    einvoice_api_key: Optional[str] = Field(None, description="E-Invoice API key (will be encrypted)")
    einvoice_enabled: Optional[bool] = Field(None, description="Enable E-Invoice generation")
    einvoice_api_mode: Optional[str] = Field(None, description="API mode: SANDBOX or PRODUCTION")

    ewaybill_username: Optional[str] = Field(None, description="E-Way Bill portal username")
    ewaybill_password: Optional[str] = Field(None, description="E-Way Bill portal password (will be encrypted)")
    ewaybill_app_key: Optional[str] = Field(None, description="E-Way Bill app key (will be encrypted)")
    ewaybill_enabled: Optional[bool] = Field(None, description="Enable E-Way Bill generation")
    ewaybill_api_mode: Optional[str] = Field(None, description="API mode: SANDBOX or PRODUCTION")


class GSTCredentialsResponse(BaseModel):
    """Response with masked credentials."""
    company_id: UUID
    einvoice_username: Optional[str] = None
    einvoice_password_set: bool = Field(..., description="Whether password is configured")
    einvoice_enabled: bool
    einvoice_api_mode: str

    ewaybill_username: Optional[str] = None
    ewaybill_password_set: bool = Field(..., description="Whether password is configured")
    ewaybill_enabled: bool
    ewaybill_api_mode: str

    updated_at: Optional[datetime] = None


class EncryptRequest(BaseModel):
    """Request to encrypt a value (for testing/admin)."""
    value: str = Field(..., description="Value to encrypt")


class EncryptResponse(BaseModel):
    """Encrypted value response."""
    encrypted: str = Field(..., description="Encrypted value")
    is_encrypted: bool = Field(..., description="Confirmation that value is encrypted")


class TestConnectionRequest(BaseModel):
    """Request to test GST portal connection."""
    portal_type: str = Field(..., description="Portal type: EINVOICE or EWAYBILL")
