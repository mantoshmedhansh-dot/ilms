-- ============================================================
-- MIGRATION PART 1: ENUM TYPES
-- Run this FIRST before other migrations
-- ============================================================

-- HR Enums
DO $$ BEGIN
    CREATE TYPE employmenttype AS ENUM ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN', 'CONSULTANT');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE employeestatus AS ENUM ('ACTIVE', 'ON_NOTICE', 'ON_LEAVE', 'SUSPENDED', 'RESIGNED', 'TERMINATED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE leavetype AS ENUM ('CASUAL', 'SICK', 'EARNED', 'MATERNITY', 'PATERNITY', 'COMPENSATORY', 'UNPAID');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE leavestatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE attendancestatus AS ENUM ('PRESENT', 'ABSENT', 'HALF_DAY', 'ON_LEAVE', 'HOLIDAY', 'WEEKEND');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE payrollstatus AS ENUM ('DRAFT', 'PROCESSING', 'PROCESSED', 'APPROVED', 'PAID');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE gender AS ENUM ('MALE', 'FEMALE', 'OTHER');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE maritalstatus AS ENUM ('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Performance Enums
DO $$ BEGIN
    CREATE TYPE appraisalcyclestatus AS ENUM ('DRAFT', 'ACTIVE', 'CLOSED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE goalstatus AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE appraisalstatus AS ENUM ('NOT_STARTED', 'SELF_REVIEW', 'MANAGER_REVIEW', 'HR_REVIEW', 'COMPLETED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Fixed Assets Enums
DO $$ BEGIN
    CREATE TYPE depreciationmethod AS ENUM ('SLM', 'WDV');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE assetstatus AS ENUM ('ACTIVE', 'UNDER_MAINTENANCE', 'DISPOSED', 'WRITTEN_OFF', 'TRANSFERRED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE assettransferstatus AS ENUM ('PENDING', 'IN_TRANSIT', 'COMPLETED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE maintenancestatus AS ENUM ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Notification Enums
DO $$ BEGIN
    CREATE TYPE notificationtype AS ENUM (
        'SYSTEM', 'ALERT', 'ANNOUNCEMENT',
        'ORDER_CREATED', 'ORDER_CONFIRMED', 'ORDER_SHIPPED', 'ORDER_DELIVERED', 'ORDER_CANCELLED',
        'LOW_STOCK', 'OUT_OF_STOCK', 'STOCK_RECEIVED',
        'APPROVAL_PENDING', 'APPROVAL_APPROVED', 'APPROVAL_REJECTED',
        'LEAVE_REQUEST', 'LEAVE_APPROVED', 'LEAVE_REJECTED', 'PAYSLIP_GENERATED', 'APPRAISAL_DUE',
        'PAYMENT_RECEIVED', 'PAYMENT_DUE', 'INVOICE_GENERATED',
        'SERVICE_ASSIGNED', 'SERVICE_COMPLETED', 'WARRANTY_EXPIRING',
        'ASSET_MAINTENANCE_DUE', 'ASSET_TRANSFER_PENDING',
        'TASK_ASSIGNED', 'REMINDER', 'MENTION'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notificationpriority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notificationchannel AS ENUM ('IN_APP', 'EMAIL', 'SMS', 'PUSH', 'WEBHOOK');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

SELECT 'Part 1: Enum types created successfully!' AS result;
