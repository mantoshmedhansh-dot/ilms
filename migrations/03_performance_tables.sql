-- ============================================================
-- MIGRATION PART 3: PERFORMANCE MANAGEMENT TABLES
-- Run AFTER Part 2 (HR tables)
-- ============================================================

-- Appraisal Cycles table
CREATE TABLE IF NOT EXISTS appraisal_cycles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    financial_year VARCHAR(10) NOT NULL,

    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    review_start_date DATE,
    review_end_date DATE,

    status appraisalcyclestatus DEFAULT 'DRAFT',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appraisal_cycles_year ON appraisal_cycles(financial_year);
CREATE INDEX IF NOT EXISTS idx_appraisal_cycles_status ON appraisal_cycles(status);

-- KPIs table
CREATE TABLE IF NOT EXISTS kpis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,

    unit_of_measure VARCHAR(50) NOT NULL,
    target_value DECIMAL(12,2),
    weightage DECIMAL(5,2) DEFAULT 0,

    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    designation VARCHAR(100),

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kpis_category ON kpis(category);
CREATE INDEX IF NOT EXISTS idx_kpis_department ON kpis(department_id);

-- Goals table
CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    cycle_id UUID NOT NULL REFERENCES appraisal_cycles(id) ON DELETE CASCADE,

    title VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,

    kpi_id UUID REFERENCES kpis(id) ON DELETE SET NULL,

    target_value DECIMAL(12,2),
    achieved_value DECIMAL(12,2),
    unit_of_measure VARCHAR(50),
    weightage DECIMAL(5,2) DEFAULT 0,

    start_date DATE NOT NULL,
    due_date DATE NOT NULL,
    completed_date DATE,

    status goalstatus DEFAULT 'PENDING',
    completion_percentage INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goals_employee ON goals(employee_id);
CREATE INDEX IF NOT EXISTS idx_goals_cycle ON goals(cycle_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);

-- Appraisals table
CREATE TABLE IF NOT EXISTS appraisals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    cycle_id UUID NOT NULL REFERENCES appraisal_cycles(id) ON DELETE CASCADE,

    status appraisalstatus DEFAULT 'NOT_STARTED',

    -- Self Review
    self_rating DECIMAL(3,1),
    self_comments TEXT,
    self_review_date TIMESTAMP,

    -- Manager Review
    manager_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    manager_rating DECIMAL(3,1),
    manager_comments TEXT,
    manager_review_date TIMESTAMP,

    -- Final Rating
    final_rating DECIMAL(3,1),
    performance_band VARCHAR(20),

    -- Goals Achievement
    goals_achieved INTEGER DEFAULT 0,
    goals_total INTEGER DEFAULT 0,
    overall_goal_score DECIMAL(5,2),

    -- Development
    strengths TEXT,
    areas_of_improvement TEXT,
    development_plan TEXT,

    -- Recommendations
    recommended_for_promotion BOOLEAN DEFAULT FALSE,
    recommended_increment_percentage DECIMAL(5,2),

    -- HR Review
    hr_reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    hr_review_date TIMESTAMP,
    hr_comments TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(employee_id, cycle_id)
);

CREATE INDEX IF NOT EXISTS idx_appraisals_employee ON appraisals(employee_id);
CREATE INDEX IF NOT EXISTS idx_appraisals_cycle ON appraisals(cycle_id);
CREATE INDEX IF NOT EXISTS idx_appraisals_status ON appraisals(status);

-- Performance Feedback table
CREATE TABLE IF NOT EXISTS performance_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    given_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    feedback_type VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,

    is_private BOOLEAN DEFAULT FALSE,
    goal_id UUID REFERENCES goals(id) ON DELETE SET NULL,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_performance_feedback_employee ON performance_feedback(employee_id);

SELECT 'Part 3: Performance management tables created successfully!' AS result;
