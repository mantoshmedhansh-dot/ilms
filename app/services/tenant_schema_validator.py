"""
Tenant Schema Validator Service

Validates tenant schemas against the expected structure.
Identifies missing tables, columns, indexes, and other schema issues.
Can auto-fix schema issues when requested.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_schema_definition import (
    TENANT_SCHEMA_TABLES,
    Table,
    Column,
    get_table_by_name,
    get_all_table_names,
)

logger = logging.getLogger(__name__)


@dataclass
class SchemaIssue:
    """Represents a schema issue found during validation."""
    severity: str  # "CRITICAL", "WARNING", "INFO"
    issue_type: str  # "MISSING_TABLE", "MISSING_COLUMN", "MISSING_INDEX", etc.
    table_name: str
    column_name: Optional[str] = None
    description: str = ""
    fix_sql: Optional[str] = None  # SQL to fix the issue


@dataclass
class ValidationResult:
    """Result of schema validation."""
    schema_name: str
    is_valid: bool
    issues: List[SchemaIssue] = field(default_factory=list)
    tables_found: List[str] = field(default_factory=list)
    tables_missing: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "schema_name": self.schema_name,
            "is_valid": self.is_valid,
            "issues_count": len(self.issues),
            "critical_issues": len([i for i in self.issues if i.severity == "CRITICAL"]),
            "warnings": len([i for i in self.issues if i.severity == "WARNING"]),
            "tables_found": self.tables_found,
            "tables_missing": self.tables_missing,
            "issues": [
                {
                    "severity": i.severity,
                    "type": i.issue_type,
                    "table": i.table_name,
                    "column": i.column_name,
                    "description": i.description,
                }
                for i in self.issues
            ]
        }


class TenantSchemaValidator:
    """Validates and repairs tenant schemas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_schema(self, schema_name: str) -> ValidationResult:
        """
        Validate a tenant schema against expected structure.

        Args:
            schema_name: Name of the tenant schema (e.g., 'tenant_acme')

        Returns:
            ValidationResult with all issues found
        """
        result = ValidationResult(schema_name=schema_name, is_valid=True)

        # Check if schema exists
        schema_exists = await self._schema_exists(schema_name)
        if not schema_exists:
            result.is_valid = False
            result.issues.append(SchemaIssue(
                severity="CRITICAL",
                issue_type="MISSING_SCHEMA",
                table_name="",
                description=f"Schema '{schema_name}' does not exist",
                fix_sql=f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'
            ))
            return result

        # Get existing tables in schema
        existing_tables = await self._get_existing_tables(schema_name)
        expected_tables = get_all_table_names()

        result.tables_found = [t for t in expected_tables if t in existing_tables]
        result.tables_missing = [t for t in expected_tables if t not in existing_tables]

        # Check each expected table
        for table_def in TENANT_SCHEMA_TABLES:
            if table_def.name not in existing_tables:
                # Table is missing
                result.is_valid = False
                result.issues.append(SchemaIssue(
                    severity="CRITICAL",
                    issue_type="MISSING_TABLE",
                    table_name=table_def.name,
                    description=f"Table '{table_def.name}' does not exist",
                    fix_sql=table_def.to_create_sql(schema_name)
                ))
            else:
                # Table exists - check columns
                column_issues = await self._validate_table_columns(
                    schema_name, table_def
                )
                result.issues.extend(column_issues)
                if any(i.severity == "CRITICAL" for i in column_issues):
                    result.is_valid = False

                # Check indexes
                index_issues = await self._validate_table_indexes(
                    schema_name, table_def
                )
                result.issues.extend(index_issues)

        return result

    async def fix_schema(self, schema_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Fix all schema issues for a tenant.

        Args:
            schema_name: Name of the tenant schema
            dry_run: If True, only report what would be fixed

        Returns:
            Dictionary with fix results
        """
        # First validate to find issues
        validation = await self.validate_schema(schema_name)

        if validation.is_valid and len(validation.issues) == 0:
            return {
                "success": True,
                "message": "Schema is valid, no fixes needed",
                "fixes_applied": [],
                "dry_run": dry_run
            }

        fixes_applied = []
        fixes_failed = []

        # Sort issues: create tables first, then columns, then indexes
        sorted_issues = sorted(
            validation.issues,
            key=lambda i: (
                0 if i.issue_type == "MISSING_SCHEMA" else
                1 if i.issue_type == "MISSING_TABLE" else
                2 if i.issue_type == "MISSING_COLUMN" else
                3
            )
        )

        for issue in sorted_issues:
            if not issue.fix_sql:
                continue

            if dry_run:
                fixes_applied.append({
                    "issue": issue.description,
                    "sql": issue.fix_sql,
                    "status": "would_apply"
                })
            else:
                try:
                    await self.db.execute(text(issue.fix_sql))
                    fixes_applied.append({
                        "issue": issue.description,
                        "sql": issue.fix_sql,
                        "status": "applied"
                    })
                    logger.info(f"Fixed: {issue.description}")
                except Exception as e:
                    fixes_failed.append({
                        "issue": issue.description,
                        "sql": issue.fix_sql,
                        "status": "failed",
                        "error": str(e)
                    })
                    logger.error(f"Failed to fix {issue.description}: {e}")

        if not dry_run:
            await self.db.commit()

        return {
            "success": len(fixes_failed) == 0,
            "message": f"Applied {len(fixes_applied)} fixes" + (
                f", {len(fixes_failed)} failed" if fixes_failed else ""
            ),
            "fixes_applied": fixes_applied,
            "fixes_failed": fixes_failed,
            "dry_run": dry_run
        }

    async def _schema_exists(self, schema_name: str) -> bool:
        """Check if schema exists."""
        result = await self.db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.schemata
                WHERE schema_name = :schema_name
            )
        """), {"schema_name": schema_name})
        return result.scalar() or False

    async def _get_existing_tables(self, schema_name: str) -> List[str]:
        """Get list of existing tables in schema."""
        result = await self.db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema_name
            AND table_type = 'BASE TABLE'
        """), {"schema_name": schema_name})
        return [row[0] for row in result.fetchall()]

    async def _get_existing_columns(
        self, schema_name: str, table_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get existing columns with their properties."""
        result = await self.db.execute(text("""
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = :schema_name
            AND table_name = :table_name
        """), {"schema_name": schema_name, "table_name": table_name})

        columns = {}
        for row in result.fetchall():
            columns[row[0]] = {
                "data_type": row[1],
                "max_length": row[2],
                "nullable": row[3] == "YES",
                "default": row[4]
            }
        return columns

    async def _get_existing_indexes(
        self, schema_name: str, table_name: str
    ) -> List[str]:
        """Get list of existing index names."""
        result = await self.db.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = :schema_name
            AND tablename = :table_name
        """), {"schema_name": schema_name, "table_name": table_name})
        return [row[0] for row in result.fetchall()]

    async def _validate_table_columns(
        self, schema_name: str, table_def: Table
    ) -> List[SchemaIssue]:
        """Validate columns for a table."""
        issues = []
        existing_cols = await self._get_existing_columns(schema_name, table_def.name)

        for col_def in table_def.columns:
            if col_def.name not in existing_cols:
                # Column missing
                issues.append(SchemaIssue(
                    severity="CRITICAL",
                    issue_type="MISSING_COLUMN",
                    table_name=table_def.name,
                    column_name=col_def.name,
                    description=f"Column '{col_def.name}' missing from table '{table_def.name}'",
                    fix_sql=self._generate_add_column_sql(schema_name, table_def.name, col_def)
                ))
            else:
                # Column exists - could add type/constraint validation here
                pass

        return issues

    async def _validate_table_indexes(
        self, schema_name: str, table_def: Table
    ) -> List[SchemaIssue]:
        """Validate indexes for a table."""
        issues = []
        existing_indexes = await self._get_existing_indexes(schema_name, table_def.name)

        for idx_def in table_def.indexes:
            if idx_def.name not in existing_indexes:
                issues.append(SchemaIssue(
                    severity="WARNING",
                    issue_type="MISSING_INDEX",
                    table_name=table_def.name,
                    description=f"Index '{idx_def.name}' missing from table '{table_def.name}'",
                    fix_sql=idx_def.to_sql(schema_name, table_def.name)
                ))

        return issues

    def _generate_add_column_sql(
        self, schema_name: str, table_name: str, col_def: Column
    ) -> str:
        """Generate ALTER TABLE ADD COLUMN statement."""
        col_type = col_def.type.value
        if col_def.type.value == "VARCHAR":
            col_type = f"VARCHAR({col_def.length or 255})"

        parts = [f'ALTER TABLE "{schema_name}".{table_name}']
        parts.append(f'ADD COLUMN "{col_def.name}" {col_type}')

        if col_def.default:
            parts.append(f"DEFAULT {col_def.default}")

        if not col_def.nullable:
            parts.append("NOT NULL")

        return " ".join(parts)


async def validate_tenant_schema(db: AsyncSession, schema_name: str) -> ValidationResult:
    """Convenience function to validate a tenant schema."""
    validator = TenantSchemaValidator(db)
    return await validator.validate_schema(schema_name)


async def fix_tenant_schema(
    db: AsyncSession, schema_name: str, dry_run: bool = False
) -> Dict[str, Any]:
    """Convenience function to fix a tenant schema."""
    validator = TenantSchemaValidator(db)
    return await validator.fix_schema(schema_name, dry_run=dry_run)
