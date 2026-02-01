"""
Enum Utilities for VARCHAR-based Status Fields

ARCHITECTURE STANDARD (from CLAUDE.md):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Database: VARCHAR(50) - NOT PostgreSQL ENUM
• SQLAlchemy: String(50) with Mapped[str]
• Pydantic: Python Enum for API validation
• API Response: Use string directly (NO .value needed)
• Case: All enum values stored in UPPERCASE

DATA FLOW:
━━━━━━━━━━
INPUT (API Request):
    Pydantic Enum → .value → String → Database
    Example: OrderStatus.PENDING → "PENDING" → VARCHAR

OUTPUT (API Response):
    Database → String → Return directly
    Example: VARCHAR "PENDING" → "PENDING" (no conversion needed)

CASE NORMALIZATION:
━━━━━━━━━━━━━━━━━━━
All enum-like string values are stored in UPPERCASE.
Use normalize_to_uppercase() or create_uppercase_validator()
to ensure case-insensitive input acceptance.

USAGE PATTERNS:
━━━━━━━━━━━━━━━
1. In SQLAlchemy Models:
   status: Mapped[str] = mapped_column(String(50), default="PENDING")

2. In Pydantic Schemas (for INPUT validation):
   status: OrderStatus = OrderStatus.PENDING

3. In Pydantic Schemas (with case normalization):
   _normalize_status = create_uppercase_validator('status', VALID_ORDER_STATUSES)

4. In API Responses (reading from DB):
   return {"status": order.status}  # Already a string, use directly

5. In API Responses (with enum input):
   return {"status": get_enum_value(data.status)}  # Safe for both
"""

from enum import Enum
from typing import Any, Optional, TypeVar, Type, Set


T = TypeVar('T', bound=Enum)


def get_enum_value(value: Any) -> str:
    """
    Safely get string value from an enum or string.

    Use this when you're unsure if the value is:
    - A Pydantic enum (from input) - has .value
    - A database string (from query) - is already a string

    Args:
        value: Either an Enum instance or a string

    Returns:
        The string value

    Examples:
        >>> get_enum_value(OrderStatus.PENDING)  # Pydantic input
        'PENDING'
        >>> get_enum_value("PENDING")  # Database value
        'PENDING'
        >>> get_enum_value(None)
        None
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    return str(value)


def get_enum_name(value: Any) -> str:
    """
    Safely get name from an enum or string.

    Args:
        value: Either an Enum instance or a string

    Returns:
        The name (for enums) or the string itself
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.name
    return str(value)


def to_enum(value: Any, enum_class: Type[T]) -> Optional[T]:
    """
    Convert a string value to an enum instance.

    Use this when you need to convert a database string
    back to an enum for comparison or validation.

    Args:
        value: String value from database
        enum_class: The Enum class to convert to

    Returns:
        Enum instance or None if not found

    Examples:
        >>> to_enum("PENDING", OrderStatus)
        OrderStatus.PENDING
        >>> to_enum("INVALID", OrderStatus)
        None
    """
    if value is None:
        return None
    if isinstance(value, enum_class):
        return value
    try:
        return enum_class(value)
    except (ValueError, KeyError):
        return None


def enum_values(enum_class: Type[Enum]) -> list:
    """
    Get all values from an enum class.

    Useful for generating comment strings for VARCHAR columns.

    Args:
        enum_class: The Enum class

    Returns:
        List of all enum values

    Examples:
        >>> enum_values(OrderStatus)
        ['PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED']
    """
    return [e.value for e in enum_class]


def enum_comment(enum_class: Type[Enum]) -> str:
    """
    Generate a comment string for VARCHAR column.

    Use this in SQLAlchemy model column definitions.

    Args:
        enum_class: The Enum class

    Returns:
        Comma-separated string of valid values

    Examples:
        >>> enum_comment(OrderStatus)
        'PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED'
    """
    return ", ".join(enum_values(enum_class))


# =============================================================================
# COMPARISON HELPERS
# =============================================================================

def is_status(db_value: str, enum_value: Enum) -> bool:
    """
    Compare a database string with an enum value.

    Args:
        db_value: String from database
        enum_value: Enum to compare with

    Returns:
        True if they match

    Examples:
        >>> is_status(order.status, OrderStatus.PENDING)
        True
    """
    if db_value is None:
        return False
    return db_value == enum_value.value


