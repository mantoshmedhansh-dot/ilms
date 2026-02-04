"""Test Phase 6: Create all 237 operational tables in a test tenant schema"""
import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:Aquapurite2026@db.ywiurorfxrjvftcnenyk.supabase.co:6543/postgres'

from sqlalchemy import create_engine, text
from app.database import Base
from app import models  # Import all models

print(f"Total models registered: {len(Base.metadata.tables)}\n")

engine = create_engine(os.environ['DATABASE_URL'], echo=False)
test_schema = "tenant_phase6test"

try:
    with engine.begin() as conn:
        print(f"Dropping schema {test_schema}...")
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{test_schema}" CASCADE'))

        print(f"Creating schema {test_schema}...")
        conn.execute(text(f'CREATE SCHEMA "{test_schema}"'))

        print(f"Setting search path to {test_schema}...")
        conn.execute(text(f'SET search_path TO "{test_schema}"'))

        print(f"Creating all {len(Base.metadata.tables)} operational tables...")
        Base.metadata.create_all(conn)

        print("\n✅ SUCCESS: All tables created\n")

    # Count tables
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = '{test_schema}'
            AND table_type = 'BASE TABLE'
        """))
        count = result.scalar()
        print(f"Final Result: {count}/{len(Base.metadata.tables)} tables created")

        if count == len(Base.metadata.tables):
            print("✅ Phase 6 operational tables: COMPLETE")
        else:
            print(f"⚠️  Only {count} out of {len(Base.metadata.tables)} tables created")

except Exception as e:
    print(f"\n❌ FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    print(f"\nFinal Result: 0/{len(Base.metadata.tables)} tables")
finally:
    engine.dispose()
