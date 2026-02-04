import json
from decimal import Decimal
from datetime import datetime, date
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import DateTime, event
from sqlalchemy.dialects.postgresql import JSONB
import psycopg
from psycopg.types.json import set_json_dumps, set_json_loads

from app.config import settings


# Custom JSON encoder that handles Decimal, datetime, UUID, etc.
class CustomJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal, datetime, UUID and other types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


def custom_json_dumps(obj):
    """Custom JSON dumps function for psycopg."""
    return json.dumps(obj, cls=CustomJSONEncoder)


# Configure psycopg to use our custom JSON encoder globally
set_json_dumps(custom_json_dumps)


# SQLite doesn't support pool settings, check database type
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Convert database URL for proper driver
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql+asyncpg://"):
    # Switch to psycopg for async PostgreSQL
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://")

# Create async engine with appropriate settings
if is_sqlite:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,  # Check connection health before use
        pool_size=settings.DB_POOL_SIZE,  # Base pool size (default: 10)
        max_overflow=settings.DB_MAX_OVERFLOW,  # Extra connections beyond pool_size (default: 20)
        pool_timeout=settings.DB_POOL_TIMEOUT,  # Seconds to wait for connection (default: 30)
        pool_recycle=settings.DB_POOL_RECYCLE,  # Recycle connections after N seconds (default: 1800)
        connect_args={
            "prepare_threshold": None,  # Disable prepared statements for Supabase Pooler
            "connect_timeout": 30,  # Connection timeout in seconds
        },
    )

# Create async session factory (for default/public schema)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Alias for public schema session
async_session_maker = async_session_factory


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class TimestampMixin:
    """Mixin for adding created_at and updated_at columns."""
    pass  # Timestamps are defined in each model directly


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session():
    """Context manager for getting database session (for background jobs)."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database tables."""
    # Import all models to register them with Base.metadata
    from app import models  # noqa: F401

    print(f"Registered {len(Base.metadata.tables)} tables")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created")
    except Exception as e:
        # Ignore "already exists" errors
        if "already exists" in str(e).lower():
            print("Database tables already exist")
        else:
            print(f"Database warning: {e}")


# ====================
# MULTI-TENANT SUPPORT
# ====================

async def get_tenant_session(schema: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for a specific tenant schema

    Args:
        schema: Tenant database schema name (e.g., 'tenant_customer1')

    Yields:
        AsyncSession configured for tenant schema
    """
    # Create connection with tenant schema
    async with engine.connect() as conn:
        # Set search_path to tenant schema
        await conn.execute(f"SET search_path TO {schema}")

        # Create session from connection
        async_session = AsyncSession(bind=conn, expire_on_commit=False)

        try:
            yield async_session
            await async_session.commit()
        except Exception:
            await async_session.rollback()
            raise
        finally:
            await async_session.close()


async def get_db_with_tenant(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session for current tenant

    This function extracts the tenant schema from the request state
    and returns a session configured for that schema.

    Usage in FastAPI routes:
        @router.get("/api/products")
        async def get_products(db: AsyncSession = Depends(get_db_with_tenant)):
            ...

    Args:
        request: FastAPI request object (injected automatically)

    Yields:
        AsyncSession for tenant schema
    """
    # Get tenant schema from request state
    if not hasattr(request.state, "schema"):
        raise ValueError("Tenant schema not found in request. Is tenant middleware enabled?")

    schema = request.state.schema

    # Get session for tenant schema
    async for session in get_tenant_session(schema):
        yield session


async def get_public_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for public schema (tenant management)

    Use this for:
    - Tenant management operations
    - Module configuration
    - Subscription management
    - Billing

    Yields:
        AsyncSession for public schema
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
