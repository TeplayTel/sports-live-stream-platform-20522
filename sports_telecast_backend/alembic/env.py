import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import your models
from src.database.connection import Base
# Import all models to ensure they are registered with SQLAlchemy
from src.database.models import (  # noqa: F401 - Import needed for Alembic model discovery
    UserDB, TeamDB, EventDB, MatchDB, MatchEventDB, 
    EmojiAssetDB, UserEmojiReactionDB, HighlightDB
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    """Get database URL from environment variables.

    Preference order:
      1) DATABASE_URL or POSTGRES_URL (full URL). If provided as 'postgresql://',
         convert to 'postgresql+asyncpg://' for Alembic's async engine.
      2) POSTGRES_HOST/PORT/DB/USER/PASSWORD components (fallback).
    """
    full_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if full_url:
        if full_url.startswith("postgresql://"):
            return full_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if full_url.startswith("postgresql+asyncpg://"):
            return full_url
        # Allow psycopg2-style schemas too by normalizing
        if full_url.startswith("postgres://"):
            return full_url.replace("postgres://", "postgresql+asyncpg://", 1)
        raise ValueError(f"Unsupported DB URL scheme for Alembic: {full_url}")

    # Fallback to individual POSTGRES_* env vars
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "sports_telecast")
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

    return f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine with a PostgreSQL advisory lock.

    This prevents concurrent migration runs (e.g., when uvicorn reload spawns multiple processes)
    which can otherwise deadlock on DDL like CREATE TYPE/CREATE TABLE.
    """
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    # Advisory lock configuration
    # Use a stable bigint key; can be overridden via env var
    lock_key = int(os.getenv("ALEMBIC_ADVISORY_LOCK_KEY", "653210987654321"))
    # Max time in seconds to wait for lock before skipping on this process
    timeout_seconds = float(os.getenv("ALEMBIC_LOCK_TIMEOUT", "30"))

    try:
        async with connectable.connect() as connection:
            # Attempt to acquire advisory lock with timeout
            start = asyncio.get_event_loop().time()
            acquired = False
            while True:
                result = await connection.execute(
                    text("SELECT pg_try_advisory_lock(:k)"),
                    {"k": lock_key},
                )
                if bool(result.scalar()):
                    acquired = True
                    break

                if asyncio.get_event_loop().time() - start > timeout_seconds:
                    # Give up acquiring lock; assume another process is performing migrations
                    print(
                        f"[alembic] Could not acquire advisory lock {lock_key} within "
                        f"{timeout_seconds}s; skipping migrations in this process"
                    )
                    return

                await asyncio.sleep(0.5)

            # Run migrations under the advisory lock
            await connection.run_sync(do_run_migrations)

            # Release lock (also released on connection close, but explicit is better)
            if acquired:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:k)"),
                    {"k": lock_key},
                )
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
