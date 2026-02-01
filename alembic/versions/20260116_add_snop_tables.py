"""add_snop_tables

S&OP (Sales and Operations Planning) module tables:
- demand_forecasts: AI-generated and manual demand forecasts
- forecast_adjustments: Manual adjustments to forecasts with approval workflow
- supply_plans: Production and procurement planning
- snop_scenarios: What-if scenario simulations
- external_factors: Promotions, seasonality, and other demand influencers
- inventory_optimizations: AI-recommended safety stock and reorder points
- snop_meetings: Consensus planning meeting records

Revision ID: add_snop_tables
Revises: fd392df33600
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_snop_tables'
down_revision: Union[str, None] = 'fd392df33600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE forecast_granularity AS ENUM ('DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE forecast_level AS ENUM ('SKU', 'CATEGORY', 'REGION', 'CHANNEL', 'COMPANY');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE forecast_status AS ENUM ('DRAFT', 'PENDING_REVIEW', 'UNDER_REVIEW', 'ADJUSTMENT_REQUESTED', 'APPROVED', 'REJECTED', 'SUPERSEDED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE forecast_algorithm AS ENUM ('HOLT_WINTERS', 'PROPHET', 'ARIMA', 'XGBOOST', 'LIGHTGBM', 'LSTM', 'ENSEMBLE', 'MANUAL');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE supply_plan_status AS ENUM ('DRAFT', 'SUBMITTED', 'APPROVED', 'IN_EXECUTION', 'COMPLETED', 'CANCELLED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE scenario_status AS ENUM ('DRAFT', 'RUNNING', 'COMPLETED', 'FAILED', 'ARCHIVED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE external_factor_type AS ENUM ('PROMOTION', 'SEASONAL', 'WEATHER', 'ECONOMIC', 'COMPETITOR', 'EVENT', 'PRICE_CHANGE', 'SUPPLY_DISRUPTION');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create demand_forecasts table
    op.execute("""
        CREATE TABLE IF NOT EXISTS demand_forecasts (
            id UUID PRIMARY KEY,
            forecast_code VARCHAR(50) NOT NULL UNIQUE,
            forecast_name VARCHAR(200) NOT NULL,
            forecast_level forecast_level NOT NULL DEFAULT 'SKU',
            granularity forecast_granularity NOT NULL DEFAULT 'WEEKLY',
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
            warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
            region_id UUID REFERENCES regions(id) ON DELETE SET NULL,
            channel VARCHAR(50),
            forecast_start_date DATE NOT NULL,
            forecast_end_date DATE NOT NULL,
            forecast_horizon_days INTEGER DEFAULT 90,
            forecast_data JSONB NOT NULL DEFAULT '[]',
            total_forecasted_qty NUMERIC(15, 2) DEFAULT 0,
            avg_daily_demand NUMERIC(15, 4) DEFAULT 0,
            peak_demand NUMERIC(15, 2) DEFAULT 0,
            algorithm_used forecast_algorithm DEFAULT 'ENSEMBLE',
            model_parameters JSONB,
            mape FLOAT,
            mae FLOAT,
            rmse FLOAT,
            forecast_bias FLOAT,
            confidence_level FLOAT DEFAULT 0.95,
            external_factors_json JSONB,
            status forecast_status DEFAULT 'DRAFT',
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            reviewed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            approved_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            submitted_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            approved_at TIMESTAMP,
            version INTEGER DEFAULT 1,
            parent_forecast_id UUID REFERENCES demand_forecasts(id) ON DELETE SET NULL,
            is_active BOOLEAN DEFAULT TRUE,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS ix_demand_forecasts_product_date ON demand_forecasts(product_id, forecast_start_date);
        CREATE INDEX IF NOT EXISTS ix_demand_forecasts_category_date ON demand_forecasts(category_id, forecast_start_date);
        CREATE INDEX IF NOT EXISTS ix_demand_forecasts_status ON demand_forecasts(status);
        CREATE INDEX IF NOT EXISTS ix_demand_forecasts_level_granularity ON demand_forecasts(forecast_level, granularity);
    """)

    # Create forecast_adjustments table
    op.execute("""
        CREATE TABLE IF NOT EXISTS forecast_adjustments (
            id UUID PRIMARY KEY,
            forecast_id UUID NOT NULL REFERENCES demand_forecasts(id) ON DELETE CASCADE,
            adjustment_date DATE NOT NULL,
            original_qty NUMERIC(15, 2) NOT NULL,
            adjusted_qty NUMERIC(15, 2) NOT NULL,
            adjustment_pct FLOAT NOT NULL,
            adjustment_reason VARCHAR(100) NOT NULL,
            justification TEXT,
            status forecast_status DEFAULT 'PENDING_REVIEW',
            adjusted_by_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            approved_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            approved_at TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_forecast_adjustments_forecast ON forecast_adjustments(forecast_id);
    """)

    # Create supply_plans table
    op.execute("""
        CREATE TABLE IF NOT EXISTS supply_plans (
            id UUID PRIMARY KEY,
            plan_code VARCHAR(50) NOT NULL UNIQUE,
            plan_name VARCHAR(200) NOT NULL,
            forecast_id UUID REFERENCES demand_forecasts(id) ON DELETE SET NULL,
            plan_start_date DATE NOT NULL,
            plan_end_date DATE NOT NULL,
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
            planned_production_qty NUMERIC(15, 2) DEFAULT 0,
            planned_procurement_qty NUMERIC(15, 2) DEFAULT 0,
            production_capacity NUMERIC(15, 2) DEFAULT 0,
            capacity_utilization_pct FLOAT DEFAULT 0,
            vendor_id UUID REFERENCES vendors(id) ON DELETE SET NULL,
            lead_time_days INTEGER DEFAULT 0,
            schedule_data JSONB NOT NULL DEFAULT '[]',
            status supply_plan_status DEFAULT 'DRAFT',
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            approved_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            approved_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS ix_supply_plans_forecast ON supply_plans(forecast_id);
        CREATE INDEX IF NOT EXISTS ix_supply_plans_product ON supply_plans(product_id);
    """)

    # Create snop_scenarios table
    op.execute("""
        CREATE TABLE IF NOT EXISTS snop_scenarios (
            id UUID PRIMARY KEY,
            scenario_code VARCHAR(50) NOT NULL UNIQUE,
            scenario_name VARCHAR(200) NOT NULL,
            description TEXT,
            base_scenario_id UUID REFERENCES snop_scenarios(id) ON DELETE SET NULL,
            demand_multiplier FLOAT DEFAULT 1.0,
            supply_constraint_pct FLOAT DEFAULT 100.0,
            lead_time_multiplier FLOAT DEFAULT 1.0,
            price_change_pct FLOAT DEFAULT 0.0,
            assumptions JSONB NOT NULL DEFAULT '{}',
            simulation_start_date DATE NOT NULL,
            simulation_end_date DATE NOT NULL,
            results JSONB,
            projected_revenue NUMERIC(18, 2),
            projected_margin NUMERIC(18, 2),
            stockout_probability FLOAT,
            service_level_pct FLOAT,
            status scenario_status DEFAULT 'DRAFT',
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );

        CREATE INDEX IF NOT EXISTS ix_snop_scenarios_status ON snop_scenarios(status);
    """)

    # Create external_factors table
    op.execute("""
        CREATE TABLE IF NOT EXISTS external_factors (
            id UUID PRIMARY KEY,
            factor_code VARCHAR(50) NOT NULL UNIQUE,
            factor_name VARCHAR(200) NOT NULL,
            factor_type external_factor_type NOT NULL,
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
            region_id UUID REFERENCES regions(id) ON DELETE SET NULL,
            applies_to_all BOOLEAN DEFAULT FALSE,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            impact_multiplier FLOAT DEFAULT 1.0,
            impact_absolute NUMERIC(15, 2),
            metadata_json JSONB,
            is_active BOOLEAN DEFAULT TRUE,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_external_factors_type_dates ON external_factors(factor_type, start_date, end_date);
        CREATE INDEX IF NOT EXISTS ix_external_factors_product ON external_factors(product_id);
    """)

    # Create inventory_optimizations table
    op.execute("""
        CREATE TABLE IF NOT EXISTS inventory_optimizations (
            id UUID PRIMARY KEY,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
            recommended_safety_stock NUMERIC(15, 2) NOT NULL,
            recommended_reorder_point NUMERIC(15, 2) NOT NULL,
            recommended_order_qty NUMERIC(15, 2) NOT NULL,
            current_safety_stock NUMERIC(15, 2) DEFAULT 0,
            current_reorder_point NUMERIC(15, 2) DEFAULT 0,
            avg_daily_demand NUMERIC(15, 4) NOT NULL,
            demand_std_dev NUMERIC(15, 4) NOT NULL,
            lead_time_days INTEGER NOT NULL,
            lead_time_std_dev FLOAT DEFAULT 0,
            service_level_target FLOAT DEFAULT 0.95,
            holding_cost_pct FLOAT DEFAULT 0.25,
            ordering_cost NUMERIC(15, 2) DEFAULT 100,
            stockout_cost NUMERIC(15, 2),
            expected_stockout_rate FLOAT DEFAULT 0,
            expected_inventory_turns FLOAT DEFAULT 0,
            expected_holding_cost NUMERIC(15, 2) DEFAULT 0,
            calculation_details JSONB,
            valid_from DATE NOT NULL,
            valid_until DATE NOT NULL,
            is_applied BOOLEAN DEFAULT FALSE,
            applied_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(product_id, warehouse_id, valid_from)
        );

        CREATE INDEX IF NOT EXISTS ix_inventory_opt_product_warehouse ON inventory_optimizations(product_id, warehouse_id);
    """)

    # Create snop_meetings table
    op.execute("""
        CREATE TABLE IF NOT EXISTS snop_meetings (
            id UUID PRIMARY KEY,
            meeting_code VARCHAR(50) NOT NULL UNIQUE,
            meeting_title VARCHAR(200) NOT NULL,
            meeting_date TIMESTAMP NOT NULL,
            planning_period_start DATE NOT NULL,
            planning_period_end DATE NOT NULL,
            participants JSONB NOT NULL DEFAULT '[]',
            agenda TEXT,
            meeting_notes TEXT,
            forecasts_reviewed JSONB NOT NULL DEFAULT '[]',
            decisions JSONB,
            action_items JSONB,
            is_completed BOOLEAN DEFAULT FALSE,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_snop_meetings_date ON snop_meetings(meeting_date);
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.execute("DROP TABLE IF EXISTS snop_meetings CASCADE;")
    op.execute("DROP TABLE IF EXISTS inventory_optimizations CASCADE;")
    op.execute("DROP TABLE IF EXISTS external_factors CASCADE;")
    op.execute("DROP TABLE IF EXISTS snop_scenarios CASCADE;")
    op.execute("DROP TABLE IF EXISTS supply_plans CASCADE;")
    op.execute("DROP TABLE IF EXISTS forecast_adjustments CASCADE;")
    op.execute("DROP TABLE IF EXISTS demand_forecasts CASCADE;")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS external_factor_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS scenario_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS supply_plan_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS forecast_algorithm CASCADE;")
    op.execute("DROP TYPE IF EXISTS forecast_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS forecast_level CASCADE;")
    op.execute("DROP TYPE IF EXISTS forecast_granularity CASCADE;")