def status_in(db_value: str, *enum_values: Enum) -> bool:
    """
    Check if database value matches any of the given enums.

    Args:
        db_value: String from database
        enum_values: Enum values to check against

    Returns:
        True if db_value matches any enum value

    Examples:
        >>> status_in(order.status, OrderStatus.PENDING, OrderStatus.CONFIRMED)
        True
    """
    if db_value is None:
        return False
    return db_value in [e.value for e in enum_values]


# =============================================================================
# LEVEL COMPARISON (for Role hierarchy)
# =============================================================================

def compare_levels(level1: str, level2: str, level_order: dict) -> int:
    """
    Compare two level strings using a hierarchy order.

    Args:
        level1: First level string
        level2: Second level string
        level_order: Dict mapping level names to numeric values

    Returns:
        -1 if level1 < level2 (higher authority)
         0 if equal
         1 if level1 > level2 (lower authority)
    """
    val1 = level_order.get(level1, 999)
    val2 = level_order.get(level2, 999)

    if val1 < val2:
        return -1
    elif val1 > val2:
        return 1
    return 0


# =============================================================================
# CASE NORMALIZATION FOR PYDANTIC SCHEMAS
# =============================================================================

def normalize_to_uppercase(value: Any, valid_values: Set[str]) -> Any:
    """
    Normalize a string value to UPPERCASE if it's a valid enum value.

    Use this in Pydantic field_validators to accept case-insensitive input
    while ensuring UPPERCASE storage in the database.

    Args:
        value: The input value (may be any type)
        valid_values: Set of valid UPPERCASE values

    Returns:
        UPPERCASE string if valid, original value otherwise (for Pydantic to handle)

    Examples:
        >>> normalize_to_uppercase('pending', {'PENDING', 'ACTIVE'})
        'PENDING'
        >>> normalize_to_uppercase('PENDING', {'PENDING', 'ACTIVE'})
        'PENDING'
        >>> normalize_to_uppercase('invalid', {'PENDING', 'ACTIVE'})
        'invalid'  # Returns as-is for Pydantic to raise validation error
    """
    if value is None:
        return value
    if isinstance(value, str):
        upper_v = value.upper()
        if upper_v in valid_values:
            return upper_v
    return value


def create_uppercase_validator(field_name: str, valid_values: Set[str]) -> classmethod:
    """
    Create a Pydantic field_validator that normalizes values to UPPERCASE.

    Usage:
        class MySchema(BaseModel):
            status: StatusType

            _normalize_status = create_uppercase_validator('status', VALID_ORDER_STATUSES)

    Args:
        field_name: Name of the field to validate
        valid_values: Set of valid UPPERCASE values

    Returns:
        A classmethod decorator that can be assigned to the schema
    """
    from pydantic import field_validator

    @field_validator(field_name, mode='before')
    @classmethod
    def validate(cls, v):
        return normalize_to_uppercase(v, valid_values)

    return validate


# =============================================================================
# PRE-DEFINED VALID VALUE SETS FOR COMMON ENUMS
# =============================================================================
# Use these with normalize_to_uppercase() or create_uppercase_validator()

# Role hierarchy
VALID_ROLE_LEVELS = {
    "SUPER_ADMIN", "DIRECTOR", "HEAD", "MANAGER", "EXECUTIVE"
}

# Order management
VALID_ORDER_STATUSES = {
    "NEW", "PENDING_PAYMENT", "CONFIRMED", "ALLOCATED", "PICKLIST_CREATED",
    "PICKING", "PACKED", "READY_TO_SHIP", "SHIPPED", "IN_TRANSIT",
    "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED", "RETURNED", "REFUNDED"
}

VALID_PAYMENT_STATUSES = {
    "PENDING", "AUTHORIZED", "CAPTURED", "PAID", "PARTIALLY_PAID",
    "REFUNDED", "PARTIALLY_REFUNDED", "CANCELLED", "FAILED"
}

VALID_PAYMENT_METHODS = {
    "CASH", "CARD", "UPI", "NET_BANKING", "WALLET", "EMI", "COD", "CHEQUE"
}

