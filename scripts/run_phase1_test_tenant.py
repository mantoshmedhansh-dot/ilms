#!/usr/bin/env python3
"""
Create test tenant and subscriptions on Supabase
"""
import psycopg
from pathlib import Path

def create_test_tenant():
    # Connect to Supabase
    conn = psycopg.connect(
        host='db.ywiurorfxrjvftcnenyk.supabase.co',
        port=6543,
        user='postgres',
        password='Aquapurite2026',
        dbname='postgres'
    )

    print("✅ Connected to Supabase")

    cursor = conn.cursor()

    # Create test tenant
    print("\n👤 Creating test tenant...")
    cursor.execute("""
        INSERT INTO public.tenants (
            name,
            subdomain,
            database_schema,
            status,
            plan_id
        )
        VALUES (
            'Test Company',
            'testcompany',
            'tenant_testcompany',
            'active',
            (SELECT id FROM public.plans WHERE slug = 'starter')
        )
        ON CONFLICT (subdomain) DO UPDATE
        SET
            name = EXCLUDED.name,
            updated_at = NOW()
        RETURNING id, name, subdomain, database_schema
    """)
    tenant = cursor.fetchone()
    conn.commit()

    tenant_id = tenant[0]
    print(f"  ✓ Tenant created: {tenant[1]}")
    print(f"    - Subdomain: {tenant[2]}")
    print(f"    - Schema: {tenant[3]}")
    print(f"    - ID: {tenant_id}")

    # Delete existing subscriptions
    print("\n🗑️  Cleaning up old subscriptions...")
    cursor.execute("""
        DELETE FROM public.tenant_subscriptions
        WHERE tenant_id = %s
    """, (tenant_id,))
    conn.commit()

    # Create subscriptions for Starter plan modules
    print("\n📦 Creating module subscriptions...")
    cursor.execute("""
        INSERT INTO public.tenant_subscriptions (
            tenant_id,
            module_id,
            status,
            starts_at
        )
        SELECT
            %s,
            m.id,
            'active',
            NOW()
        FROM public.modules m
        WHERE m.code IN ('system_admin', 'oms_fulfillment', 'd2c_storefront')
        RETURNING module_id
    """, (tenant_id,))
    subscriptions = cursor.fetchall()
    conn.commit()

    print(f"  ✓ Created {len(subscriptions)} subscriptions")

    # Verify tenant and subscriptions
    print("\n✅ Verifying test tenant setup...")
    cursor.execute("""
        SELECT
            t.name as tenant_name,
            m.code as module_code,
            m.name as module_name,
            ts.status
        FROM public.tenant_subscriptions ts
        JOIN public.tenants t ON ts.tenant_id = t.id
        JOIN public.modules m ON ts.module_id = m.id
        WHERE t.subdomain = 'testcompany'
        ORDER BY m.display_order
    """)
    active_subscriptions = cursor.fetchall()

    print(f"\n  Tenant: {active_subscriptions[0][0]}")
    print(f"  Active Subscriptions: {len(active_subscriptions)}/3")
    for sub in active_subscriptions:
        print(f"    ✓ {sub[1]}: {sub[2]} ({sub[3]})")

    # Test module access queries
    print("\n🧪 Testing module access queries...")

    # Test 1: Check OMS access (should be true)
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM public.tenant_subscriptions ts
            JOIN public.tenants t ON ts.tenant_id = t.id
            JOIN public.modules m ON ts.module_id = m.id
            WHERE t.subdomain = 'testcompany'
            AND m.code = 'oms_fulfillment'
            AND ts.status = 'active'
        ) as has_access
    """)
    has_oms = cursor.fetchone()[0]
    print(f"  ✓ OMS access: {has_oms} (expected: True)")

    # Test 2: Check Finance access (should be false)
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM public.tenant_subscriptions ts
            JOIN public.tenants t ON ts.tenant_id = t.id
            JOIN public.modules m ON ts.module_id = m.id
            WHERE t.subdomain = 'testcompany'
            AND m.code = 'finance'
            AND ts.status = 'active'
        ) as has_access
    """)
    has_finance = cursor.fetchone()[0]
    print(f"  ✓ Finance access: {has_finance} (expected: False)")

    print("\n" + "="*70)
    print("📋 COPY THIS TENANT ID FOR API TESTING:")
    print("="*70)
    print(f"\nTenant ID: {tenant_id}")
    print(f"\nUse in API calls:")
    print(f'curl -H "X-Tenant-ID: {tenant_id}" http://localhost:8000/api/...')
    print("\n" + "="*70)

    cursor.close()
    conn.close()
    print("\n✅ Test tenant setup complete!")

if __name__ == '__main__':
    create_test_tenant()
