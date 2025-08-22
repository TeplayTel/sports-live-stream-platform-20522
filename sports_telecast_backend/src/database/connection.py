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
# Removed unused asynccontextmanager import to satisfy linter
import re
import logging

# Configure module-level logger
logger = logging.getLogger(__name__)

# PUBLIC_INTERFACE
# Use environment variables for DB connection string in the following order:
# 1. DATABASE_URL or POSTGRES_URL for PostgreSQL connections
# 2. SQLITE_URL for SQLite connections
# 3. Default SQLite path: sqlite+aiosqlite:///./app.db
#
# When using SQLite:
# - Tables are created automatically on startup
# - Alembic migrations are skipped
# - Both sync and async engines are configured with appropriate drivers

def get_database_url():
    """Determine the database URL based on environment variables."""
    # Check for PostgreSQL URL first
    pg_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if pg_url:
        return pg_url, "postgresql"

    # Check for explicit SQLite URL
    sqlite_url = os.environ.get("SQLITE_URL")
    if sqlite_url:
        return sqlite_url, "sqlite"

    # Default to local SQLite database
    return "sqlite+aiosqlite:///./app.db", "sqlite"

# Get database configuration
DATABASE_URL, DB_TYPE = get_database_url()

# Configure database URLs for sync and async operations
if DB_TYPE == "postgresql":
    if DATABASE_URL.startswith("postgresql://"):
        ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql+asyncpg://"):
        ASYNC_DATABASE_URL = DATABASE_URL
    else:
        raise ValueError(
            "Unknown PostgreSQL connection string format. "
            "Expected postgresql:// or postgresql+asyncpg://"
        )
    
    # For sync operations and Alembic migrations
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    
elif DB_TYPE == "sqlite":
    # Convert URL to proper format if needed
    if not DATABASE_URL.startswith(("sqlite://", "sqlite+aiosqlite://")):
        raise ValueError("SQLite URL must start with sqlite:// or sqlite+aiosqlite://")
    
    # Ensure async URL uses aiosqlite
    ASYNC_DATABASE_URL = re.sub(r'^sqlite:\/\/', 'sqlite+aiosqlite://', DATABASE_URL)
    
    # For sync operations, use regular sqlite
    SYNC_DATABASE_URL = re.sub(r'^sqlite\+aiosqlite:\/\/', 'sqlite://', ASYNC_DATABASE_URL)
    engine = create_engine(
        SYNC_DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# For async operations
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    future=True
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# PUBLIC_INTERFACE
async def get_db() -> AsyncSession:
    """
    PUBLIC_INTERFACE: FastAPI dependency that provides a SQLAlchemy AsyncSession.

    Usage in FastAPI endpoints:
      - Inject as a dependency: `db: AsyncSession = Depends(get_db)`
      - Do NOT call context-manager methods on `db`; it is already a live AsyncSession.

    Notes:
      - This function is an async context manager used by FastAPI's dependency system.
        FastAPI will enter/exit this context around the request and yield a real
        AsyncSession instance to the endpoint function.
      - Common pitfall: Do not pass `get_db()` itself or treat it as a generator.
        Always rely on FastAPI to inject the yielded AsyncSession.
    """
    db = AsyncSessionLocal()
    try:
        # Defensive check to catch incorrect session construction early.
        is_asyncsession = isinstance(db, AsyncSession)
        logger.debug(f"[get_db] Created session type={type(db)!r} isinstance(AsyncSession)={is_asyncsession}")
        if not is_asyncsession:
            # In case configuration changes break the session factory
            raise RuntimeError(f"get_db did not create an AsyncSession instance. Got: {type(db)}")
        yield db
    finally:
        try:
            await db.close()
        except Exception as e:
            logger.warning(f"[get_db] Error closing session {type(db)!r}: {e}")

# PUBLIC_INTERFACE
async def init_database():
    """
    Initialize database resources. For SQLite, creates all tables.
    For PostgreSQL, this is handled by Alembic migrations.
    """
    if DB_TYPE == "sqlite":
        # Create all tables for SQLite
        # Use sync engine for table creation as it's a one-time operation
        Base.metadata.create_all(engine)

# PUBLIC_INTERFACE
async def close_database_connections():
    """
    Properly close async DB connections.
    """
    await async_engine.dispose()

# PUBLIC_INTERFACE
async def check_database_connection():
    """
    Check if the DB connection is available.
    :return: True if connection OK, raises exception otherwise
    """
    async with async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True

# PUBLIC_INTERFACE
async def get_database_health():
    """
    Return DB connection healthcheck info.
    """
    try:
        ok = await check_database_connection()
        return {
            "status": "ok" if ok else "error",
            "type": DB_TYPE,
            "url": DATABASE_URL.split("@")[-1]  # Safe portion of URL for logging
        }
    except Exception as e:
        return {"status": "error", "detail": str(e), "type": DB_TYPE}

# =============================================================================
# File summary and future notes
# =============================================================================
# Purpose:
#   This file establishes and manages database connections for both PostgreSQL
#   and SQLite backends. It provides unified session management while handling
#   the specific requirements of each database type (migrations vs auto-creation,
#   sync/async drivers, etc.).
#
# Usage notes:
#   - Import the get_db dependency in FastAPI routes for database access:
#       from src.database.connection import get_db
#   - Handles session management (open/close).
#   - For PostgreSQL: Uses environment variables in .env
#   - For SQLite: Uses SQLITE_URL env var or defaults to ./app.db
#   - SQLite mode creates tables automatically; PostgreSQL uses Alembic
#
# Reminders & future improvements:
#   - Consider adding connection pooling configuration for PostgreSQL
#   - Add automated reconnection logic for robustness
#   - Document any custom session configurations here when modified
#   - Consider adding migration support for SQLite if needed
#
# Last updated: 2024-06 (Kavia code generation agent)