VALID_ORDER_SOURCES = {
    "WEBSITE", "MOBILE_APP", "STORE", "PHONE", "DEALER",
    "AMAZON", "FLIPKART", "OTHER"
}

# Company
VALID_COMPANY_TYPES = {
    "PRIVATE_LIMITED", "PUBLIC_LIMITED", "LLP", "PARTNERSHIP",
    "PROPRIETORSHIP", "OPC", "TRUST", "SOCIETY", "HUF", "GOVERNMENT"
}

VALID_GST_REGISTRATION_TYPES = {
    "REGULAR", "COMPOSITION", "CASUAL", "SEZ_UNIT", "SEZ_DEVELOPER",
    "ISD", "TDS_DEDUCTOR", "TCS_COLLECTOR", "NON_RESIDENT", "UNREGISTERED"
}

VALID_BANK_ACCOUNT_TYPES = {"CURRENT", "SAVINGS", "OD", "CC"}

# Dealer
VALID_DEALER_TYPES = {
    "DISTRIBUTOR", "DEALER", "SUB_DEALER", "RETAILER",
    "FRANCHISE", "MODERN_TRADE", "INSTITUTIONAL", "GOVERNMENT"
}

VALID_DEALER_STATUSES = {
    "PENDING_APPROVAL", "ACTIVE", "INACTIVE", "SUSPENDED",
    "BLACKLISTED", "TERMINATED"
}

VALID_DEALER_TIERS = {"PLATINUM", "GOLD", "SILVER", "BRONZE", "STANDARD"}

# Vendor
VALID_VENDOR_TYPES = {
    "MANUFACTURER", "IMPORTER", "DISTRIBUTOR", "TRADING",
    "SERVICE_PROVIDER", "CONTRACTOR", "TRANSPORTER", "OTHER"
}

VALID_VENDOR_STATUSES = {"ACTIVE", "INACTIVE", "PENDING_APPROVAL", "BLACKLISTED"}

# Shipment
VALID_SHIPMENT_STATUSES = {
    "CREATED", "PACKED", "READY_FOR_PICKUP", "PICKED_UP", "IN_TRANSIT",
    "OUT_FOR_DELIVERY", "DELIVERED", "FAILED_DELIVERY", "RTO_INITIATED",
    "RTO_IN_TRANSIT", "RTO_DELIVERED", "CANCELLED", "LOST"
}

VALID_PACKAGING_TYPES = {"BOX", "ENVELOPE", "POLY_BAG", "PALLET", "CUSTOM"}

# Purchase
VALID_PO_STATUSES = {
    "DRAFT", "PENDING_APPROVAL", "APPROVED", "SENT_TO_VENDOR",
    "ACKNOWLEDGED", "PARTIALLY_RECEIVED", "FULLY_RECEIVED", "CLOSED", "CANCELLED"
}

VALID_GRN_STATUSES = {
    "DRAFT", "PENDING_QC", "QC_PASSED", "QC_FAILED",
    "ACCEPTED", "REJECTED", "PUT_AWAY_COMPLETE"
}

# Service
VALID_SERVICE_STATUSES = {
    "OPEN", "ASSIGNED", "IN_PROGRESS", "ON_HOLD", "RESOLVED",
    "CLOSED", "CANCELLED", "ESCALATED"
}

VALID_INSTALLATION_STATUSES = {
    "PENDING", "SCHEDULED", "IN_PROGRESS", "COMPLETED",
    "FAILED", "CANCELLED", "RESCHEDULED"
}

# Lead/CRM
VALID_LEAD_STATUSES = {
    "NEW", "CONTACTED", "QUALIFIED", "PROPOSAL_SENT", "NEGOTIATION",
    "WON", "LOST", "DISQUALIFIED"
}

# Approval workflow
VALID_APPROVAL_STATUSES = {
    "PENDING", "APPROVED", "REJECTED", "RETURNED", "ESCALATED"
}

# Picklist
VALID_PICKLIST_STATUSES = {
    "PENDING", "ASSIGNED", "IN_PROGRESS", "COMPLETED",
    "PARTIALLY_PICKED", "CANCELLED"
}

VALID_PICKLIST_TYPES = {"SINGLE_ORDER", "BATCH", "WAVE"}
