from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid


class CategoryBase(BaseModel):
    """Base category schema."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    image_url: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: int = Field(default=0)
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)
    is_featured: bool = False


class CategoryCreate(CategoryBase):
    """Category creation schema."""
    pass


class CategoryUpdate(BaseModel):
    """Category update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    image_url: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class CategoryResponse(BaseResponseSchema):
    """Category response schema."""
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    image_url: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    is_active: bool
    is_featured: bool
    created_at: datetime
    updated_at: datetime

class CategoryWithChildren(CategoryResponse):
    """Category with nested children."""
    children: List["CategoryWithChildren"] = []
    product_count: Optional[int] = None


class CategoryListResponse(BaseModel):
    """Paginated category list."""
    items: List[CategoryResponse]
    total: int
    page: int
    size: int
    pages: int


class CategoryTreeResponse(BaseModel):
    """Category tree response."""
    categories: List[CategoryWithChildren]


# Enable forward reference resolution
CategoryWithChildren.model_rebuild()
