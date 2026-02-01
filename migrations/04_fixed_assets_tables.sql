-- ============================================================
-- MIGRATION PART 4: FIXED ASSETS TABLES
-- Run AFTER Part 1 (enum types)
-- ============================================================

-- Asset Categories table
CREATE TABLE IF NOT EXISTS asset_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    depreciation_method depreciationmethod DEFAULT 'SLM',
    depreciation_rate DECIMAL(5,2) NOT NULL,
    useful_life_years INTEGER NOT NULL,

    asset_account_id UUID,
    depreciation_account_id UUID,
    expense_account_id UUID,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_categories_code ON asset_categories(code);

-- Assets table
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_code VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category_id UUID NOT NULL REFERENCES asset_categories(id) ON DELETE RESTRICT,

    -- Serial/Model Info
    serial_number VARCHAR(100),
    model_number VARCHAR(100),
    manufacturer VARCHAR(100),

    -- Location
    warehouse_id UUID,
    location_details VARCHAR(200),
    custodian_employee_id UUID,
    department_id UUID,

    -- Purchase Details
    purchase_date DATE NOT NULL,
    purchase_price DECIMAL(14,2) NOT NULL,
    purchase_invoice_no VARCHAR(50),
    vendor_id UUID,
    po_number VARCHAR(50),

    -- Capitalization
    capitalization_date DATE NOT NULL,
    installation_cost DECIMAL(12,2) DEFAULT 0,
    other_costs DECIMAL(12,2) DEFAULT 0,
    capitalized_value DECIMAL(14,2) NOT NULL,

    -- Depreciation (overrides)
    depreciation_method depreciationmethod,
    depreciation_rate DECIMAL(5,2),
    useful_life_years INTEGER,
    salvage_value DECIMAL(12,2) DEFAULT 0,

    -- Current Values
    accumulated_depreciation DECIMAL(14,2) DEFAULT 0,
    current_book_value DECIMAL(14,2) NOT NULL,
    last_depreciation_date DATE,

    -- Warranty
    warranty_start_date DATE,
    warranty_end_date DATE,
    warranty_details TEXT,

    -- Insurance
    insured BOOLEAN DEFAULT FALSE,
    insurance_policy_no VARCHAR(50),
    insurance_value DECIMAL(14,2),
    insurance_expiry DATE,

    -- Status
    status assetstatus DEFAULT 'ACTIVE',

    -- Disposal
    disposal_date DATE,
    disposal_price DECIMAL(14,2),
    disposal_reason TEXT,
    gain_loss_on_disposal DECIMAL(14,2),

    -- Documents
    documents JSONB,
    images JSONB,
    notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_code ON assets(asset_code);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category_id);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_warehouse ON assets(warehouse_id);

-- Depreciation Entries table
CREATE TABLE IF NOT EXISTS depreciation_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,

    period_date DATE NOT NULL,
    financial_year VARCHAR(10) NOT NULL,

    opening_book_value DECIMAL(14,2) NOT NULL,
    depreciation_method depreciationmethod NOT NULL,
    depreciation_rate DECIMAL(5,2) NOT NULL,
    depreciation_amount DECIMAL(12,2) NOT NULL,
    closing_book_value DECIMAL(14,2) NOT NULL,
    accumulated_depreciation DECIMAL(14,2) NOT NULL,

    journal_entry_id UUID,
    is_posted BOOLEAN DEFAULT FALSE,

    processed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    processed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(asset_id, period_date)
);

CREATE INDEX IF NOT EXISTS idx_depreciation_entries_asset ON depreciation_entries(asset_id);
CREATE INDEX IF NOT EXISTS idx_depreciation_entries_period ON depreciation_entries(period_date);
CREATE INDEX IF NOT EXISTS idx_depreciation_entries_fy ON depreciation_entries(financial_year);

-- Asset Transfers table
CREATE TABLE IF NOT EXISTS asset_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    transfer_number VARCHAR(30) UNIQUE NOT NULL,

    -- From Location
    from_warehouse_id UUID,
    from_department_id UUID,
    from_custodian_id UUID,
    from_location_details VARCHAR(200),

    -- To Location
    to_warehouse_id UUID,
    to_department_id UUID,
    to_custodian_id UUID,
    to_location_details VARCHAR(200),

    transfer_date DATE NOT NULL,
    reason TEXT,

    status assettransferstatus DEFAULT 'PENDING',

    requested_by UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP,
    completed_at TIMESTAMP,
    received_by UUID REFERENCES users(id) ON DELETE SET NULL,

    notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_transfers_asset ON asset_transfers(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_transfers_status ON asset_transfers(status);

-- Asset Maintenance table
CREATE TABLE IF NOT EXISTS asset_maintenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    maintenance_number VARCHAR(30) UNIQUE NOT NULL,

    maintenance_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,

    scheduled_date DATE NOT NULL,
    started_date DATE,
    completed_date DATE,

    estimated_cost DECIMAL(12,2) DEFAULT 0,
    actual_cost DECIMAL(12,2) DEFAULT 0,

    vendor_id UUID,
    vendor_invoice_no VARCHAR(50),

    status maintenancestatus DEFAULT 'SCHEDULED',

    findings TEXT,
    parts_replaced TEXT,
    recommendations TEXT,

    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    documents JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_maintenance_asset ON asset_maintenance(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_maintenance_status ON asset_maintenance(status);

SELECT 'Part 4: Fixed assets tables created successfully!' AS result;
