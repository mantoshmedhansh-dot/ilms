"""
Base Schema Classes for Pydantic Models

This module provides base classes that handle common patterns like UUID serialization,
ensuring consistency across all response schemas.

RULE: All response schemas that use `from_attributes=True` MUST inherit from BaseResponseSchema.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class BaseResponseSchema(BaseModel):
    """
    Base class for all response schemas that read from ORM models.

    Features:
    - Automatically handles UUID → string serialization in JSON
    - Enables from_attributes for ORM compatibility
    - Consistent datetime serialization

    Usage:
        class ProductResponse(BaseResponseSchema):
            id: UUID
            name: str
            category_id: Optional[UUID] = None
    """
    model_config = ConfigDict(
        from_attributes=True,
        # Serialize UUIDs as strings in JSON output
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat() if v else None,
        },
        # Allow population by field name or alias
        populate_by_name=True,
    )


class BaseCreateSchema(BaseModel):
    """
    Base class for create/input schemas.

    These schemas accept string UUIDs from frontend and convert to UUID objects.
    No from_attributes needed since these don't read from ORM.
    """
    model_config = ConfigDict(
        # Allow extra fields to be ignored (forward compatibility)
        extra='ignore',
    )


class BaseUpdateSchema(BaseModel):
    """
    Base class for update/patch schemas.

    All fields are optional by default for partial updates.
    """
    model_config = ConfigDict(
        extra='ignore',
    )


# Type aliases for common UUID patterns
UUIDField = UUID
OptionalUUID = Optional[UUID]
