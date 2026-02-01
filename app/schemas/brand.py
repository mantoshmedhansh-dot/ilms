from pydantic import BaseModel, Field, EmailStr, computed_field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid


class BrandBase(BaseModel):
    """Base brand schema."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    banner_url: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    sort_order: int = Field(default=0)
    is_featured: bool = False


class BrandCreate(BrandBase):
    """Brand creation schema."""
    pass


class BrandUpdate(BaseModel):
    """Brand update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class BrandResponse(BaseResponseSchema):
    """Brand response schema."""
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    sort_order: int
    is_active: bool
    is_featured: bool
    created_at: datetime
    updated_at: datetime

    # Frontend compatibility alias
    @computed_field
    @property
    def code(self) -> str:
        """Alias for slug - frontend expects 'code' field."""
        return self.slug

class BrandWithStats(BrandResponse):
    """Brand with product statistics."""
    product_count: int = 0


class BrandListResponse(BaseModel):
    """Paginated brand list."""
    items: List[BrandResponse]
    total: int
    page: int
    size: int
    pages: int
