#!/usr/bin/env python3
"""
Complete SQL Generator for Supabase Migration
Reads SQLite database and generates PostgreSQL-compatible SQL
"""
import sqlite3
import json
import re
from datetime import datetime

DB_PATH = "/Users/mantosh/Desktop/Consumer durable 2/consumer_durable.db"
OUTPUT_PATH = "/Users/mantosh/Desktop/Consumer durable 2/FINAL_supabase_setup.sql"

def format_uuid(uuid_str):
    """Convert 32-char hex to UUID format with hyphens"""
    if uuid_str and len(str(uuid_str)) == 32:
        s = str(uuid_str)
        return f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return uuid_str

def escape_string(s):
    """Escape string for SQL"""
    if s is None:
        return "NULL"
    s = str(s).replace("'", "''")
    return f"'{s}'"

def format_value(val, col_name, bool_cols):
    """Format value for PostgreSQL"""
    if val is None:
        return "NULL"

    # Boolean columns
    if col_name in bool_cols:
        return "TRUE" if val else "FALSE"

    # Numbers
    if isinstance(val, (int, float)) and col_name not in bool_cols:
        return str(val)

    # UUID detection
    val_str = str(val)
    if len(val_str) == 32 and re.match(r'^[a-f0-9]+$', val_str.lower()):
        return f"'{format_uuid(val_str)}'"

    # JSON fields - handle specially
    if col_name in ['assigned_pincodes', 'existing_brands', 'extra_data']:
        if val_str == 'null' or val_str == '':
            return "NULL"
        return escape_string(val_str)

    return escape_string(val_str)

# Connect to SQLite
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Boolean columns by table
bool_cols_by_table = {
    'modules': ['is_active'],
    'permissions': ['is_active'],
    'roles': ['is_system', 'is_active'],
    'regions': ['is_active'],
    'users': ['is_active', 'is_verified'],
    'user_roles': [],
    'role_permissions': [],
    'categories': ['is_active', 'is_featured'],
    'brands': ['is_active', 'is_featured'],
    'products': ['is_active', 'is_featured', 'is_bestseller', 'is_new_arrival', 'extended_warranty_available'],
    'warehouses': ['is_active', 'is_default', 'can_fulfill_orders', 'can_receive_transfers'],
    'dealers': ['is_msme', 'security_deposit_paid', 'kyc_verified', 'can_place_orders',
                'receive_promotions', 'portal_access'],
}

# Generate output
output = []
output.append("-- =====================================================")
output.append("-- COMPLETE SUPABASE SETUP - ALL TABLES AND DATA")
output.append(f"-- Generated: {datetime.now().isoformat()}")
output.append("-- =====================================================")
output.append("")

# STEP 1: DROP TABLES
output.append("-- STEP 1: DROP ALL TABLES")
tables_to_drop = ['dealers', 'warehouses', 'products', 'brands', 'categories',
                  'role_permissions', 'user_roles', 'permissions', 'modules',
                  'users', 'roles', 'regions', 'audit_logs']
for t in tables_to_drop:
    output.append(f"DROP TABLE IF EXISTS {t} CASCADE;")
output.append("")

# STEP 2: ENUM TYPES
output.append("-- STEP 2: DROP AND CREATE ENUM TYPES")
output.append("DROP TYPE IF EXISTS rolelevel CASCADE;")
output.append("CREATE TYPE rolelevel AS ENUM ('SUPER_ADMIN', 'DIRECTOR', 'HEAD', 'MANAGER', 'EXECUTIVE');")
output.append("")
output.append("DROP TYPE IF EXISTS regiontype CASCADE;")
output.append("CREATE TYPE regiontype AS ENUM ('COUNTRY', 'ZONE', 'STATE', 'DISTRICT', 'CITY', 'AREA');")
output.append("")

# STEP 3: CREATE TABLES
output.append("-- STEP 3: CREATE ALL TABLES")
output.append("")

