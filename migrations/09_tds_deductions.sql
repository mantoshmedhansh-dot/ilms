-- Migration: TDS (Tax Deducted at Source) Tables
-- Description: Tables for TDS deduction tracking, Form 16A certificates

-- Create TDS section enum
DO $$ BEGIN
    CREATE TYPE tds_section AS ENUM (
        '194A', '194C', '194H', '194I', '194IA', '194J', '194Q', '195',
        '192', '194B', '194D', '194E', '194G', '194K', '194LA', '194LB', '194N', '194O'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create TDS deduction status enum
DO $$ BEGIN
    CREATE TYPE tds_deduction_status AS ENUM (
        'PENDING',
        'DEPOSITED',
        'CERTIFICATE_ISSUED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- TDS Deductions Table
CREATE TABLE IF NOT EXISTS tds_deductions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Deductee Information
    deductee_id UUID,
    deductee_type VARCHAR(50) NOT NULL,  -- VENDOR, CUSTOMER, EMPLOYEE
    deductee_name VARCHAR(255) NOT NULL,
    deductee_pan VARCHAR(10) NOT NULL,
    deductee_address TEXT,

    -- Deduction Details
    section tds_section NOT NULL,
    deduction_date DATE NOT NULL,
    financial_year VARCHAR(9) NOT NULL,  -- 2024-25
    quarter VARCHAR(2) NOT NULL,  -- Q1, Q2, Q3, Q4

    -- Amount Details
    gross_amount DECIMAL(15, 2) NOT NULL,
    tds_rate DECIMAL(5, 2) NOT NULL,
    tds_amount DECIMAL(15, 2) NOT NULL,
    surcharge DECIMAL(15, 2) DEFAULT 0,
    education_cess DECIMAL(15, 2) DEFAULT 0,
    total_tds DECIMAL(15, 2) NOT NULL,

    -- Lower/Nil Deduction Certificate
    lower_deduction_cert_no VARCHAR(50),
    lower_deduction_rate DECIMAL(5, 2),

    -- Reference
    reference_type VARCHAR(50),  -- INVOICE, PAYMENT, BILL
    reference_id UUID,
    reference_number VARCHAR(100),
    narration TEXT,

    -- Deposit Details
    status tds_deduction_status DEFAULT 'PENDING',
    deposit_date DATE,
    challan_number VARCHAR(50),
    challan_date DATE,
    bsr_code VARCHAR(20),  -- Bank BSR Code
    cin VARCHAR(50),  -- Challan Identification Number

    -- Certificate Details
    certificate_number VARCHAR(50),
    certificate_date DATE,
    certificate_issued BOOLEAN DEFAULT FALSE,

    -- Audit
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for TDS Deductions
CREATE INDEX IF NOT EXISTS ix_tds_deductions_company_fy ON tds_deductions(company_id, financial_year);
CREATE INDEX IF NOT EXISTS ix_tds_deductions_deductee_pan ON tds_deductions(deductee_pan);
CREATE INDEX IF NOT EXISTS ix_tds_deductions_status ON tds_deductions(status);
CREATE INDEX IF NOT EXISTS ix_tds_deductions_section ON tds_deductions(section);
CREATE INDEX IF NOT EXISTS ix_tds_deductions_quarter ON tds_deductions(financial_year, quarter);

-- TDS Rates Configuration Table
CREATE TABLE IF NOT EXISTS tds_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    section tds_section NOT NULL,
    description VARCHAR(255) NOT NULL,

    -- Rate Details
    standard_rate DECIMAL(5, 2) NOT NULL,
    higher_rate DECIMAL(5, 2),  -- If PAN not provided (typically 2x)
    threshold_amount DECIMAL(15, 2) DEFAULT 0,

    -- Applicability
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_tds_rates_company_section ON tds_rates(company_id, section);

-- Form 16A Certificates Table
CREATE TABLE IF NOT EXISTS form_16a_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Certificate Info
    certificate_number VARCHAR(50) NOT NULL,
    issue_date DATE NOT NULL,

    -- Period
    financial_year VARCHAR(9) NOT NULL,
    quarter VARCHAR(2) NOT NULL,

    -- Deductee
    deductee_name VARCHAR(255) NOT NULL,
    deductee_pan VARCHAR(10) NOT NULL,
    deductee_address TEXT,

    -- Deductor (Company)
    deductor_name VARCHAR(255) NOT NULL,
    deductor_tan VARCHAR(10) NOT NULL,
    deductor_pan VARCHAR(10),
    deductor_address TEXT,

    -- Summary
    total_amount_paid DECIMAL(15, 2) NOT NULL,
    total_tds_deducted DECIMAL(15, 2) NOT NULL,
    total_tds_deposited DECIMAL(15, 2) NOT NULL,

    -- Status
    is_revised BOOLEAN DEFAULT FALSE,
    original_certificate_id UUID,

    -- Storage
    pdf_path VARCHAR(500),

    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_form16a_company_fy_qtr ON form_16a_certificates(company_id, financial_year, quarter);
CREATE INDEX IF NOT EXISTS ix_form16a_deductee_pan ON form_16a_certificates(deductee_pan);

-- Insert default TDS rates (FY 2024-25)
INSERT INTO tds_rates (id, company_id, section, description, standard_rate, higher_rate, threshold_amount, effective_from, is_active)
SELECT
    gen_random_uuid(),
    c.id,
    '194A'::tds_section,
    'Interest other than interest on securities',
    10.00,
    20.00,
    40000,
    '2024-04-01',
    TRUE
FROM companies c
WHERE NOT EXISTS (
    SELECT 1 FROM tds_rates tr WHERE tr.company_id = c.id AND tr.section = '194A'
);

INSERT INTO tds_rates (id, company_id, section, description, standard_rate, higher_rate, threshold_amount, effective_from, is_active)
SELECT
    gen_random_uuid(),
    c.id,
    '194C'::tds_section,
    'Payment to contractors',
    2.00,
    20.00,
    30000,
    '2024-04-01',
    TRUE
FROM companies c
WHERE NOT EXISTS (
    SELECT 1 FROM tds_rates tr WHERE tr.company_id = c.id AND tr.section = '194C'
);

INSERT INTO tds_rates (id, company_id, section, description, standard_rate, higher_rate, threshold_amount, effective_from, is_active)
SELECT
    gen_random_uuid(),
    c.id,
    '194J'::tds_section,
    'Professional/Technical fees',
    10.00,
    20.00,
    30000,
    '2024-04-01',
    TRUE
FROM companies c
WHERE NOT EXISTS (
    SELECT 1 FROM tds_rates tr WHERE tr.company_id = c.id AND tr.section = '194J'
);

INSERT INTO tds_rates (id, company_id, section, description, standard_rate, higher_rate, threshold_amount, effective_from, is_active)
SELECT
    gen_random_uuid(),
    c.id,
    '194H'::tds_section,
    'Commission/Brokerage',
    5.00,
    20.00,
    15000,
    '2024-04-01',
    TRUE
FROM companies c
WHERE NOT EXISTS (
    SELECT 1 FROM tds_rates tr WHERE tr.company_id = c.id AND tr.section = '194H'
);

INSERT INTO tds_rates (id, company_id, section, description, standard_rate, higher_rate, threshold_amount, effective_from, is_active)
SELECT
    gen_random_uuid(),
    c.id,
    '194I'::tds_section,
    'Rent',
    10.00,
    20.00,
    240000,
    '2024-04-01',
    TRUE
FROM companies c
WHERE NOT EXISTS (
    SELECT 1 FROM tds_rates tr WHERE tr.company_id = c.id AND tr.section = '194I'
);

-- Comments
COMMENT ON TABLE tds_deductions IS 'TDS deductions made on payments to vendors/contractors';
COMMENT ON TABLE tds_rates IS 'TDS rate configuration by section';
COMMENT ON TABLE form_16a_certificates IS 'Form 16A TDS certificates issued to deductees';
COMMENT ON COLUMN tds_deductions.bsr_code IS 'Bank BSR Code from challan';
COMMENT ON COLUMN tds_deductions.cin IS 'Challan Identification Number';
