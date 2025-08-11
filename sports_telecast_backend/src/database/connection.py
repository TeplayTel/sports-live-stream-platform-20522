# Loads environment variables from a .env file for application configuration
from dotenv import load_dotenv

# Load environment variables from .env automatically, supporting local development and deployment
load_dotenv()

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from contextlib import asynccontextmanager

# PUBLIC_INTERFACE
# Use only the provided environment variable for DB connection string.
# This backend strictly requires DATABASE_URL or POSTGRES_URL to be set in the environment.
# Only the full PostgreSQL connection string is used by this backend:
#
#   - DATABASE_URL (preferred key)
#   - POSTGRES_URL (alternative key; used if DATABASE_URL is absent)
#
# Other env vars (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, etc.) are NOT parsed and not required for backend startup.
# The .env file may contain these, but only the full connection string var is used.

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
print("===============DATABASE_URL at runtime:", DATABASE_URL)
print("[DEBUG] DATABASE_URL used by BE:", DATABASE_URL)
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL or POSTGRES_URL must be set as an environment variable for DB connection.\n"
        "No database username provided. By default, the system expects the role/user 'appuser'.\n"
        "If you see errors referring to 'role \"kavia\" does not exist', you have not set your env vars correctly, "
        "or are using the wrong username in your connection string.\n"
        "Update your .env to match the correct username and see .env.example for reference.\n"
        "Hardcoded database connection or localhost with the wrong user is not supported.\n"
        "Please contact support if you see this error in production."
    )

# If the DATABASE_URL is not already async, convert it (SQLAlchemy async format)
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    ASYNC_DATABASE_URL = DATABASE_URL
else:
    raise ValueError(
        "Unknown database connection string format. "
        "Expected postgresql:// or postgresql+asyncpg://"
    )

# For sync operations and Alembic migrations
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# For async operations
async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, class_=AsyncSession
)

# PUBLIC_INTERFACE
@asynccontextmanager
async def get_db():
    """
    Dependency that provides a SQLAlchemy async database session.
    Usage: async with get_db() as session:
    Or: db = await get_db().__anext__()
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

# PUBLIC_INTERFACE
async def init_database():
    """
    (Stub) Initialize database resources. For production, ensure all tables exist.
    """
    pass

# PUBLIC_INTERFACE
async def close_database_connections():
    """
    (Stub) Properly close async DB connections, if needed.
    """
    await async_engine.dispose()

# PUBLIC_INTERFACE
async def check_database_connection():
    """
    (Stub) Check if the DB connection is available.
    :return: True if connection OK, raises exception otherwise
    """
    async with async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True

# PUBLIC_INTERFACE
async def get_database_health():
    """
    (Stub) Return DB connection healthcheck info. Customize as required.
    """
    try:
        ok = await check_database_connection()
        return {"status": "ok" if ok else "error"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# =============================================================================
# File summary and future notes
# =============================================================================
# Purpose:
#   This file establishes and manages the database connection settings,
#   including engine creation and database session management for the
#   sports telecast backend. It is a foundational part of the API's interaction
#   with PostgreSQL, supporting CRUD operations for user, event, match, and
#   profile data.
#
# Usage notes:
#   - Import the get_db dependency in FastAPI routes for database access:
#       from src.database.connection import get_db
#   - Handles session management (open/close).
#   - Relies on environment variables in .env for PostgreSQL connectivity.
#   - Ensure appropriate models are imported before running migrations.
#
# Reminders & future improvements:
#   - Consider adding connection pooling configuration for high-traffic scenarios.
#   - Add automated reconnection logic for robustness in case of dropped connections.
#   - Evaluate async session management if application requires high concurrency.
#   - Document any custom session configurations here when modified.
#
# Last updated: 2024-06 (Kavia code generation agent)