# MODULES
output.append("""-- MODULES
CREATE TABLE modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# PERMISSIONS
output.append("""-- PERMISSIONS
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    module_id UUID REFERENCES modules(id) ON DELETE SET NULL,
    action VARCHAR(50),
    resource VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# ROLES
output.append("""-- ROLES
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    level rolelevel NOT NULL DEFAULT 'EXECUTIVE',
    department VARCHAR(50),
    is_system BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# REGIONS
output.append("""-- REGIONS
CREATE TABLE regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    type regiontype NOT NULL DEFAULT 'STATE',
    parent_id UUID REFERENCES regions(id) ON DELETE SET NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# USERS
output.append("""-- USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    avatar_url VARCHAR(500),
    employee_code VARCHAR(50) UNIQUE,
    department VARCHAR(100),
    designation VARCHAR(100),
    region_id UUID REFERENCES regions(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP
);""")
output.append("")

# USER_ROLES
output.append("""-- USER_ROLES
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, role_id)
);""")
output.append("")

# ROLE_PERMISSIONS
output.append("""-- ROLE_PERMISSIONS
CREATE TABLE role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(role_id, permission_id)
);""")
output.append("")

# AUDIT_LOGS
output.append("""-- AUDIT_LOGS
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    old_values TEXT,
    new_values TEXT,
    description TEXT,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# CATEGORIES
output.append("""-- CATEGORIES
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    image_url VARCHAR(500),
    icon VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    meta_title VARCHAR(200),
    meta_description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# BRANDS
output.append("""-- BRANDS
CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    logo_url VARCHAR(500),
    banner_url VARCHAR(500),
    website VARCHAR(500),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# PRODUCTS
output.append("""-- PRODUCTS
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(300) NOT NULL,
    slug VARCHAR(300) UNIQUE NOT NULL,
    sku VARCHAR(100) UNIQUE NOT NULL,
    model_number VARCHAR(100),
    short_description TEXT,
    description TEXT,
    features TEXT,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    brand_id UUID REFERENCES brands(id) ON DELETE SET NULL,
    mrp DECIMAL(12,2),
    selling_price DECIMAL(12,2),
    dealer_price DECIMAL(12,2),
    cost_price DECIMAL(12,2),
    hsn_code VARCHAR(20),
    gst_rate DECIMAL(5,2),
    warranty_months INTEGER,
    extended_warranty_available BOOLEAN DEFAULT FALSE,
    warranty_terms TEXT,
    weight_kg DECIMAL(8,2),
    length_cm DECIMAL(8,2),
    width_cm DECIMAL(8,2),
    height_cm DECIMAL(8,2),
    min_stock_level INTEGER,
    max_stock_level INTEGER,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_bestseller BOOLEAN DEFAULT FALSE,
    is_new_arrival BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    meta_title VARCHAR(200),
    meta_description TEXT,
    meta_keywords VARCHAR(500),
    extra_data TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    published_at TIMESTAMP,
    model_code VARCHAR(50),
    item_type VARCHAR(20),
    dead_weight_kg DECIMAL(8,2),
    fg_code VARCHAR(50),
    part_code VARCHAR(50)
);""")
output.append("")

# WAREHOUSES
output.append("""-- WAREHOUSES
CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    warehouse_type VARCHAR(50),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    country VARCHAR(100) DEFAULT 'India',
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    contact_name VARCHAR(100),
    contact_phone VARCHAR(20),
    contact_email VARCHAR(255),
    region_id UUID REFERENCES regions(id) ON DELETE SET NULL,
    manager_id UUID REFERENCES users(id) ON DELETE SET NULL,
    total_capacity DECIMAL(12,2) DEFAULT 0,
    current_utilization DECIMAL(12,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    can_fulfill_orders BOOLEAN DEFAULT TRUE,
    can_receive_transfers BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# DEALERS - Full 81-column table
output.append("""-- DEALERS (FULL SCHEMA - 81 columns)
CREATE TABLE dealers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_code VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    legal_name VARCHAR(200) NOT NULL,
    display_name VARCHAR(200),
    dealer_type VARCHAR(13) NOT NULL,
    status VARCHAR(16) NOT NULL,
    tier VARCHAR(8) NOT NULL,
    parent_dealer_id UUID REFERENCES dealers(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    gstin VARCHAR(15) NOT NULL,
    pan VARCHAR(10) NOT NULL,
    tan VARCHAR(10),
    gst_registration_type VARCHAR(30) NOT NULL,
    is_msme BOOLEAN NOT NULL DEFAULT FALSE,
    msme_number VARCHAR(30),
    contact_person VARCHAR(200) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    alternate_phone VARCHAR(20),
    whatsapp VARCHAR(20),
    registered_address_line1 VARCHAR(255) NOT NULL,
    registered_address_line2 VARCHAR(255),
    registered_city VARCHAR(100) NOT NULL,
    registered_district VARCHAR(100) NOT NULL,
    registered_state VARCHAR(100) NOT NULL,
    registered_state_code VARCHAR(2) NOT NULL,
    registered_pincode VARCHAR(10) NOT NULL,
    shipping_address_line1 VARCHAR(255),
    shipping_address_line2 VARCHAR(255),
    shipping_city VARCHAR(100),
    shipping_state VARCHAR(100),
    shipping_pincode VARCHAR(10),
    region VARCHAR(50) NOT NULL,
    state VARCHAR(100) NOT NULL,
    territory VARCHAR(100),
    assigned_pincodes TEXT,
    business_type VARCHAR(50) NOT NULL,
    establishment_year INTEGER,
    annual_turnover DECIMAL(14,2),
    shop_area_sqft INTEGER,
    no_of_employees INTEGER,
    existing_brands TEXT,
    bank_name VARCHAR(200),
    bank_branch VARCHAR(200),
    bank_account_number VARCHAR(30),
    bank_ifsc VARCHAR(11),
    bank_account_name VARCHAR(200),
    credit_limit DECIMAL(14,2) NOT NULL DEFAULT 0,
    credit_days INTEGER NOT NULL DEFAULT 30,
    credit_status VARCHAR(7) NOT NULL DEFAULT 'ACTIVE',
    outstanding_amount DECIMAL(14,2) NOT NULL DEFAULT 0,
    overdue_amount DECIMAL(14,2) NOT NULL DEFAULT 0,
    security_deposit DECIMAL(14,2) NOT NULL DEFAULT 0,
    security_deposit_paid BOOLEAN NOT NULL DEFAULT FALSE,
    default_warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
    sales_rep_id UUID REFERENCES users(id) ON DELETE SET NULL,
    area_sales_manager_id UUID REFERENCES users(id) ON DELETE SET NULL,
    agreement_start_date DATE,
    agreement_end_date DATE,
    agreement_document_url VARCHAR(500),
    gst_certificate_url VARCHAR(500),
    pan_card_url VARCHAR(500),
    shop_photo_url VARCHAR(500),
    cancelled_cheque_url VARCHAR(500),
    kyc_verified BOOLEAN NOT NULL DEFAULT FALSE,
    kyc_verified_at TIMESTAMP,
    kyc_verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    total_orders INTEGER NOT NULL DEFAULT 0,
    total_revenue DECIMAL(14,2) NOT NULL DEFAULT 0,
    last_order_date TIMESTAMP,
    average_order_value DECIMAL(12,2),
    dealer_rating DECIMAL(3,2),
    payment_rating DECIMAL(3,2),
    can_place_orders BOOLEAN NOT NULL DEFAULT TRUE,
    receive_promotions BOOLEAN NOT NULL DEFAULT TRUE,
    portal_access BOOLEAN NOT NULL DEFAULT TRUE,
    internal_notes TEXT,
    onboarded_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);""")
output.append("")

# STEP 4: INDEXES
output.append("-- STEP 4: CREATE INDEXES")
output.append("CREATE INDEX idx_users_email ON users(email);")
output.append("CREATE INDEX idx_permissions_code ON permissions(code);")
output.append("CREATE INDEX idx_products_sku ON products(sku);")
output.append("CREATE INDEX idx_products_category ON products(category_id);")
output.append("CREATE INDEX idx_products_brand ON products(brand_id);")
output.append("CREATE INDEX idx_dealers_code ON dealers(dealer_code);")
output.append("CREATE INDEX idx_dealers_gstin ON dealers(gstin);")
output.append("")

# STEP 5: INSERT DATA
output.append("-- STEP 5: INSERT DATA")
output.append("")

# Tables to migrate (in order respecting foreign keys)
tables_to_migrate = [
    'modules', 'permissions', 'roles', 'regions', 'users',
    'user_roles', 'role_permissions', 'categories', 'brands',
    'products', 'warehouses', 'dealers'
]

for table in tables_to_migrate:
    bool_cols = bool_cols_by_table.get(table, [])

    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()

        if not rows:
            output.append(f"-- {table.upper()} (0 rows)")
            output.append("")
            continue

        cols = [desc[0] for desc in cursor.description]
        output.append(f"-- {table.upper()} ({len(rows)} rows)")

        for row in rows:
            values = []
            skip_row = False

            for i, col in enumerate(cols):
                val = row[i]

                # Skip invalid user_roles (where user_id is an integer instead of UUID)
                if table == 'user_roles' and col == 'user_id':
                    if val is not None and len(str(val)) < 32:
                        skip_row = True
                        break

                values.append(format_value(val, col, bool_cols))

            if not skip_row:
                output.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(values)});")

        output.append("")

    except Exception as e:
        output.append(f"-- Error migrating {table}: {e}")
        output.append("")

conn.close()

# Write output
with open(OUTPUT_PATH, "w") as f:
    f.write("\n".join(output))

print(f"Generated: {OUTPUT_PATH}")
print(f"Total lines: {len(output)}")
