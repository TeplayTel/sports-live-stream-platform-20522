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
    EmojiAssetDB, UserEmojiReactionDB, HighlightDB,
    UserProfileDB, ScheduleDB, ScheduleMatchDB
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
    DB_PORT = os.getenv("POSTGRES_PORT", "5001")
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
    """
    Run migrations using an async engine with a PostgreSQL advisory lock.

    Improvements:
    - Sets connection-level timeouts to avoid indefinite blocking on DDL locks.
    - Sets application_name for easier identification in pg_stat_activity.
    - Bounded retry loop for advisory lock acquisition with logging.
    """
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    # Advisory lock configuration
    lock_key = int(os.getenv("ALEMBIC_ADVISORY_LOCK_KEY", "653210987654321"))

    # Time to wait for advisory lock acquisition (seconds)
    lock_wait_seconds = float(os.getenv("ALEMBIC_LOCK_TIMEOUT", "30"))

    # Database-level timeouts (string values acceptable by Postgres, e.g. '15s', '2min')
    statement_timeout = os.getenv("ALEMBIC_STATEMENT_TIMEOUT", "5min")
    lock_timeout_db = os.getenv("ALEMBIC_PG_LOCK_TIMEOUT", "15s")
    idle_tx_timeout = os.getenv("ALEMBIC_IDLE_TX_TIMEOUT", "2min")
    application_name = os.getenv("ALEMBIC_APPLICATION_NAME", "sports_telecast_alembic")

    try:
        async with connectable.connect() as connection:
            # Apply connection-level settings to minimize hang risk
            # Note: Using literals here because some SET commands cannot be parameterized.
            await connection.execute(text(f"SET application_name TO '{application_name}'"))
            await connection.execute(text(f"SET lock_timeout TO '{lock_timeout_db}'"))
            await connection.execute(text(f"SET statement_timeout TO '{statement_timeout}'"))
            await connection.execute(text(f"SET idle_in_transaction_session_timeout TO '{idle_tx_timeout}'"))

            # Try to acquire advisory lock
            loop = asyncio.get_event_loop()
            start = loop.time()
            acquired = False
            attempt = 0
            while True:
                attempt += 1
                result = await connection.execute(
                    text("SELECT pg_try_advisory_lock(:k)"),
                    {"k": lock_key},
                )
                if bool(result.scalar()):
                    acquired = True
                    print(f"[alembic] Acquired advisory lock {lock_key} after {attempt} attempt(s).")
                    break

                if loop.time() - start > lock_wait_seconds:
                    print(
                        f"[alembic] Could not acquire advisory lock {lock_key} within "
                        f"{lock_wait_seconds}s; skipping migrations in this process"
                    )
                    return

                await asyncio.sleep(0.5)

            # Run migrations under the advisory lock
            print("[alembic] Running migrations (online)...")
            await connection.run_sync(do_run_migrations)
            print("[alembic] Migrations completed successfully.")

            # Release lock explicitly
            if acquired:
                await connection.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": lock_key})
                print(f"[alembic] Released advisory lock {lock_key}.")
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
