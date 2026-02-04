"""
Tenant Schema Definition - Single Source of Truth

This module defines the complete tenant schema structure.
All tenant tables, columns, indexes, and constraints are defined here.
The schema service uses this to create and validate tenant schemas.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ColumnType(Enum):
    """PostgreSQL column types."""
    UUID = "UUID"
    VARCHAR = "VARCHAR"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    DECIMAL = "DECIMAL"
    TIMESTAMPTZ = "TIMESTAMPTZ"
    DATE = "DATE"
    JSONB = "JSONB"


@dataclass
class Column:
    """Column definition."""
    name: str
    type: ColumnType
    length: Optional[int] = None  # For VARCHAR
    precision: Optional[tuple] = None  # For DECIMAL (precision, scale)
    nullable: bool = True
    unique: bool = False
    primary_key: bool = False
    default: Optional[str] = None  # SQL default expression
    references: Optional[str] = None  # Foreign key reference "table(column)"
    on_delete: Optional[str] = None  # CASCADE, SET NULL, etc.

    def to_sql(self, schema_name: str) -> str:
        """Generate SQL column definition."""
        parts = [f'"{self.name}"']

        # Type
        if self.type == ColumnType.VARCHAR:
            parts.append(f"VARCHAR({self.length or 255})")
        elif self.type == ColumnType.DECIMAL and self.precision:
            parts.append(f"DECIMAL({self.precision[0]}, {self.precision[1]})")
        else:
            parts.append(self.type.value)

        # Constraints
        if self.primary_key:
            parts.append("PRIMARY KEY")
            if self.type == ColumnType.UUID:
                parts.append("DEFAULT gen_random_uuid()")
        elif self.default:
            parts.append(f"DEFAULT {self.default}")

        if not self.nullable and not self.primary_key:
            parts.append("NOT NULL")

        if self.unique and not self.primary_key:
            parts.append("UNIQUE")

        # Foreign key
        if self.references:
            ref_table, ref_col = self.references.split("(")
            ref_col = ref_col.rstrip(")")
            fk_table = f'"{schema_name}".{ref_table}' if not ref_table.startswith('"') else ref_table
            parts.append(f"REFERENCES {fk_table}({ref_col})")
            if self.on_delete:
                parts.append(f"ON DELETE {self.on_delete}")

        return " ".join(parts)


@dataclass
class Index:
    """Index definition."""
    name: str
    columns: List[str]
    unique: bool = False

    def to_sql(self, schema_name: str, table_name: str) -> str:
        """Generate CREATE INDEX statement."""
        unique_str = "UNIQUE " if self.unique else ""
        cols = ", ".join(self.columns)
        return f'CREATE {unique_str}INDEX IF NOT EXISTS {self.name} ON "{schema_name}".{table_name}({cols})'


@dataclass
class Table:
    """Table definition."""
    name: str
    columns: List[Column]
    indexes: List[Index] = field(default_factory=list)
    description: str = ""

    def to_create_sql(self, schema_name: str) -> str:
        """Generate CREATE TABLE statement."""
        col_defs = [col.to_sql(schema_name) for col in self.columns]
        cols_sql = ",\n                    ".join(col_defs)
        return f'''CREATE TABLE IF NOT EXISTS "{schema_name}".{self.name} (
                    {cols_sql}
                )'''

    def get_index_sql(self, schema_name: str) -> List[str]:
        """Generate CREATE INDEX statements."""
        return [idx.to_sql(schema_name, self.name) for idx in self.indexes]


# =============================================================================
# TENANT SCHEMA DEFINITION - All required tables for a tenant
# =============================================================================

TENANT_SCHEMA_TABLES: List[Table] = [
    # -------------------------------------------------------------------------
    # REGIONS TABLE - Must be created first (users references it)
    # -------------------------------------------------------------------------
    Table(
        name="regions",
        description="Geographic regions for organization hierarchy",
        columns=[
            Column("id", ColumnType.UUID, primary_key=True),
            Column("name", ColumnType.VARCHAR, length=100, nullable=False),
            Column("code", ColumnType.VARCHAR, length=50, nullable=False, unique=True),
            Column("type", ColumnType.VARCHAR, length=50, nullable=False, default="'STATE'"),
            Column("parent_id", ColumnType.UUID, references="regions(id)", on_delete="SET NULL"),
            Column("description", ColumnType.TEXT),
            Column("is_active", ColumnType.BOOLEAN, default="TRUE"),
            Column("created_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
            Column("updated_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
        ],
        indexes=[
            Index("idx_regions_code", ["code"]),
            Index("idx_regions_parent", ["parent_id"]),
            Index("idx_regions_type", ["type"]),
        ]
    ),

    # -------------------------------------------------------------------------
    # ROLES TABLE
    # -------------------------------------------------------------------------
    Table(
        name="roles",
        description="User roles for RBAC",
        columns=[
            Column("id", ColumnType.UUID, primary_key=True),
            Column("name", ColumnType.VARCHAR, length=100, nullable=False),
            Column("code", ColumnType.VARCHAR, length=50, nullable=False, unique=True),
            Column("description", ColumnType.TEXT),
            Column("level", ColumnType.VARCHAR, length=50, nullable=False, default="'USER'"),
            Column("department", ColumnType.VARCHAR, length=50),
            Column("is_system", ColumnType.BOOLEAN, default="FALSE"),
            Column("is_active", ColumnType.BOOLEAN, default="TRUE"),
            Column("created_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
            Column("updated_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
        ],
        indexes=[
            Index("idx_roles_code", ["code"]),
            Index("idx_roles_level", ["level"]),
        ]
    ),

    # -------------------------------------------------------------------------
    # USERS TABLE
    # -------------------------------------------------------------------------
    Table(
        name="users",
        description="Tenant users",
        columns=[
            Column("id", ColumnType.UUID, primary_key=True),
            Column("email", ColumnType.VARCHAR, length=255, nullable=False, unique=True),
            Column("phone", ColumnType.VARCHAR, length=20, unique=True),
            Column("password_hash", ColumnType.VARCHAR, length=255, nullable=False),
            Column("first_name", ColumnType.VARCHAR, length=100, nullable=False),
            Column("last_name", ColumnType.VARCHAR, length=100),
            Column("avatar_url", ColumnType.VARCHAR, length=500),
            Column("employee_code", ColumnType.VARCHAR, length=50, unique=True),
            Column("department", ColumnType.VARCHAR, length=100),
            Column("designation", ColumnType.VARCHAR, length=100),
            Column("region_id", ColumnType.UUID, references="regions(id)", on_delete="SET NULL"),
            Column("is_active", ColumnType.BOOLEAN, default="TRUE"),
            Column("is_verified", ColumnType.BOOLEAN, default="FALSE"),
            Column("created_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
            Column("updated_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
            Column("last_login_at", ColumnType.TIMESTAMPTZ),
        ],
        indexes=[
            Index("idx_users_email", ["email"]),
            Index("idx_users_phone", ["phone"]),
            Index("idx_users_employee_code", ["employee_code"]),
            Index("idx_users_region", ["region_id"]),
            Index("idx_users_is_active", ["is_active"]),
        ]
    ),

    # -------------------------------------------------------------------------
    # USER_ROLES TABLE
    # -------------------------------------------------------------------------
    Table(
        name="user_roles",
        description="User-Role assignments",
        columns=[
            Column("id", ColumnType.UUID, primary_key=True),
            Column("user_id", ColumnType.UUID, nullable=False, references="users(id)", on_delete="CASCADE"),
            Column("role_id", ColumnType.UUID, nullable=False, references="roles(id)", on_delete="CASCADE"),
            Column("assigned_by", ColumnType.UUID, references="users(id)", on_delete="SET NULL"),
            Column("assigned_at", ColumnType.TIMESTAMPTZ, default="NOW()"),
            Column("created_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
        ],
        indexes=[
            Index("idx_user_roles_user", ["user_id"]),
            Index("idx_user_roles_role", ["role_id"]),
        ]
    ),

    # -------------------------------------------------------------------------
    # AUDIT_LOGS TABLE
    # -------------------------------------------------------------------------
    Table(
        name="audit_logs",
        description="Audit trail for all actions",
        columns=[
            Column("id", ColumnType.UUID, primary_key=True),
            Column("user_id", ColumnType.UUID, references="users(id)", on_delete="SET NULL"),
            Column("action", ColumnType.VARCHAR, length=50, nullable=False),
            Column("entity_type", ColumnType.VARCHAR, length=50, nullable=False),
            Column("entity_id", ColumnType.UUID),
            Column("old_values", ColumnType.JSONB),
            Column("new_values", ColumnType.JSONB),
            Column("description", ColumnType.TEXT),
            Column("ip_address", ColumnType.VARCHAR, length=50),
            Column("user_agent", ColumnType.VARCHAR, length=500),
            Column("created_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
        ],
        indexes=[
            Index("idx_audit_action", ["action"]),
            Index("idx_audit_entity_type", ["entity_type"]),
            Index("idx_audit_entity_id", ["entity_id"]),
            Index("idx_audit_user", ["user_id"]),
            Index("idx_audit_created", ["created_at"]),
        ]
    ),

    # -------------------------------------------------------------------------
    # PERMISSIONS TABLE
    # -------------------------------------------------------------------------
    Table(
        name="permissions",
        description="Granular permissions",
        columns=[
            Column("id", ColumnType.UUID, primary_key=True),
            Column("name", ColumnType.VARCHAR, length=100, nullable=False),
            Column("code", ColumnType.VARCHAR, length=100, nullable=False, unique=True),
            Column("description", ColumnType.TEXT),
            Column("module_code", ColumnType.VARCHAR, length=50, nullable=False),
            Column("action", ColumnType.VARCHAR, length=50, nullable=False),
            Column("is_active", ColumnType.BOOLEAN, default="TRUE"),
            Column("created_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
            Column("updated_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
        ],
        indexes=[
            Index("idx_permissions_code", ["code"]),
            Index("idx_permissions_module", ["module_code"]),
        ]
    ),

    # -------------------------------------------------------------------------
    # ROLE_PERMISSIONS TABLE
    # -------------------------------------------------------------------------
    Table(
        name="role_permissions",
        description="Role-Permission assignments",
        columns=[
            Column("id", ColumnType.UUID, primary_key=True),
            Column("role_id", ColumnType.UUID, nullable=False, references="roles(id)", on_delete="CASCADE"),
            Column("permission_id", ColumnType.UUID, nullable=False, references="permissions(id)", on_delete="CASCADE"),
            Column("created_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
        ],
        indexes=[
            Index("idx_role_permissions_role", ["role_id"]),
            Index("idx_role_permissions_permission", ["permission_id"]),
            Index("idx_role_permissions_unique", ["role_id", "permission_id"], unique=True),
        ]
    ),

    # -------------------------------------------------------------------------
    # REFRESH_TOKENS TABLE (for JWT token management)
    # -------------------------------------------------------------------------
    Table(
        name="refresh_tokens",
        description="JWT refresh token storage",
        columns=[
            Column("id", ColumnType.UUID, primary_key=True),
            Column("user_id", ColumnType.UUID, nullable=False, references="users(id)", on_delete="CASCADE"),
            Column("token_hash", ColumnType.VARCHAR, length=255, nullable=False, unique=True),
            Column("expires_at", ColumnType.TIMESTAMPTZ, nullable=False),
            Column("revoked", ColumnType.BOOLEAN, default="FALSE"),
            Column("revoked_at", ColumnType.TIMESTAMPTZ),
            Column("created_at", ColumnType.TIMESTAMPTZ, default="NOW()", nullable=False),
        ],
        indexes=[
            Index("idx_refresh_tokens_user", ["user_id"]),
            Index("idx_refresh_tokens_hash", ["token_hash"]),
            Index("idx_refresh_tokens_expires", ["expires_at"]),
        ]
    ),
]


def get_table_by_name(name: str) -> Optional[Table]:
    """Get table definition by name."""
    for table in TENANT_SCHEMA_TABLES:
        if table.name == name:
            return table
    return None


def get_all_table_names() -> List[str]:
    """Get list of all table names."""
    return [table.name for table in TENANT_SCHEMA_TABLES]


def get_required_columns(table_name: str) -> List[str]:
    """Get list of required (non-nullable) columns for a table."""
    table = get_table_by_name(table_name)
    if not table:
        return []
    return [col.name for col in table.columns if not col.nullable or col.primary_key]
