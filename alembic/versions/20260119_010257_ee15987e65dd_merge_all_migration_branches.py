"""Merge all migration branches

Revision ID: ee15987e65dd
Revises: add_document_sequences, 20260117_add_coupons, 20260117_customer_otps, 20260117_reviews, 20260117_razorpay, 20260117_add_returns_refunds, add_uppercase_check_constraints, add_wishlist_001, 20260119_product_costs
Create Date: 2026-01-19 01:02:57.951230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee15987e65dd'
down_revision: Union[str, None] = ('add_document_sequences', '20260117_add_coupons', '20260117_customer_otps', '20260117_reviews', '20260117_razorpay', '20260117_add_returns_refunds', 'add_uppercase_check_constraints', 'add_wishlist_001', '20260119_product_costs')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
