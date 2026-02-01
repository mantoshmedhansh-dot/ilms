"""Initialize database tables."""
import asyncio
import sys
sys.path.insert(0, '/Users/mantosh/Consumer durable')

from app.database import engine, Base

# Import all models to register them with Base
from app.models import *


async def init():
    """Create all tables."""
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init())
