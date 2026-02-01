from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseResponseSchema
from typing import Optional, List, Literal
from datetime import datetime
import uuid


# String-based enum for API input/output (matches VARCHAR in database)
# IMPORTANT: All values MUST be UPPERCASE to match database convention
RoleLevelType = Literal["SUPER_ADMIN", "DIRECTOR", "HEAD", "MANAGER", "EXECUTIVE"]
VALID_ROLE_LEVELS = {"SUPER_ADMIN", "DIRECTOR", "HEAD", "MANAGER", "EXECUTIVE"}


class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    code: str = Field(..., min_length=1, max_length=50, description="Unique role code")
    description: Optional[str] = Field(None, description="Role description")
    level: RoleLevelType = Field(..., description="Role hierarchy level")
    department: Optional[str] = Field(None, max_length=50, description="Department association")

    @field_validator('level', mode='before')
    @classmethod
    def normalize_level_to_uppercase(cls, v):
        """Convert level to UPPERCASE before validation. Accepts case-insensitive input."""
        if isinstance(v, str):
            upper_v = v.upper()
            if upper_v in VALID_ROLE_LEVELS:
                return upper_v
        return v  # Let Pydantic handle validation error for invalid values


class RoleCreate(RoleBase):
    """Role creation schema."""
    permission_ids: Optional[List[uuid.UUID]] = Field(
        default=[],
        description="Permission IDs to assign"
    )


class RoleUpdate(BaseModel):
    """Role update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    level: Optional[RoleLevelType] = None
    department: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

    @field_validator('name', 'department', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None for optional fields."""
        if v == "":
            return None
        return v

    @field_validator('level', mode='before')
    @classmethod
    def normalize_level_to_uppercase(cls, v):
        """Convert level to UPPERCASE before validation. Accepts case-insensitive input."""
        if v is None or v == "":
            return None  # Treat empty string as None (no update)
        if isinstance(v, str):
            upper_v = v.upper()
            if upper_v in VALID_ROLE_LEVELS:
                return upper_v
        return v  # Let Pydantic handle validation error for invalid values


class PermissionBasicInfo(BaseResponseSchema):
    """Basic permission info for role response."""
    id: uuid.UUID
    name: str
    code: str
    action: Optional[str] = None
    module_name: Optional[str] = None
class RoleResponse(BaseResponseSchema):
    """Role response schema."""
    id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    level: str
    department: Optional[str] = None
    is_system: bool
    is_active: bool
    permission_count: int = 0
    created_at: datetime
    updated_at: datetime

class RoleWithPermissions(RoleResponse):
    """Role response with permissions."""
    permissions: List[PermissionBasicInfo] = []


class RoleListResponse(BaseModel):
    """Paginated role list response."""
    items: List[RoleResponse]
    total: int
    page: int
    size: int
    pages: int
