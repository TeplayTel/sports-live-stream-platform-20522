"""Ensure users table and constraints exist; prepare for JWT auth (robust idempotent)

Revision ID: 006_users_table_jwt_prep
Revises: 005_add_image_url_to_emoji_assets
Create Date: 2025-08-20 10:00:00.000000

This migration is designed to be safe to execute multiple times and in varied schema states.
It will:
- Ensure the userroleenum enum exists (no-op if already present).
- Create the users table if missing with a sane default schema (UUID PK).
- Add any missing columns on users without failing if they already exist.
- Ensure a PRIMARY KEY exists on user_id (best-effort; no failure if impossible).
- Ensure unique indexes on email and username only if no duplicates exist, otherwise skip and log.
- Downgrade only removes the created indexes if present; it will not drop users table or enum to avoid data loss.
"""
from alembic import op, context
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "006_users_table_jwt_prep"
down_revision = "005_add_image_url_to_emoji_assets"
branch_labels = None
depends_on = None


def _log(msg: str) -> None:
    """Diagnostic logger for this migration."""
    print(f"[006_users_table] {msg}")


def _current_schema(bind) -> str:
    """Return the current effective schema for the session (first in search_path)."""
    try:
        res = bind.execute(text("SELECT current_schema() AS s")).mappings().first()
        if res and res["s"]:
            return res["s"]
    except Exception as e:
        _log(f"Warning: could not determine current schema; defaulting to 'public': {e}")
    return "public"


def _table_exists(bind, schema: str, table: str) -> bool:
    """Check if a table exists in the specified schema."""
    try:
        res = bind.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.tables
                  WHERE table_schema = :schema
                    AND table_name = :table
                ) AS exists
                """
            ),
            {"schema": schema, "table": table},
        ).scalar()
        return bool(res)
    except Exception as e:
        _log(f"Warning: table existence check failed for {schema}.{table}: {e}")
        return False


def _column_exists(bind, schema: str, table: str, column: str) -> bool:
    """Check if a column exists in a table within the specified schema."""
    try:
        res = bind.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.columns
                  WHERE table_schema = :schema
                    AND table_name = :table
                    AND column_name = :column
                ) AS exists
                """
            ),
            {"schema": schema, "table": table, "column": column},
        ).scalar()
        return bool(res)
    except Exception as e:
        _log(f"Warning: column existence check failed for {schema}.{table}.{column}: {e}")
        return False


def _index_exists(bind, schema: str, index_name: str) -> bool:
    """Check if an index exists by name (schema-aware)."""
    try:
        res = bind.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM pg_class c
                  JOIN pg_namespace n ON n.oid = c.relnamespace
                  WHERE c.relkind = 'i'
                    AND c.relname = :iname
                    AND n.nspname = :schema
                ) AS exists
                """
            ),
            {"iname": index_name, "schema": schema},
        ).scalar()
        return bool(res)
    except Exception as e:
        _log(f"Warning: index existence check failed for {schema}.{index_name}: {e}")
        return False


def _has_primary_key(bind, schema: str, table: str) -> bool:
    """Determine whether a table has a primary key constraint."""
    try:
        res = bind.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.table_constraints
                  WHERE table_schema = :schema
                    AND table_name = :table
                    AND constraint_type = 'PRIMARY KEY'
                ) AS has_pk
                """
            ),
            {"schema": schema, "table": table},
        ).scalar()
        return bool(res)
    except Exception as e:
        _log(f"Warning: PK check failed for {schema}.{table}: {e}")
        return False


def _qualified_name(schema: str, table: str) -> str:
    """Return a properly quoted qualified table name, e.g. "public"."users"."""
    return f'"{schema}"."{table}"'


