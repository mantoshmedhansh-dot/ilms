"""Seed inventory for Delhi warehouse to enable D2C order allocation

Revision ID: 20260120_delhi_inv
Revises: 20260120_coupons
Create Date: 2026-01-20

This migration adds inventory to the Delhi warehouse for D2C testing.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime
import uuid

# revision identifiers, used by Alembic.
revision: str = '20260120_delhi_inv'
down_revision: Union[str, None] = '20260120_coupons'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add inventory to Delhi warehouse for D2C products."""
    connection = op.get_bind()

    # Get Delhi warehouse ID
    warehouse_result = connection.execute(
        sa.text("SELECT id FROM warehouses WHERE code = 'WH-DEL-001' LIMIT 1")
    )
    warehouse_row = warehouse_result.fetchone()

    if not warehouse_row:
        print("WARNING: Delhi warehouse (WH-DEL-001) not found. Skipping inventory seed.")
        return

    warehouse_id = warehouse_row[0]
    print(f"Found Delhi warehouse: {warehouse_id}")

    # Get products that are active for D2C
    products_result = connection.execute(
        sa.text("""
            SELECT id, name, sku
            FROM products
            WHERE is_active = true
            AND storefront_visible = true
            LIMIT 20
        """)
    )
    products = products_result.fetchall()

    if not products:
        print("WARNING: No active D2C products found. Skipping inventory seed.")
        return

    print(f"Found {len(products)} active products for D2C")

    # Add inventory for each product
    for product in products:
        product_id = product[0]
        product_name = product[1]
        product_sku = product[2]

        # Check if inventory already exists
        existing = connection.execute(
            sa.text("""
                SELECT id, available_quantity
                FROM inventory_summary
                WHERE warehouse_id = :warehouse_id AND product_id = :product_id
            """),
            {"warehouse_id": warehouse_id, "product_id": product_id}
        ).fetchone()

        if existing:
            # Update existing inventory if it's low
            if existing[1] < 10:
                connection.execute(
                    sa.text("""
                        UPDATE inventory_summary
                        SET total_quantity = total_quantity + 100,
                            available_quantity = available_quantity + 100,
                            updated_at = :now
                        WHERE id = :id
                    """),
                    {"id": existing[0], "now": datetime.utcnow()}
                )
                print(f"  Updated inventory for {product_sku}: +100 units")
            else:
                print(f"  Inventory exists for {product_sku}: {existing[1]} units")
        else:
            # Create new inventory record
            inv_id = str(uuid.uuid4())
            connection.execute(
                sa.text("""
                    INSERT INTO inventory_summary
                    (id, warehouse_id, product_id, total_quantity, available_quantity,
                     reserved_quantity, allocated_quantity, created_at, updated_at)
                    VALUES
                    (:id, :warehouse_id, :product_id, 100, 100, 0, 0, :now, :now)
                """),
                {
                    "id": inv_id,
                    "warehouse_id": warehouse_id,
                    "product_id": product_id,
                    "now": datetime.utcnow()
                }
            )
            print(f"  Created inventory for {product_sku}: 100 units")

    print("Inventory seed complete!")


def downgrade() -> None:
    """Remove seeded inventory (optional - we don't remove inventory on downgrade)."""
    # Don't remove inventory on downgrade as it could affect real data
    pass
