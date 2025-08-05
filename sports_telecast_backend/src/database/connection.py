import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

# Database configuration - Use environment variables with PostgreSQL naming convention
POSTGRES_URL = os.getenv("POSTGRES_URL")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sports_telecast")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Create async database URL
if POSTGRES_URL:
    # Parse the POSTGRES_URL and rebuild with asyncpg driver
    if POSTGRES_URL.startswith("postgresql://"):
        # Extract components from URL for proper asyncpg format
        url_parts = POSTGRES_URL.replace("postgresql://", "").split("/")
        if len(url_parts) >= 2:
            connection_part = url_parts[0]  # host:port or user:pass@host:port
            db_name = url_parts[1]
            
            if "@" in connection_part:
                # Has user credentials
                creds, host_port = connection_part.split("@")
                if ":" in creds:
                    user, password = creds.split(":", 1)
                else:
                    user = creds
                    password = POSTGRES_PASSWORD
            else:
                # No credentials in URL, use env vars
                host_port = connection_part
                user = POSTGRES_USER
                password = POSTGRES_PASSWORD
            
            if ":" in host_port:
                host, port = host_port.split(":")
            else:
                host = host_port
                port = POSTGRES_PORT
            
            DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
        else:
            # Fallback to component-based URL
            DB_HOST = os.getenv("DB_HOST", "localhost")
            DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    else:
        # URL doesn't start with postgresql://, treat as components
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
else:
    # Build URL from components
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

logger.info(f"Database URL configured: postgresql+asyncpg://{POSTGRES_USER}:***@localhost:{POSTGRES_PORT}/{POSTGRES_DB}")

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
            # Import all models to ensure they're registered
            from .models import UserDB  # noqa: F401 - Import needed for SQLAlchemy model registration
            
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
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
            await conn.execute(func.select(func.literal(1)))
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
            result = await conn.execute(func.select(func.literal(1)))
            await result.fetchone()
        
        return {
            "status": "healthy",
            "database": POSTGRES_DB,
            "host": "localhost",
            "port": POSTGRES_PORT,
            "connection_pool_size": engine.pool.size(),
            "checked_out_connections": engine.pool.checkedout(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": POSTGRES_DB,
            "host": "localhost",
            "port": POSTGRES_PORT,
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