def _create_enum_if_missing(enum_name: str, values: list[str]) -> None:
    """Create a Postgres ENUM type if it does not exist."""
    vals = ", ".join([f"'{v}'" for v in values])
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                CREATE TYPE {enum_name} AS ENUM ({vals});
            END IF;
        END$$;
        """
    )


def _safe_add_column(bind, schema: str, table: str, column_sql: str) -> None:
    """Add a column with IF NOT EXISTS guard using raw SQL."""
    qname = _qualified_name(schema, table)
    try:
        op.execute(f"ALTER TABLE IF EXISTS {qname} ADD COLUMN IF NOT EXISTS {column_sql}")
    except Exception as e:
        _log(f"Warning: failed to add column on {qname} -> {column_sql}: {e}")


def _ensure_unique_index(bind, schema: str, table: str, column: str, index_name: str) -> None:
    """Ensure a UNIQUE index exists on table(column).

    - Skips creation if index already exists (by name).
    - Checks for duplicates; if duplicates exist, logs and skips to avoid migration failure.
    - Uses IF NOT EXISTS to avoid errors on re-run.
    """
    if _index_exists(bind, schema, index_name):
        return

    # Duplicate check (ignore NULLs to avoid false positives; both columns are NOT NULL in our schema)
    try:
        qname = _qualified_name(schema, table)
        dup_count = bind.execute(
            text(
                f"""
                SELECT COUNT(1) AS cnt
                FROM (
                    SELECT "{column}"
                    FROM {qname}
                    WHERE "{column}" IS NOT NULL
                    GROUP BY "{column}"
                    HAVING COUNT(*) > 1
                ) d
                """
            )
        ).scalar()
    except Exception as e:
        _log(f"Warning: duplicate check failed for index {index_name} on {schema}.{table}.{column}: {e}")
        dup_count = 0

    if dup_count and dup_count > 0:
        _log(
            f"Notice: Skipping UNIQUE index {index_name} on {schema}.{table}({column}) "
            f"due to {dup_count} duplicate value group(s)."
        )
        return

    try:
        op.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "{index_name}" ON "{table}" ("{column}")')
    except Exception as e:
        _log(f"Warning: failed to create UNIQUE index {index_name} on {table}({column}): {e}")


def _ensure_pk_on(bind, schema: str, table: str, column: str) -> None:
    """Best-effort ensure PRIMARY KEY exists on (column). Will not fail migration."""
    if not (_table_exists(bind, schema, table) and _column_exists(bind, schema, table, column)):
        return
    if _has_primary_key(bind, schema, table):
        return

    qname = _qualified_name(schema, table)
    # If possible, enforce NOT NULL first (skip errors)
    try:
        bind.execute(text(f'ALTER TABLE {qname} ALTER COLUMN "{column}" SET NOT NULL'))
    except Exception:
        pass

    try:
        bind.execute(text(f'ALTER TABLE {qname} ADD PRIMARY KEY ("{column}")'))
    except Exception as e:
        _log(f"Warning: could not add PRIMARY KEY on {qname}({column}): {e}")


def _ensure_users_table_and_columns(bind) -> None:
    """Ensure users table exists and has required columns, PK, and indexes."""
    schema = _current_schema(bind)
    table = "users"
    qname = _qualified_name(schema, table)

    # Ensure enum exists up-front
    _create_enum_if_missing("userroleenum", ["user", "admin", "moderator"])

    # Create table if missing (UUID PK, NOT NULLs where expected)
    if not _table_exists(bind, schema, table):
        _log("Creating table: users (if missing)")
        try:
            op.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {qname} (
                    user_id UUID PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    username VARCHAR(50) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    avatar_url TEXT,
                    role userroleenum NOT NULL DEFAULT 'user',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    preferences JSON,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
        except Exception as e:
            _log(f"Warning: CREATE TABLE users failed (continuing if table exists or will be fixed by adds): {e}")

    # Add any missing columns
    required_columns = {
        "user_id": ' "user_id" UUID ',
        "email": ' "email" VARCHAR(255) NOT NULL ',
        "username": ' "username" VARCHAR(50) NOT NULL ',
        "password_hash": ' "password_hash" VARCHAR(255) NOT NULL ',
        "full_name": ' "full_name" VARCHAR(255) ',
        "avatar_url": ' "avatar_url" TEXT ',
        "role": ' "role" userroleenum NOT NULL DEFAULT \'user\' ',
        "is_active": ' "is_active" BOOLEAN NOT NULL DEFAULT TRUE ',
        "preferences": ' "preferences" JSON ',
        "created_at": ' "created_at" TIMESTAMPTZ NOT NULL DEFAULT now() ',
        "updated_at": ' "updated_at" TIMESTAMPTZ NOT NULL DEFAULT now() ',
    }
    for col, ddl in required_columns.items():
        if not _column_exists(bind, schema, table, col):
            _safe_add_column(bind, schema, table, ddl)

    # Ensure PK exists on user_id (best-effort)
    _ensure_pk_on(bind, schema, table, "user_id")

    # Ensure unique indexes (skip creation if duplicates exist)
    _ensure_unique_index(bind, schema, table, "email", "ix_users_email")
    _ensure_unique_index(bind, schema, table, "username", "ix_users_username")


# PUBLIC_INTERFACE
def upgrade():
    """Alembic upgrade: ensure users table, enum, columns, PK, and unique indexes exist.

    Behavior:
    - Offline mode: emits idempotent SQL for enum creation and index creation (with IF NOT EXISTS).
      Column/table creation is emitted with IF NOT EXISTS where possible.
    - Online mode: schema-aware checks, guarded adds, duplicate-aware unique index creation.
    Safe to re-run without causing errors.
    """
    offline = False
    try:
        offline = context.is_offline_mode()
    except Exception:
        offline = False

    # Ensure enum exists (offline/online)
    _create_enum_if_missing("userroleenum", ["user", "admin", "moderator"])

    if offline:
        # Emit CREATE TABLE IF NOT EXISTS (idempotent) and indexes
        # Note: In offline mode we cannot introspect; emit guarded SQL that is safe on re-run.
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id UUID PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                username VARCHAR(50) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                avatar_url TEXT,
                role userroleenum NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                preferences JSON,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        # Add columns defensively in case table exists with partial schema
        op.execute('ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS user_id UUID')
        op.execute('ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS email VARCHAR(255)')
        op.execute('ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS username VARCHAR(50)')
        op.execute('ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)')
        op.execute('ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)')
        op.execute('ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS avatar_url TEXT')
        op.execute("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS role userroleenum")
        op.execute("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS is_active BOOLEAN")
        op.execute("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS preferences JSON")
        op.execute('ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ')
        op.execute('ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ')

        # Indexes (cannot detect duplicates offline; rely on IF NOT EXISTS)
        op.execute('CREATE UNIQUE INDEX IF NOT EXISTS "ix_users_email" ON "users" ("email")')
        op.execute('CREATE UNIQUE INDEX IF NOT EXISTS "ix_users_username" ON "users" ("username")')
        return

    # Online path: full schema-aware checks
    bind = op.get_bind()
    _ensure_users_table_and_columns(bind)


# PUBLIC_INTERFACE
def downgrade():
    """Alembic downgrade: remove unique indexes created by this migration (if any).

    Non-destructive:
    - Drops ix_users_username and ix_users_email if they exist.
    - Does not drop users table or enum types to avoid data loss.
    """
    # In both offline/online modes, guarded DROP INDEX is safe
    try:
        op.execute('DROP INDEX IF EXISTS "ix_users_username"')
    except Exception as e:
        _log(f"Warning: dropping index ix_users_username failed (ignored): {e}")
    try:
        op.execute('DROP INDEX IF EXISTS "ix_users_email"')
    except Exception as e:
        _log(f"Warning: dropping index ix_users_email failed (ignored): {e}")
    # Note: users table and enum userroleenum are intentionally preserved to avoid data loss.
