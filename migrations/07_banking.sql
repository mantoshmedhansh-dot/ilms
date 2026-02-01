-- ============================================================
-- MIGRATION PART 7: BANKING MODULE
-- Bank Accounts, Transactions, and Reconciliation
-- ============================================================

-- Bank Transaction Type Enum
DO $$ BEGIN
    CREATE TYPE bank_transaction_type AS ENUM ('CREDIT', 'DEBIT');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Bank Accounts Table
CREATE TABLE IF NOT EXISTS bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Account Details
    account_name VARCHAR(200) NOT NULL,
    account_number VARCHAR(50) NOT NULL UNIQUE,
    bank_name VARCHAR(200) NOT NULL,
    branch_name VARCHAR(200),
    ifsc_code VARCHAR(20),
    swift_code VARCHAR(20),

    -- Account Type
    account_type VARCHAR(50) DEFAULT 'CURRENT',

    -- Balances
    opening_balance DECIMAL(15, 2) DEFAULT 0,
    current_balance DECIMAL(15, 2) DEFAULT 0,

    -- Linked Ledger Account
    ledger_account_id UUID REFERENCES ledger_accounts(id),

    -- Credit Limits (for CC/OD accounts)
    credit_limit DECIMAL(15, 2),
    available_limit DECIMAL(15, 2),

    -- Last Reconciliation
    last_reconciled_date DATE,
    last_reconciled_balance DECIMAL(15, 2),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_bank_accounts_bank ON bank_accounts(bank_name);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_active ON bank_accounts(is_active);

-- Bank Transactions Table
CREATE TABLE IF NOT EXISTS bank_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Parent Account
    bank_account_id UUID NOT NULL REFERENCES bank_accounts(id),

    -- Transaction Details
    transaction_date DATE NOT NULL,
    value_date DATE,
    description TEXT NOT NULL,
    reference_number VARCHAR(100),
    cheque_number VARCHAR(20),

    -- Transaction Type
    transaction_type bank_transaction_type NOT NULL,

    -- Amounts
    amount DECIMAL(15, 2) NOT NULL,
    debit_amount DECIMAL(15, 2) DEFAULT 0,
    credit_amount DECIMAL(15, 2) DEFAULT 0,
    running_balance DECIMAL(15, 2),

    -- Reconciliation
    is_reconciled BOOLEAN DEFAULT FALSE,
    reconciled_at TIMESTAMP,
    matched_journal_entry_id UUID REFERENCES journal_entries(id),
    reconciliation_status VARCHAR(50) DEFAULT 'PENDING',

    -- Import Tracking
    source VARCHAR(50) DEFAULT 'IMPORT',
    import_reference VARCHAR(255),
    import_batch_id UUID,

    -- Categorization
    category VARCHAR(100),
    party_name VARCHAR(200),
    party_id UUID,

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_account ON bank_transactions(bank_account_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_date ON bank_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_reconciled ON bank_transactions(is_reconciled);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_type ON bank_transactions(transaction_type);

-- Bank Reconciliation Sessions Table
CREATE TABLE IF NOT EXISTS bank_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Account
    bank_account_id UUID NOT NULL REFERENCES bank_accounts(id),

    -- Period
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    -- Balances
    statement_opening_balance DECIMAL(15, 2) NOT NULL,
    statement_closing_balance DECIMAL(15, 2) NOT NULL,
    book_balance DECIMAL(15, 2) NOT NULL,

    -- Reconciliation Items
    total_credits DECIMAL(15, 2) DEFAULT 0,
    total_debits DECIMAL(15, 2) DEFAULT 0,
    uncleared_deposits DECIMAL(15, 2) DEFAULT 0,
    uncleared_withdrawals DECIMAL(15, 2) DEFAULT 0,
    difference DECIMAL(15, 2) DEFAULT 0,

    -- Statistics
    total_transactions INTEGER DEFAULT 0,
    matched_transactions INTEGER DEFAULT 0,
    unmatched_transactions INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'IN_PROGRESS',
    is_balanced BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_bank_reconciliations_account ON bank_reconciliations(bank_account_id);
CREATE INDEX IF NOT EXISTS idx_bank_reconciliations_period ON bank_reconciliations(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_bank_reconciliations_status ON bank_reconciliations(status);

SELECT 'Part 7: Banking tables created successfully!' AS result;
