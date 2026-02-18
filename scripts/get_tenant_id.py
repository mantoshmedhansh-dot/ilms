"""Get tenant ID for API testing."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.connect() as conn:
        r = await conn.execute(text(
            "SELECT id, subdomain, database_schema FROM public.tenants WHERE subdomain = 'finaltest2026'"
        ))
        row = r.fetchone()
        if row:
            print(f"Tenant ID: {row.id}")
            print(f"Subdomain: {row.subdomain}")
            print(f"Schema: {row.database_schema}")

asyncio.run(main())
