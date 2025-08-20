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

# Global flag to indicate if we applied an in-memory revision truncation patch
_REV_TRUNC_PATCH_ACTIVE = False

def _ensure_alembic_version_length_sync(conn: Connection) -> None:
    """
    Ensure alembic_version.version_num column is at least VARCHAR(64).
    This must occur BEFORE Alembic writes/reads long revision IDs.

    Implementation detail:
    - Reads current type info using information_schema for Postgres.
    - If length is exactly 32 (legacy), issues an ALTER TABLE to VARCHAR(64).
    - If table/column doesn't exist (first migration), it's a no-op.
    - If already >= 64 or unlimited (text), it's a no-op.
    - Runs with IF EXISTS like behavior via try/except for portability.
    """
    try:
        # Check existence and current length (PostgreSQL specific query)
        result = conn.execute(
            text(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'alembic_version'
                  AND column_name = 'version_num'
                """
            )
        )
        row = result.first()
        if not row:
            # version table not yet present; nothing to do
            return

        current_len = row[0]  # None for TEXT (unlimited), or integer for varchar
        # None => TEXT or similar unlimited; treat as OK
        if current_len is None or current_len >= 64:
            return

        # Attempt to widen safely; if it's already widened by another process, ignore errors
        try:
            conn.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)"))
            print("[alembic] Ensured alembic_version.version_num is VARCHAR(64).")
        except Exception as ddl_ex:
            # Ignore concurrent upgrades or non-Postgres dialect differences
            print(f"[alembic] Non-fatal: could not ALTER alembic_version.version_num -> VARCHAR(64): {ddl_ex}")
    except Exception as ex:
        # Non-fatal; continue normal flow
        print(f"[alembic] WARN: version_num length detection failed (non-fatal): {ex}")

def _maybe_patch_revision_truncation(conn: Connection) -> None:
    """
    Detect if alembic_version.version_num is still narrow (<64); if so, apply a temporary
    in-memory patch so Alembic only uses the first N chars of revision ids when
    reading/writing during this process. This allows migrations to proceed safely.

    This does NOT alter the database schema; it only changes behavior in-memory.
    A clear warning is printed so operators know this is a temporary compatibility hack.
    """
    global _REV_TRUNC_PATCH_ACTIVE
    if _REV_TRUNC_PATCH_ACTIVE:
        return
    try:
        result = conn.execute(
            text(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'alembic_version'
                  AND column_name = 'version_num'
                """
            )
        )
        row = result.first()
        if not row:
            # version table not yet present; nothing to patch
            return

        current_len = row[0]
        # If unlimited or already >= 64, bypass the hack.
        if current_len is None or current_len >= 64:
            return

        max_len = int(current_len or 32)
        try:
            from alembic.script.revision import Revision
            from alembic.runtime.environment import EnvironmentContext
            from alembic.runtime.migration import MigrationContext as _MC
        except Exception as import_ex:
            print(f"[alembic] WARN: Could not import Alembic internals for truncation patch: {import_ex}")
            return

        if not hasattr(Revision, "_orig_revision_property"):
            _orig_getattr = Revision.__getattribute__

            def _patched_getattribute(self, name):  # noqa: ANN001
                if name in ("revision", "down_revision", "down_revisions"):
                    try:
                        val = _orig_getattr(self, name)
                        if val is None:
                            return val
                        if isinstance(val, str):
                            return val[:max_len]
                        if isinstance(val, (list, tuple)):
                            return type(val)(v[:max_len] if isinstance(v, str) else v for v in val)
                        return val
                    except Exception:
                        return _orig_getattr(self, name)
                return _orig_getattr(self, name)

            Revision._orig_revision_property = _orig_getattr  # type: ignore[attr-defined]
            Revision.__getattribute__ = _patched_getattribute  # type: ignore[assignment]

        try:
            orig_stamp = EnvironmentContext.stamp

            def _patched_stamp(self, *args, **kwargs):  # noqa: ANN001
                if args and isinstance(args[0], str):
                    args = (args[0][:max_len],) + args[1:]
                if "revision" in kwargs and isinstance(kwargs["revision"], str):
                    kwargs["revision"] = kwargs["revision"][:max_len]
                return orig_stamp(self, *args, **kwargs)

            EnvironmentContext.stamp = _patched_stamp  # type: ignore[assignment]
        except Exception as e:
            print(f"[alembic] WARN: Could not patch EnvironmentContext.stamp: {e}")

        try:
            orig_set_current = _MC._set_current_revision

            def _patched_set_current_revision(self, old, new):  # noqa: ANN001
                if isinstance(old, str):
                    old = old[:max_len]
                if isinstance(new, str):
                    new = new[:max_len]
                return orig_set_current(self, old, new)

            # Assign the patched function to the MigrationContext
            _MC._set_current_revision = _patched_set_current_revision  # type: ignore[assignment]
        except Exception as e:
            print("[alembic] WARN: Could not patch Alembic MigrationContext current revision update: {}".format(e))

        print(
            f"[alembic] WARNING: Detected alembic_version.version_num as VARCHAR({current_len}). "
            f"Applying temporary in-memory truncation of revision IDs to {max_len} chars so migrations can proceed. "
            "Please ensure the widening migration expands this column to 64."
        )
        _REV_TRUNC_PATCH_ACTIVE = True
    except Exception as ex:
        # Non-fatal; continue normal flow
        print(f"[alembic] WARN: version_num length detection failed (non-fatal): {ex}")

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
        # Offline mode: no database connection available; pre-hook not applicable.
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    """
    Run Alembic migrations within a context-managed transaction.
    Adds extra debugging around begin/commit to surface hidden exceptions.
    """
    # IMPORTANT: Ensure widening FIRST, then apply temporary patch if needed
    # BEFORE Alembic reads/writes any revision IDs.
    _ensure_alembic_version_length_sync(connection)
    _maybe_patch_revision_truncation(connection)

    context.configure(connection=connection, target_metadata=target_metadata)

    print("[alembic] BEGIN migration transaction")
    try:
        with context.begin_transaction():
            context.run_migrations()
        print("[alembic] END migration transaction (run_migrations completed)")
    except Exception as e:
        # Print full exception to ensure visibility in CI logs
        import traceback as _tb
        print("[alembic] EXCEPTION during run_migrations:")
        for line in "".join(_tb.format_exception(type(e), e, e.__traceback__)).splitlines():
            print("[alembic]   " + line)
        # Re-raise so Alembic handles rollback as usual
        raise


