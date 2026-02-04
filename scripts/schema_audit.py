"""
Schema Audit Script - Compare Production (Supabase) vs Local (Docker)

This script exports and compares table structures to identify mismatches.
Production (Supabase) is the SOURCE OF TRUTH.

Usage:
    python -m scripts.schema_audit
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


# Database URLs
PRODUCTION_URL = os.environ.get("PRODUCTION_DB_URL", "")
LOCAL_URL = "postgresql+psycopg://ilms:ilms_dev_2026@localhost:5432/ilms_erp"


async def get_schema_info(engine, db_name: str) -> dict:
    """Get complete schema information from a database."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    schema = {"tables": {}}

    async with async_session() as session:
        # Get all tables
        result = await session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]

        print(f"\n{db_name}: Found {len(tables)} tables")

        # Get columns for each table
        for table in tables:
            result = await session.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table
                ORDER BY ordinal_position
            """), {"table": table})

            columns = {}
            for row in result.fetchall():
                col_name, data_type, nullable, default, max_len = row
                columns[col_name] = {
                    "type": data_type,
                    "nullable": nullable == "YES",
                    "default": default,
                    "max_length": max_len
                }

            schema["tables"][table] = columns

    return schema


def compare_schemas(prod_schema: dict, local_schema: dict) -> dict:
    """Compare production and local schemas."""
    differences = {
        "tables_only_in_production": [],
        "tables_only_in_local": [],
        "column_differences": {}
    }

    prod_tables = set(prod_schema["tables"].keys())
    local_tables = set(local_schema["tables"].keys())

    # Tables only in production
    differences["tables_only_in_production"] = sorted(prod_tables - local_tables)

    # Tables only in local
    differences["tables_only_in_local"] = sorted(local_tables - prod_tables)

    # Compare columns for common tables
    common_tables = prod_tables & local_tables

    for table in sorted(common_tables):
        prod_cols = prod_schema["tables"][table]
        local_cols = local_schema["tables"][table]

        prod_col_names = set(prod_cols.keys())
        local_col_names = set(local_cols.keys())

        table_diff = {
            "columns_only_in_production": sorted(prod_col_names - local_col_names),
            "columns_only_in_local": sorted(local_col_names - prod_col_names),
            "type_mismatches": []
        }

        # Check for type mismatches in common columns
        common_cols = prod_col_names & local_col_names
        for col in sorted(common_cols):
            prod_type = prod_cols[col]["type"]
            local_type = local_cols[col]["type"]

            # Normalize types for comparison
            prod_type_norm = prod_type.lower().replace("character varying", "varchar")
            local_type_norm = local_type.lower().replace("character varying", "varchar")

            if prod_type_norm != local_type_norm:
                table_diff["type_mismatches"].append({
                    "column": col,
                    "production_type": prod_type,
                    "local_type": local_type
                })

        # Only add if there are differences
        if (table_diff["columns_only_in_production"] or
            table_diff["columns_only_in_local"] or
            table_diff["type_mismatches"]):
            differences["column_differences"][table] = table_diff

    return differences


def print_report(differences: dict):
    """Print a formatted report of differences."""
    print("\n" + "=" * 80)
    print("SCHEMA AUDIT REPORT")
    print("Production (Supabase) vs Local (Docker)")
    print("=" * 80)

    # Tables only in production
    if differences["tables_only_in_production"]:
        print(f"\n### TABLES ONLY IN PRODUCTION ({len(differences['tables_only_in_production'])}):")
        print("    (These need to be REMOVED from local or ADDED to production)")
        for t in differences["tables_only_in_production"]:
            print(f"    - {t}")
    else:
        print("\n### TABLES ONLY IN PRODUCTION: None")

    # Tables only in local
    if differences["tables_only_in_local"]:
        print(f"\n### TABLES ONLY IN LOCAL ({len(differences['tables_only_in_local'])}):")
        print("    (These need migration to production)")
        for t in differences["tables_only_in_local"]:
            print(f"    - {t}")
    else:
        print("\n### TABLES ONLY IN LOCAL: None")

    # Column differences
    if differences["column_differences"]:
        print(f"\n### COLUMN DIFFERENCES ({len(differences['column_differences'])} tables):")
        for table, diff in sorted(differences["column_differences"].items()):
            print(f"\n  TABLE: {table}")

            if diff["columns_only_in_production"]:
                print(f"    Columns ONLY in Production (missing in local):")
                for col in diff["columns_only_in_production"]:
                    print(f"      - {col}")

            if diff["columns_only_in_local"]:
                print(f"    Columns ONLY in Local (missing in production):")
                for col in diff["columns_only_in_local"]:
                    print(f"      - {col}")

            if diff["type_mismatches"]:
                print(f"    Type Mismatches:")
                for m in diff["type_mismatches"]:
                    print(f"      - {m['column']}: PROD={m['production_type']} vs LOCAL={m['local_type']}")
    else:
        print("\n### COLUMN DIFFERENCES: None")

    print("\n" + "=" * 80)

    # Summary
    total_issues = (
        len(differences["tables_only_in_production"]) +
        len(differences["tables_only_in_local"]) +
        len(differences["column_differences"])
    )

    if total_issues == 0:
        print("RESULT: Schemas are IN SYNC!")
    else:
        print(f"RESULT: Found {total_issues} areas with differences")
        print("\nACTION REQUIRED:")
        print("  1. Production (Supabase) is SOURCE OF TRUTH")
        print("  2. Local Docker must be updated to match production")
        print("  3. SQLAlchemy models must match production schema")
        print("  4. Pydantic schemas must match models")

    print("=" * 80)


async def main():
    if not PRODUCTION_URL:
        print("ERROR: PRODUCTION_DB_URL environment variable not set!")
        print("Usage: PRODUCTION_DB_URL='postgresql+psycopg://...' python -m scripts.schema_audit")
        sys.exit(1)

    print("=" * 80)
    print("SCHEMA AUDIT: Production (Supabase) vs Local (Docker)")
    print("=" * 80)

    # Connect to production
    print("\nConnecting to PRODUCTION (Supabase)...")
    prod_engine = create_async_engine(PRODUCTION_URL, echo=False)
    prod_schema = await get_schema_info(prod_engine, "PRODUCTION")
    await prod_engine.dispose()

    # Connect to local
    print("\nConnecting to LOCAL (Docker)...")
    local_engine = create_async_engine(LOCAL_URL, echo=False)
    local_schema = await get_schema_info(local_engine, "LOCAL")
    await local_engine.dispose()

    # Compare
    print("\nComparing schemas...")
    differences = compare_schemas(prod_schema, local_schema)

    # Print report
    print_report(differences)

    # Save detailed report to file
    report_file = Path(__file__).parent.parent / "schema_audit_report.txt"
    with open(report_file, "w") as f:
        f.write("SCHEMA AUDIT DETAILED REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write("PRODUCTION TABLES:\n")
        for table in sorted(prod_schema["tables"].keys()):
            f.write(f"\n  {table}:\n")
            for col, info in prod_schema["tables"][table].items():
                f.write(f"    - {col}: {info['type']}\n")

        f.write("\n\nLOCAL TABLES:\n")
        for table in sorted(local_schema["tables"].keys()):
            f.write(f"\n  {table}:\n")
            for col, info in local_schema["tables"][table].items():
                f.write(f"    - {col}: {info['type']}\n")

    print(f"\nDetailed report saved to: {report_file}")

    return differences


if __name__ == "__main__":
    asyncio.run(main())
