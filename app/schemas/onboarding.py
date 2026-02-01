"""Pydantic schemas for tenant onboarding and registration."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class SubdomainCheckRequest(BaseModel):
    """Request to check if subdomain is available."""
    subdomain: str = Field(..., min_length=3, max_length=63)

    @field_validator('subdomain')
    @classmethod
    def validate_subdomain(cls, v: str) -> str:
        """Validate subdomain format."""
        # Only allow lowercase alphanumeric and hyphens
        if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', v):
            raise ValueError(
                'Subdomain must contain only lowercase letters, numbers, and hyphens. '
                'It cannot start or end with a hyphen.'
            )

        # Reserved subdomains
        reserved = [
            'admin', 'api', 'www', 'mail', 'smtp', 'ftp', 'localhost',
            'webmail', 'email', 'support', 'help', 'status', 'blog',
            'forum', 'store', 'shop', 'dashboard', 'app', 'my', 'account',
            'auth', 'login', 'signup', 'register', 'cdn', 'static', 'assets',
            'files', 'uploads', 'download', 'test', 'demo', 'sandbox'
        ]

        if v in reserved:
            raise ValueError(f'Subdomain "{v}" is reserved and cannot be used.')

        return v


class SubdomainCheckResponse(BaseModel):
    """Response for subdomain availability check."""
    subdomain: str
    available: bool
    message: Optional[str] = None


class TenantRegistrationRequest(BaseModel):
    """Request to register a new tenant."""

    # Company Details
    company_name: str = Field(..., min_length=2, max_length=200)
    subdomain: str = Field(..., min_length=3, max_length=63)

    # Admin User Details
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=100)
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    admin_phone: Optional[str] = Field(None, max_length=20)

    # Module Selection
    selected_modules: List[str] = Field(..., min_items=1)

    # Optional
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)  # "1-10", "11-50", etc.
    country: Optional[str] = Field(None, max_length=100)

    @field_validator('subdomain')
    @classmethod
    def validate_subdomain(cls, v: str) -> str:
        """Validate subdomain format (same as SubdomainCheckRequest)."""
        if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', v):
            raise ValueError(
                'Subdomain must contain only lowercase letters, numbers, and hyphens. '
                'It cannot start or end with a hyphen.'
            )

        reserved = [
            'admin', 'api', 'www', 'mail', 'smtp', 'ftp', 'localhost',
            'webmail', 'email', 'support', 'help', 'status', 'blog',
            'forum', 'store', 'shop', 'dashboard', 'app', 'my', 'account',
            'auth', 'login', 'signup', 'register', 'cdn', 'static', 'assets',
            'files', 'uploads', 'download', 'test', 'demo', 'sandbox'
        ]

        if v in reserved:
            raise ValueError(f'Subdomain "{v}" is reserved.')

        return v

    @field_validator('admin_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long.')

        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter.')

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter.')

        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number.')

        return v

    @field_validator('selected_modules')
    @classmethod
    def validate_modules(cls, v: List[str]) -> List[str]:
        """Validate module selection."""
        if not v:
            raise ValueError('At least one module must be selected.')

        # system_admin must be included
        if 'system_admin' not in v:
            raise ValueError('system_admin module is required for all tenants.')

        return v


class TenantRegistrationResponse(BaseModel):
    """Response after successful tenant registration."""

    # Tenant Details
    tenant_id: str
    company_name: str
    subdomain: str
    database_schema: str
    status: str

    # Admin User
    admin_user_id: str
    admin_email: str

    # Authentication
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

    # Subscription Info
    subscribed_modules: List[str]
    plan_name: Optional[str] = None
    monthly_cost: Optional[float] = None

    message: str


class AvailableModuleResponse(BaseModel):
    """Response for available module information."""

    code: str
    name: str
    description: str
    category: str
    base_price: float
    is_required: bool = False
    dependencies: List[str] = []
    # Features can be any type since sections field can contain various data
    features: List = []


class ModuleListResponse(BaseModel):
    """Response for list of available modules."""

    modules: List[AvailableModuleResponse]
    total: int


class ModulePricingResponse(BaseModel):
    """Response for module pricing calculation."""

    selected_modules: List[str]
    monthly_cost: float
    yearly_cost: float
    discount_percentage: float = 0.0
    total_modules: int
