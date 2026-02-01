-- ============================================================
-- MIGRATION PART 2: HR TABLES
-- Run AFTER Part 1 (enum types)
-- ============================================================

-- Departments table
CREATE TABLE IF NOT EXISTS departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    head_id UUID REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_departments_code ON departments(code);
CREATE INDEX IF NOT EXISTS idx_departments_parent ON departments(parent_id);

-- Employees table
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_code VARCHAR(20) UNIQUE NOT NULL,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Personal Info
    date_of_birth DATE,
    gender gender,
    blood_group VARCHAR(5),
    marital_status maritalstatus,
    nationality VARCHAR(50) DEFAULT 'Indian',

    -- Personal Contact
    personal_email VARCHAR(255),
    personal_phone VARCHAR(20),

    -- Emergency Contact
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    emergency_contact_relation VARCHAR(50),

    -- Address
    current_address JSONB,
    permanent_address JSONB,

    -- Employment Details
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    designation VARCHAR(100),
    employment_type employmenttype DEFAULT 'FULL_TIME',
    status employeestatus DEFAULT 'ACTIVE',

    -- Employment Dates
    joining_date DATE NOT NULL,
    confirmation_date DATE,
    resignation_date DATE,
    last_working_date DATE,

    -- Reporting
    reporting_manager_id UUID REFERENCES employees(id) ON DELETE SET NULL,

    -- Indian Compliance Documents
    pan_number VARCHAR(10),
    aadhaar_number VARCHAR(12),
    uan_number VARCHAR(12),
    esic_number VARCHAR(17),

    -- Bank Details
    bank_name VARCHAR(100),
    bank_account_number VARCHAR(20),
    bank_ifsc_code VARCHAR(11),

    -- Other
    profile_photo_url VARCHAR(500),
    documents JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_employees_code ON employees(employee_code);
CREATE INDEX IF NOT EXISTS idx_employees_user ON employees(user_id);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department_id);
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);
CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees(reporting_manager_id);

-- Salary Structures table
CREATE TABLE IF NOT EXISTS salary_structures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID UNIQUE NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    effective_from DATE NOT NULL,

    -- CTC Breakdown (Monthly)
    basic_salary DECIMAL(12,2) NOT NULL,
    hra DECIMAL(12,2) DEFAULT 0,
    conveyance DECIMAL(12,2) DEFAULT 0,
    medical_allowance DECIMAL(12,2) DEFAULT 0,
    special_allowance DECIMAL(12,2) DEFAULT 0,
    other_allowances DECIMAL(12,2) DEFAULT 0,
    gross_salary DECIMAL(12,2) NOT NULL,

    -- Employer Contributions
    employer_pf DECIMAL(12,2) DEFAULT 0,
    employer_esic DECIMAL(12,2) DEFAULT 0,

    -- CTC
    annual_ctc DECIMAL(14,2) NOT NULL,
    monthly_ctc DECIMAL(12,2) NOT NULL,

    -- Statutory Applicability
    pf_applicable BOOLEAN DEFAULT TRUE,
    esic_applicable BOOLEAN DEFAULT FALSE,
    pt_applicable BOOLEAN DEFAULT TRUE,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_salary_structures_employee ON salary_structures(employee_id);

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    attendance_date DATE NOT NULL,

    check_in TIMESTAMP,
    check_out TIMESTAMP,
    work_hours DECIMAL(4,2),

    status attendancestatus NOT NULL,

    is_late BOOLEAN DEFAULT FALSE,
    late_minutes INTEGER DEFAULT 0,
    is_early_out BOOLEAN DEFAULT FALSE,
    early_out_minutes INTEGER DEFAULT 0,

    location_in JSONB,
    location_out JSONB,

    remarks TEXT,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(employee_id, attendance_date)
);

CREATE INDEX IF NOT EXISTS idx_attendance_employee ON attendance(employee_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date);
CREATE INDEX IF NOT EXISTS idx_attendance_status ON attendance(status);

