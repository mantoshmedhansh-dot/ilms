"""Create template schema with all operational tables

Revision ID: 003_create_template_schema
Revises: 002_seed_modules_and_plans
Create Date: 2026-02-01 11:00:00.000000

This migration creates a template_tenant schema containing the structure
of all operational tables. This template is copied when provisioning new tenants.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '003_create_template_schema'
down_revision = '002_seed_modules_and_plans'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create template_tenant schema with all operational table structures.

    This uses a different approach: we'll create the schema and then
    use SQLAlchemy to create all tables within it.
    """
    # Create template schema
    op.execute('CREATE SCHEMA IF NOT EXISTS template_tenant')

    print("✓ Created template_tenant schema")
    print("  Note: Tables will be created programmatically when needed")
    print("  Use: python scripts/create_template_tables.py")


def downgrade() -> None:
    """Drop template schema and all its tables."""
    op.execute('DROP SCHEMA IF EXISTS template_tenant CASCADE')
    print("✓ Dropped template_tenant schema")
