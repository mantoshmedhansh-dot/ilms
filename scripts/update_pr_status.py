"""Quick script to update PR status to APPROVED on production."""
import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Production database URL - replace with your Render PostgreSQL URL
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL environment variable")
    print("Example: export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'")
    exit(1)

# Ensure correct driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def update_pr_status():
    async with async_session() as session:
        # First show existing PRs
        result = await session.execute(
            text("SELECT id, requisition_number, status FROM purchase_requisitions")
        )
        rows = result.fetchall()
        print("Existing PRs:")
        for row in rows:
            print(f"  {row.requisition_number} - {row.status}")

        # Update to APPROVED
        await session.execute(
            text("UPDATE purchase_requisitions SET status = 'APPROVED', updated_at = NOW() WHERE status NOT IN ('CONVERTED', 'CANCELLED')")
        )
        await session.commit()
        print("\nUpdated all PRs to APPROVED status!")

        # Verify
        result = await session.execute(
            text("SELECT id, requisition_number, status FROM purchase_requisitions")
        )
        rows = result.fetchall()
        print("\nAfter update:")
        for row in rows:
            print(f"  {row.requisition_number} - {row.status}")

if __name__ == "__main__":
    asyncio.run(update_pr_status())