-- Leave Balances table
CREATE TABLE IF NOT EXISTS leave_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type leavetype NOT NULL,
    financial_year VARCHAR(10) NOT NULL,

    opening_balance DECIMAL(4,1) DEFAULT 0,
    accrued DECIMAL(4,1) DEFAULT 0,
    taken DECIMAL(4,1) DEFAULT 0,
    adjusted DECIMAL(4,1) DEFAULT 0,
    closing_balance DECIMAL(4,1) DEFAULT 0,
    carry_forward_limit DECIMAL(4,1) DEFAULT 0,

    UNIQUE(employee_id, leave_type, financial_year)
);

CREATE INDEX IF NOT EXISTS idx_leave_balances_employee ON leave_balances(employee_id);

-- Leave Requests table
CREATE TABLE IF NOT EXISTS leave_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type leavetype NOT NULL,

    from_date DATE NOT NULL,
    to_date DATE NOT NULL,
    days DECIMAL(4,1) NOT NULL,
    is_half_day BOOLEAN DEFAULT FALSE,
    half_day_type VARCHAR(15),

    reason TEXT,
    status leavestatus DEFAULT 'PENDING',

    applied_on TIMESTAMP DEFAULT NOW(),
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_on TIMESTAMP,
    rejection_reason TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leave_requests_employee ON leave_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_requests_status ON leave_requests(status);

-- Payrolls table
CREATE TABLE IF NOT EXISTS payrolls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_month DATE NOT NULL,
    financial_year VARCHAR(10) NOT NULL,

    status payrollstatus DEFAULT 'DRAFT',

    total_employees INTEGER DEFAULT 0,
    total_gross DECIMAL(14,2) DEFAULT 0,
    total_deductions DECIMAL(14,2) DEFAULT 0,
    total_net DECIMAL(14,2) DEFAULT 0,

    processed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    processed_at TIMESTAMP,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payrolls_month ON payrolls(payroll_month);
CREATE INDEX IF NOT EXISTS idx_payrolls_status ON payrolls(status);

-- Payslips table
CREATE TABLE IF NOT EXISTS payslips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_id UUID NOT NULL REFERENCES payrolls(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    payslip_number VARCHAR(30) UNIQUE NOT NULL,

    -- Attendance Summary
    working_days INTEGER NOT NULL,
    days_present DECIMAL(4,1) NOT NULL,
    days_absent DECIMAL(4,1) DEFAULT 0,
    leaves_taken DECIMAL(4,1) DEFAULT 0,

    -- Earnings
    basic_earned DECIMAL(12,2) DEFAULT 0,
    hra_earned DECIMAL(12,2) DEFAULT 0,
    conveyance_earned DECIMAL(12,2) DEFAULT 0,
    medical_earned DECIMAL(12,2) DEFAULT 0,
    special_earned DECIMAL(12,2) DEFAULT 0,
    other_earned DECIMAL(12,2) DEFAULT 0,
    overtime_amount DECIMAL(12,2) DEFAULT 0,
    arrears DECIMAL(12,2) DEFAULT 0,
    bonus DECIMAL(12,2) DEFAULT 0,
    gross_earnings DECIMAL(12,2) NOT NULL,

    -- Deductions - Statutory
    employee_pf DECIMAL(12,2) DEFAULT 0,
    employer_pf DECIMAL(12,2) DEFAULT 0,
    employee_esic DECIMAL(12,2) DEFAULT 0,
    employer_esic DECIMAL(12,2) DEFAULT 0,
    professional_tax DECIMAL(12,2) DEFAULT 0,
    tds DECIMAL(12,2) DEFAULT 0,

    -- Deductions - Other
    loan_deduction DECIMAL(12,2) DEFAULT 0,
    advance_deduction DECIMAL(12,2) DEFAULT 0,
    other_deductions DECIMAL(12,2) DEFAULT 0,
    total_deductions DECIMAL(12,2) NOT NULL,

    -- Net Pay
    net_salary DECIMAL(12,2) NOT NULL,

    -- Payment
    payment_mode VARCHAR(20),
    payment_date DATE,
    payment_reference VARCHAR(50),
    payslip_pdf_url VARCHAR(500),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payslips_payroll ON payslips(payroll_id);
CREATE INDEX IF NOT EXISTS idx_payslips_employee ON payslips(employee_id);

SELECT 'Part 2: HR tables created successfully!' AS result;
