"""Database-agnostic type definitions for SQLAlchemy models.

This module provides type definitions that work with both SQLite and PostgreSQL.
"""
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# Use JSON instead of JSONB for cross-database compatibility
# JSONB is PostgreSQL-specific, JSON works with both SQLite and PostgreSQL
JSONType = JSON

# UUID type that works with both databases
UUIDType = PG_UUID
