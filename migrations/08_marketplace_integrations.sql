-- ============================================================
-- MIGRATION PART 8: MARKETPLACE INTEGRATIONS
-- API Integration credentials for Amazon, Flipkart, etc.
-- ============================================================

-- Marketplace Integrations Table
CREATE TABLE IF NOT EXISTS marketplace_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Marketplace
    marketplace_type VARCHAR(50) NOT NULL,  -- AMAZON, FLIPKART, MEESHO, SNAPDEAL

    -- Credentials (encrypted)
    client_id VARCHAR(255),
    client_secret TEXT,  -- Encrypted
    refresh_token TEXT,  -- Encrypted (Amazon)
    api_key TEXT,        -- Encrypted

    -- Seller Info
    seller_id VARCHAR(100),
    marketplace_seller_name VARCHAR(255),

    -- Settings
    is_sandbox BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,

    -- Sync Settings
    auto_sync_orders BOOLEAN DEFAULT TRUE,
    auto_sync_inventory BOOLEAN DEFAULT TRUE,
    sync_interval_minutes INTEGER DEFAULT 30,

    -- Last Sync Timestamps
    last_order_sync_at TIMESTAMP,
    last_inventory_sync_at TIMESTAMP,
    last_sync_at TIMESTAMP,
    last_sync_status VARCHAR(50),
    last_sync_error TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id),

    -- Unique constraint
    CONSTRAINT uq_company_marketplace UNIQUE (company_id, marketplace_type)
);

CREATE INDEX IF NOT EXISTS idx_marketplace_integrations_company ON marketplace_integrations(company_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_integrations_type ON marketplace_integrations(marketplace_type);
CREATE INDEX IF NOT EXISTS idx_marketplace_integrations_active ON marketplace_integrations(is_active);

SELECT 'Part 8: Marketplace integrations table created successfully!' AS result;
