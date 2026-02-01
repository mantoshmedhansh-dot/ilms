"""Pydantic schemas for file uploads."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from enum import Enum


class UploadCategory(str, Enum):
    """Categories for file uploads."""
    LOGOS = "logos"
    PRODUCTS = "products"
    CATEGORIES = "categories"
    BRANDS = "brands"
    DOCUMENTS = "documents"
    SIGNATURES = "signatures"


class UploadResponse(BaseModel):
    """Response after successful file upload."""
    url: str = Field(..., description="Public URL of the uploaded file")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL (for images)")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type")


class MultiUploadResponse(BaseModel):
    """Response after successful multiple file upload."""
    files: List[UploadResponse] = Field(..., description="List of uploaded files")
    total: int = Field(..., description="Total number of files uploaded")


class DeleteRequest(BaseModel):
    """Request to delete a file."""
    url: str = Field(..., description="URL of the file to delete")


class DeleteResponse(BaseModel):
    """Response after file deletion."""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")
