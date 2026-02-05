"""Add Training Modules table for partner training management

Revision ID: training_modules_001
Revises: 20260205_add_dom_tables
Create Date: 2026-02-05

Tables created:
- training_modules: Admin-created training modules for partners
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = 'training_modules_001'
down_revision = '20260205_add_dom_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists (for idempotent migrations)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'training_modules' not in existing_tables:
        op.create_table(
            'training_modules',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('module_code', sa.String(50), nullable=False, unique=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),

            # Module Type
            sa.Column('training_type', sa.String(50), default='VIDEO'),

            # Content
            sa.Column('content_url', sa.String(500), nullable=True),
            sa.Column('thumbnail_url', sa.String(500), nullable=True),
            sa.Column('duration_minutes', sa.Integer(), default=0),

            # Requirements
            sa.Column('is_mandatory', sa.Boolean(), default=False),
            sa.Column('passing_score', sa.Integer(), nullable=True),
            sa.Column('prerequisites', JSONB, nullable=True),

            # Status
            sa.Column('status', sa.String(50), default='DRAFT'),
            sa.Column('is_active', sa.Boolean(), default=True),

            # Display Order
            sa.Column('sort_order', sa.Integer(), default=0),
            sa.Column('category', sa.String(100), nullable=True),

            # Timestamps
            sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )

        # Create index on module_code
        op.create_index('ix_training_modules_module_code', 'training_modules', ['module_code'])
        op.create_index('ix_training_modules_status', 'training_modules', ['status'])

        print("Created table: training_modules")
    else:
        print("Table training_modules already exists, skipping creation")


def downgrade():
    # Drop indexes first
    op.drop_index('ix_training_modules_status', table_name='training_modules')
    op.drop_index('ix_training_modules_module_code', table_name='training_modules')

    # Drop table
    op.drop_table('training_modules')
