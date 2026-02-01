-- Create cms_mega_menu_items table for D2C storefront navigation
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS cms_mega_menu_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    image_url VARCHAR(500),
    menu_type VARCHAR(20) NOT NULL DEFAULT 'CATEGORY',
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    url VARCHAR(500),
    target VARCHAR(20) NOT NULL DEFAULT '_self',
    show_subcategories BOOLEAN NOT NULL DEFAULT TRUE,
    subcategory_ids JSONB,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_highlighted BOOLEAN NOT NULL DEFAULT FALSE,
    highlight_text VARCHAR(20),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

-- Create index for sorting and filtering
CREATE INDEX IF NOT EXISTS idx_cms_mega_menu_items_sort ON cms_mega_menu_items(sort_order);
CREATE INDEX IF NOT EXISTS idx_cms_mega_menu_items_active ON cms_mega_menu_items(is_active);
CREATE INDEX IF NOT EXISTS idx_cms_mega_menu_items_company ON cms_mega_menu_items(company_id);

-- Add comment to table
COMMENT ON TABLE cms_mega_menu_items IS 'Mega menu items for D2C storefront navigation. Allows admin to control which categories appear in the mega menu.';
