import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import text
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

# Database configuration using POSTGRES_* environment variables
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "sports_telecast")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

# Create async database URL
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info(f"Database URL configured: postgresql+asyncpg://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# PUBLIC_INTERFACE
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

# PUBLIC_INTERFACE
@asynccontextmanager
async def get_db_session():
    """
    Context manager for database sessions
    
    Usage:
        async with get_db_session() as session:
            # Use session here
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database transaction error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

# PUBLIC_INTERFACE
async def init_database():
    """
    Initialize database tables
    
    Creates all tables defined in the models if they don't exist.
    This should be called on application startup.
    """
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered with SQLAlchemy
            from .models import (  # noqa: F401 - Import needed for SQLAlchemy model registration
                UserDB, TeamDB, EventDB, MatchDB, MatchEventDB, 
                EmojiAssetDB, UserEmojiReactionDB, HighlightDB,
                UserProfileDB, ScheduleDB, ScheduleMatchDB
            )
            
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            
            # Log table creation confirmation
            logger.info("All database models registered and tables initialized:")
            logger.info("- users, user_profiles, teams, events, matches, match_events")
            logger.info("- emoji_assets, user_emoji_reactions, highlights")
            logger.info("- schedules, schedule_matches")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

# PUBLIC_INTERFACE
async def check_database_connection() -> bool:
    """
    Check if database connection is working
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection check successful")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

# PUBLIC_INTERFACE
async def close_database_connections():
    """
    Close all database connections
    
    Should be called on application shutdown.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

# Database health check function
# PUBLIC_INTERFACE
async def get_database_health() -> dict:
    """
    Get database health information
    
    Returns:
        dict: Database health status and connection info
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()  # Remove await here since fetchone() is not async
        
        return {
            "status": "healthy",
            "database": DB_NAME,
            "host": DB_HOST,
            "port": DB_PORT,
            "connection_pool_size": engine.pool.size(),
            "checked_out_connections": engine.pool.checkedout(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": DB_NAME,
            "host": DB_HOST,
            "port": DB_PORT,
        }

# Dependency for FastAPI
# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions
    
    Usage in FastAPI routes:
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_db)):
            # Use db session here
    """
    async for session in get_database_session():
        yield session
