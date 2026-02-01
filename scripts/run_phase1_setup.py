#!/usr/bin/env python3
"""
Run Phase 1 setup on Supabase database
"""
import psycopg
from pathlib import Path

def run_setup():
    # Connect to Supabase
    conn = psycopg.connect(
        host='db.ywiurorfxrjvftcnenyk.supabase.co',
        port=6543,
        user='postgres',
        password='Aquapurite2026',
        dbname='postgres'
    )

    print("✅ Connected to Supabase")

    # Read SQL file
    sql_file = Path(__file__).parent / 'phase1_setup_supabase.sql'
    sql_content = sql_file.read_text()

    print("📄 Running phase1_setup_supabase.sql...")

    # Split SQL by statements and execute
    # Remove comments and empty lines
    statements = []
    current_statement = []

    for line in sql_content.split('\n'):
        stripped = line.strip()
        # Skip comments and separators
        if stripped.startswith('--') or stripped.startswith('===') or not stripped:
            continue
        current_statement.append(line)
        # Check if statement ends with semicolon
        if stripped.endswith(';'):
            statements.append('\n'.join(current_statement))
            current_statement = []

    cursor = conn.cursor()

    # Execute each statement
    for i, statement in enumerate(statements, 1):
        try:
            cursor.execute(statement)
            conn.commit()
            print(f"  ✓ Statement {i}/{len(statements)} executed")
        except Exception as e:
            conn.rollback()
            # Ignore "already exists" errors
            if 'already exists' in str(e).lower():
                print(f"  ⊘ Statement {i}/{len(statements)} - Table/constraint already exists (skipped)")
            else:
                print(f"  ✗ Statement {i}/{len(statements)} failed: {e}")

    print("\n✅ Phase 1 setup completed!")

    # Verify tables created
    print("\n📊 Verifying tables...")
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN (
            'tenants', 'modules', 'plans', 'tenant_subscriptions',
            'feature_flags', 'billing_history', 'usage_metrics'
        )
        ORDER BY table_name
    """)
    tables = cursor.fetchall()

    print(f"  Tables created: {len(tables)}/7")
    for table in tables:
        print(f"    ✓ {table[0]}")

    # Verify modules seeded
    print("\n📦 Verifying modules...")
    cursor.execute("""
        SELECT code, name, price_monthly
        FROM public.modules
        ORDER BY display_order
    """)
    modules = cursor.fetchall()

    print(f"  Modules seeded: {len(modules)}/10")
    for module in modules:
        print(f"    ✓ {module[0]}: {module[1]} (₹{module[2]}/mo)")

    # Verify plans seeded
    print("\n💰 Verifying plans...")
    cursor.execute("""
        SELECT slug, name, price_inr
        FROM public.plans
        ORDER BY display_order
    """)
    plans = cursor.fetchall()

    print(f"  Plans seeded: {len(plans)}/4")
    for plan in plans:
        print(f"    ✓ {plan[0]}: {plan[1]} (₹{plan[2]}/mo)")

    cursor.close()
    conn.close()
    print("\n✅ Setup verification complete!")

if __name__ == '__main__':
    run_setup()
