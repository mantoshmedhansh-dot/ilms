from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.region import RegionType


class RegionBase(BaseModel):
    """Base region schema."""
    name: str = Field(..., min_length=1, max_length=100, description="Region name")
    code: str = Field(..., min_length=1, max_length=20, description="Unique region code")
    type: RegionType = Field(..., description="Region type in hierarchy")
    description: Optional[str] = Field(None, description="Region description")
    parent_id: Optional[uuid.UUID] = Field(None, description="Parent region ID")


class RegionCreate(RegionBase):
    """Region creation schema."""
    pass


class RegionUpdate(BaseModel):
    """Region update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class RegionResponse(BaseResponseSchema):
    """Region response schema."""
    id: uuid.UUID
    name: str
    code: str
    type: str
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class RegionWithChildren(RegionResponse):
    """Region response with children."""
    children: List["RegionWithChildren"] = []


class RegionListResponse(BaseModel):
    """Paginated region list response."""
    items: List[RegionResponse]
    total: int
    page: int
    size: int
    pages: int


class RegionTreeResponse(BaseModel):
    """Region hierarchy tree response."""
    regions: List[RegionWithChildren]


# Enable forward reference resolution
RegionWithChildren.model_rebuild()
