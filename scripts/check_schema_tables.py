"""Check what tables exist in public vs tenant schema."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.connect() as conn:
        # Check public schema tables
        r = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        public_tables = [row[0] for row in r.fetchall()]
        print(f"=== PUBLIC SCHEMA ({len(public_tables)} tables) ===")
        for t in public_tables:
            print(f"  {t}")

        # Check tenant schema tables
        r = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'tenant_finaltest2026' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tenant_tables = [row[0] for row in r.fetchall()]
        print(f"\n=== TENANT_FINALTEST2026 SCHEMA ({len(tenant_tables)} tables) ===")
        for t in tenant_tables:
            print(f"  {t}")

        # Test search_path works
        print("\n=== SEARCH PATH TEST ===")
        await conn.execute(text('SET search_path TO "tenant_finaltest2026"'))
        r = await conn.execute(text("SHOW search_path"))
        print(f"  search_path = {r.scalar()}")
        r = await conn.execute(text("SELECT COUNT(*) FROM orders"))
        print(f"  orders count = {r.scalar()}")

asyncio.run(main())
