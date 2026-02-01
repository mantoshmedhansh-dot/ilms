from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr = Field(..., description="User email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    employee_code: Optional[str] = Field(None, max_length=50, description="Employee code")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    designation: Optional[str] = Field(None, max_length=100, description="Designation")
    region_id: Optional[uuid.UUID] = Field(None, description="Region ID for filtering")


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=6, description="Password")
    role_ids: Optional[List[uuid.UUID]] = Field(default=[], description="Role IDs to assign")


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    employee_code: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)
    region_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None


class RoleBasicInfo(BaseResponseSchema):
    """Basic role info for user response."""
    id: uuid.UUID
    name: str
    code: str
    level: str
class RegionBasicInfo(BaseResponseSchema):
    """Basic region info for user response."""
    id: uuid.UUID
    name: str
    code: str
    type: str
class UserResponse(BaseResponseSchema):
    """User response schema."""
    id: uuid.UUID
    email: str
    phone: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    full_name: str
    employee_code: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    region: Optional[RegionBasicInfo] = None
    roles: List[RoleBasicInfo] = []
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

class UserListResponse(BaseModel):
    """Paginated user list response."""
    items: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class UserRoleAssignment(BaseModel):
    """Schema for assigning/revoking roles to a user."""
    role_ids: List[uuid.UUID] = Field(..., description="List of role IDs to assign")
