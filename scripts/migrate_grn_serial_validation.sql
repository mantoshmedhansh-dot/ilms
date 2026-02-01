-- Migration: Add GRN serial validation and force GRN fields
-- Date: 2026-01-24
-- Purpose: Enable serial validation in GRN flow and forced GRN capability

-- ==================== 1. Add new columns to goods_receipt_notes ====================

-- Forced GRN fields
ALTER TABLE goods_receipt_notes
ADD COLUMN IF NOT EXISTS is_forced BOOLEAN DEFAULT FALSE;

ALTER TABLE goods_receipt_notes
ADD COLUMN IF NOT EXISTS force_reason TEXT;

ALTER TABLE goods_receipt_notes
ADD COLUMN IF NOT EXISTS forced_by UUID REFERENCES users(id) ON DELETE SET NULL;

-- Serial validation status
ALTER TABLE goods_receipt_notes
ADD COLUMN IF NOT EXISTS serial_validation_status VARCHAR(50);

COMMENT ON COLUMN goods_receipt_notes.serial_validation_status IS 'VALIDATED, PARTIAL_MATCH, NO_MATCH, SKIPPED';

ALTER TABLE goods_receipt_notes
ADD COLUMN IF NOT EXISTS serial_mismatch_details JSONB;

COMMENT ON COLUMN goods_receipt_notes.serial_mismatch_details IS 'Details of serial mismatches if any';

-- Stock items created flag
ALTER TABLE goods_receipt_notes
ADD COLUMN IF NOT EXISTS stock_items_created BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN goods_receipt_notes.stock_items_created IS 'True after stock_items have been created from this GRN';

-- ==================== 2. Add grn_number column to stock_items if missing ====================

ALTER TABLE stock_items
ADD COLUMN IF NOT EXISTS grn_number VARCHAR(50);

-- ==================== 3. Create the grn:force_receive permission ====================

-- First, get or create the Procurement module
INSERT INTO modules (id, name, code, description, icon, display_order, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'Procurement',
    'procurement',
    'Purchase Orders, GRN, Vendor Management',
    'ShoppingCart',
    50,
    true,
    NOW(),
    NOW()
)
ON CONFLICT (code) DO NOTHING;

-- Get the module ID
DO $$
DECLARE
    v_module_id UUID;
    v_permission_id UUID;
    v_supply_chain_head_role_id UUID;
BEGIN
    -- Get procurement module ID
    SELECT id INTO v_module_id FROM modules WHERE code = 'procurement';

    -- Create the permission if it doesn't exist
    INSERT INTO permissions (id, code, name, description, module_id, resource, action, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'grn:force_receive',
        'Force GRN Receive',
        'Allows bypassing serial validation during GRN when serials do not match PO. Only for Supply Chain Head.',
        v_module_id,
        'grn',
        'force_receive',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (code) DO UPDATE SET
        description = EXCLUDED.description,
        updated_at = NOW();

    -- Get the permission ID
    SELECT id INTO v_permission_id FROM permissions WHERE code = 'grn:force_receive';

    -- Find the Supply Chain Head role (or Director level role)
    SELECT id INTO v_supply_chain_head_role_id
    FROM roles
    WHERE code IN ('SUPPLY_CHAIN_HEAD', 'DIRECTOR', 'SUPER_ADMIN')
    ORDER BY
        CASE code
            WHEN 'SUPPLY_CHAIN_HEAD' THEN 1
            WHEN 'DIRECTOR' THEN 2
            WHEN 'SUPER_ADMIN' THEN 3
        END
    LIMIT 1;

    -- Assign permission to the role if found
    IF v_supply_chain_head_role_id IS NOT NULL AND v_permission_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id, created_at)
        VALUES (v_supply_chain_head_role_id, v_permission_id, NOW())
        ON CONFLICT (role_id, permission_id) DO NOTHING;

        RAISE NOTICE 'Permission grn:force_receive assigned to role %', v_supply_chain_head_role_id;
    ELSE
        RAISE NOTICE 'Could not find appropriate role for grn:force_receive permission. Please assign manually.';
    END IF;
END $$;

-- ==================== 4. Create index for performance ====================

CREATE INDEX IF NOT EXISTS ix_grn_is_forced ON goods_receipt_notes(is_forced) WHERE is_forced = true;
CREATE INDEX IF NOT EXISTS ix_grn_serial_validation ON goods_receipt_notes(serial_validation_status);
CREATE INDEX IF NOT EXISTS ix_grn_stock_items_created ON goods_receipt_notes(stock_items_created);

-- ==================== 5. Verify the changes ====================

SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'goods_receipt_notes'
AND column_name IN ('is_forced', 'force_reason', 'forced_by', 'serial_validation_status', 'serial_mismatch_details', 'stock_items_created')
ORDER BY column_name;

SELECT code, name, description FROM permissions WHERE code = 'grn:force_receive';

-- ==================== 6. Summary ====================
--
-- New GRN Flow:
-- 1. Create GRN with serial_numbers in items
-- 2. Call /grn/{id}/validate-serials to check serials against PO
-- 3. If valid: Call /grn/{id}/accept to accept and create stock items
-- 4. If invalid: Call /grn/{id}/force (requires grn:force_receive permission) then /grn/{id}/accept
--
-- Stock Item Creation:
-- - On GRN accept, stock_items are created from po_serials
-- - po_serials.status updated to RECEIVED
-- - po_serials.stock_item_id linked to new stock_item
-- - inventory_summary updated with quantities
-- - stock_movements created for audit trail