async def run_async_migrations() -> None:
    """
    Run migrations using an async engine with a PostgreSQL advisory lock.

    Improvements:
    - Sets connection-level timeouts to avoid indefinite blocking on DDL locks.
    - Sets application_name for easier identification in pg_stat_activity.
    - Bounded retry loop for advisory lock acquisition with logging.
    - Supports SQL echo logging when ALEMBIC_SQL_ECHO or LOG_SQL=true is set.
    - Adds robust try/except logging around run_migrations to surface hidden errors.
    """
    # Allow verbose SQL logging for diagnosis when requested
    sql_echo_env = os.getenv("ALEMBIC_SQL_ECHO") or os.getenv("LOG_SQL") or ""
    sql_echo = str(sql_echo_env).strip().lower() in {"1", "true", "yes", "on"}
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
        echo=sql_echo,
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
            try:
                # Ensure widening first; then patch if still narrow
                await connection.run_sync(_ensure_alembic_version_length_sync)
                await connection.run_sync(_maybe_patch_revision_truncation)
                await connection.run_sync(do_run_migrations)
            except Exception as e:
                # Ensure full stack trace is printed here
                import traceback as _tb
                print("[alembic] EXCEPTION bubbled from do_run_migrations:")
                for line in "".join(_tb.format_exception(type(e), e, e.__traceback__)).splitlines():
                    print("[alembic]   " + line)
                raise
            else:
                print("[alembic] Migrations completed successfully.")

            # Lightweight transaction integrity probe to catch doomed transaction state early
            try:
                # A harmless read to ensure connection still OK
                await connection.execute(text("SELECT 1"))
                # Force deferred constraints one more time right after migrations
                await connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
                print("[alembic] Post-run integrity probe passed (constraints immediate).")
            except Exception as probe_exc:
                print(f"[alembic] Post-run integrity probe FAILED: {probe_exc}")
                import traceback as _tb
                for line in "".join(_tb.format_exception(type(probe_exc), probe_exc, probe_exc.__traceback__)).splitlines():
                    print("[alembic]   " + line)
                # Re-raise to force visibility before Alembic attempts version-table update
                raise

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
