-- FAQ CMS Tables Migration
-- Creates cms_faq_categories and cms_faq_items tables for FAQ management

-- ==================== FAQ Categories Table ====================
CREATE TABLE IF NOT EXISTS cms_faq_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Content
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(500),
    icon VARCHAR(50) NOT NULL DEFAULT 'HelpCircle',  -- Lucide icon name
    icon_color VARCHAR(50),  -- Optional icon color

    -- Display
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for cms_faq_categories
CREATE INDEX IF NOT EXISTS idx_faq_categories_sort_order ON cms_faq_categories(sort_order);
CREATE INDEX IF NOT EXISTS idx_faq_categories_is_active ON cms_faq_categories(is_active);
CREATE INDEX IF NOT EXISTS idx_faq_categories_slug ON cms_faq_categories(slug);

-- ==================== FAQ Items Table ====================
CREATE TABLE IF NOT EXISTS cms_faq_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Category relationship
    category_id UUID NOT NULL REFERENCES cms_faq_categories(id) ON DELETE CASCADE,

    -- Content
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    keywords JSONB DEFAULT '[]'::jsonb,  -- Array of search keywords

    -- Display
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_featured BOOLEAN NOT NULL DEFAULT false,  -- Show in featured/popular section
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Stats
    view_count INTEGER NOT NULL DEFAULT 0,
    helpful_count INTEGER NOT NULL DEFAULT 0,  -- Users who found it helpful

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for cms_faq_items
CREATE INDEX IF NOT EXISTS idx_faq_items_category_id ON cms_faq_items(category_id);
CREATE INDEX IF NOT EXISTS idx_faq_items_sort_order ON cms_faq_items(sort_order);
CREATE INDEX IF NOT EXISTS idx_faq_items_is_active ON cms_faq_items(is_active);
CREATE INDEX IF NOT EXISTS idx_faq_items_is_featured ON cms_faq_items(is_featured);

-- ==================== Trigger for updated_at ====================
-- Update timestamp trigger for categories
CREATE OR REPLACE FUNCTION update_faq_category_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_faq_category_updated_at
    BEFORE UPDATE ON cms_faq_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_faq_category_updated_at();

-- Update timestamp trigger for items
CREATE OR REPLACE FUNCTION update_faq_item_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_faq_item_updated_at
    BEFORE UPDATE ON cms_faq_items
    FOR EACH ROW
    EXECUTE FUNCTION update_faq_item_updated_at();

-- ==================== Comments ====================
COMMENT ON TABLE cms_faq_categories IS 'FAQ categories for organizing FAQ items by topic';
COMMENT ON TABLE cms_faq_items IS 'Individual FAQ questions and answers';
COMMENT ON COLUMN cms_faq_categories.icon IS 'Lucide icon name (e.g., Package, Truck, CreditCard)';
COMMENT ON COLUMN cms_faq_items.keywords IS 'JSON array of search keywords for better discoverability';
COMMENT ON COLUMN cms_faq_items.helpful_count IS 'Number of users who marked this FAQ as helpful';
