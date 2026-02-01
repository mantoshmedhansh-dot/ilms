"""recreate_d2c_rate_card_tables

Revision ID: fd392df33600
Revises: 9dd21f7889b9
Create Date: 2026-01-15 10:33:40.597633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fd392df33600'
down_revision: Union[str, None] = '9dd21f7889b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create D2C Rate Cards table using raw SQL to avoid enum creation issues
    op.execute("""
        CREATE TABLE IF NOT EXISTS d2c_rate_cards (
            id UUID PRIMARY KEY,
            transporter_id UUID NOT NULL REFERENCES transporters(id) ON DELETE CASCADE,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            service_type d2cservicetype NOT NULL DEFAULT 'STANDARD',
            zone_type VARCHAR(20) NOT NULL DEFAULT 'DISTANCE',
            effective_from DATE NOT NULL,
            effective_to DATE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_d2c_rate_card UNIQUE (transporter_id, code, effective_from)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_d2c_rate_cards_code ON d2c_rate_cards(code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_d2c_rate_cards_transporter_id ON d2c_rate_cards(transporter_id)")

    # Create D2C Surcharges table
    op.execute("""
        CREATE TABLE IF NOT EXISTS d2c_surcharges (
            id UUID PRIMARY KEY,
            rate_card_id UUID NOT NULL REFERENCES d2c_rate_cards(id) ON DELETE CASCADE,
            surcharge_type surchargetype NOT NULL,
            calculation_type calculationtype NOT NULL DEFAULT 'PERCENTAGE',
            value NUMERIC(10, 4) NOT NULL,
            min_amount NUMERIC(10, 2),
            max_amount NUMERIC(10, 2),
            applies_to_cod BOOLEAN NOT NULL DEFAULT TRUE,
            applies_to_prepaid BOOLEAN NOT NULL DEFAULT TRUE,
            zone VARCHAR(20),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            effective_from DATE,
            effective_to DATE,
            CONSTRAINT uq_d2c_surcharge UNIQUE (rate_card_id, surcharge_type, zone)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_d2c_surcharges_rate_card_id ON d2c_surcharges(rate_card_id)")

    # Create D2C Weight Slabs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS d2c_weight_slabs (
            id UUID PRIMARY KEY,
            rate_card_id UUID NOT NULL REFERENCES d2c_rate_cards(id) ON DELETE CASCADE,
            zone VARCHAR(20) NOT NULL,
            min_weight_kg NUMERIC(10, 3) NOT NULL DEFAULT 0,
            max_weight_kg NUMERIC(10, 3) NOT NULL,
            base_rate NUMERIC(10, 2) NOT NULL,
            additional_rate_per_kg NUMERIC(10, 2) NOT NULL DEFAULT 0,
            additional_weight_unit_kg NUMERIC(10, 3) NOT NULL DEFAULT 0.5,
            cod_available BOOLEAN NOT NULL DEFAULT TRUE,
            prepaid_available BOOLEAN NOT NULL DEFAULT TRUE,
            estimated_days_min INTEGER,
            estimated_days_max INTEGER,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_d2c_weight_slab UNIQUE (rate_card_id, zone, min_weight_kg)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_d2c_weight_slab_lookup ON d2c_weight_slabs(rate_card_id, zone, min_weight_kg)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_d2c_weight_slabs_rate_card_id ON d2c_weight_slabs(rate_card_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_d2c_weight_slabs_rate_card_id")
    op.execute("DROP INDEX IF EXISTS idx_d2c_weight_slab_lookup")
    op.execute("DROP TABLE IF EXISTS d2c_weight_slabs")
    op.execute("DROP INDEX IF EXISTS ix_d2c_surcharges_rate_card_id")
    op.execute("DROP TABLE IF EXISTS d2c_surcharges")
    op.execute("DROP INDEX IF EXISTS ix_d2c_rate_cards_transporter_id")
    op.execute("DROP INDEX IF EXISTS ix_d2c_rate_cards_code")
    op.execute("DROP TABLE IF EXISTS d2c_rate_cards")
