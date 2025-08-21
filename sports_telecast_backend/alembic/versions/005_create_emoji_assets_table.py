"""create emoji_assets table for emoji uploads (idempotent)

Revision ID: 005_create_emoji_assets
Revises: 004_expand_alembic_version_length
Create Date: 2024-06-25 09:00:00.000000

This migration is designed to be robust and idempotent in any DB state:
- If the emoji_assets table does not exist, it creates it with the minimal expected schema.
- If the table already exists (e.g., created by an earlier or richer migration), it will add any missing columns.
- It will attempt to ensure a PRIMARY KEY exists on emoji_id, but will not fail the migration if data prevents it.
- The downgrade is non-destructive to avoid data loss in environments where the table pre-existed.

Notes:
- Migration 001 in this project may already create a richer emoji_assets table. This migration will NO-OP or only
  add missing pieces when the table already exists.
- Migration 004_expand_alembic_version_length runs before this revision and safely skips any operations if emoji_assets does not exist at that time.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "005_create_emoji_assets"
down_revision = "004_expand_alembic_version_length"
branch_labels = None
depends_on = None


def _current_schema(bind) -> str:
    """
    Return the current effective schema for the session (first in search_path).
    """
    try:
        res = bind.execute(text("SELECT current_schema() AS s")).mappings().first()
        if res and res["s"]:
            return res["s"]
    except Exception:
        # Default to public if we cannot determine
        return "public"
    return "public"


def _table_exists(connection, table_name: str) -> bool:
    """
    Check table existence using the SQLAlchemy inspector.
    """
    insp = sa.inspect(connection)
    return table_name in insp.get_table_names()


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    """
    Check whether a column exists on a table.
    """
    insp = sa.inspect(connection)
    try:
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return column_name in cols
    except Exception:
        return False


def _has_primary_key(bind, schema: str, table: str) -> bool:
    """
    Determine whether a table has a primary key constraint.
    """
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
    except Exception:
        return False


def _qualified_name(schema: str, table: str) -> str:
    """
    Return a properly quoted qualified table name, e.g. "public"."emoji_assets"
    """
    return f'"{schema}"."{table}"'


def _safe_add_primary_key_on_emoji_id(bind, schema: str, table: str) -> None:
    """
    Attempt to add a PRIMARY KEY on emoji_id if not present.

    Safety:
    - If emoji_id column does not exist, this function will do nothing (caller should ensure adding column first).
    - If any NULL values exist in emoji_id, we will skip making it NOT NULL and PK to avoid failure.
    - If duplicates exist or any other error occurs while adding the PK, we catch and continue (migration proceeds).
    """
    if not _column_exists(bind, table, "emoji_id"):
        # Cannot add a PK without the column
        return

    if _has_primary_key(bind, schema, table):
        return

    qname = _qualified_name(schema, table)

    # Check for NULLs in emoji_id; if present, skip enforcing NOT NULL and PK to avoid errors
    try:
        null_count = bind.execute(
            text(f"SELECT COUNT(1) FROM {qname} WHERE \"emoji_id\" IS NULL")
        ).scalar()
    except Exception:
        null_count = None

    # If possible, set NOT NULL prior to adding PK
    if null_count == 0:
        try:
            bind.execute(
                text(f'ALTER TABLE {qname} ALTER COLUMN "emoji_id" SET NOT NULL')
            )
        except Exception:
            # Ignore failure, continue to try adding PK which may still fail if NULLs/duplicates exist
            pass

    # Try to add the primary key constraint
    try:
        bind.execute(text(f'ALTER TABLE {qname} ADD PRIMARY KEY ("emoji_id")'))
    except Exception:
        # Do not block the migration; lack of PK does not prevent application from working
        pass


def upgrade():
    """
    Historical migration to introduce emoji_assets.

    Robust behaviors:
    - Creates emoji_assets if missing.
    - Adds missing columns if the table exists but is incomplete.
    - Attempts to ensure a PRIMARY KEY on emoji_id without failing the migration if impossible.
    """
    bind = op.get_bind()
    schema = _current_schema(bind)

    table_name = "emoji_assets"
    

    # If table does not exist, create it with minimal schema used by legacy upload endpoint.
    if not _table_exists(bind, table_name):
        op.create_table(
            table_name,
            sa.Column("emoji_id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("emoji_type", sa.String(length=32), nullable=False),
            sa.Column("file_location", sa.String(length=256), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        return  # Done

    # Table exists; ensure required columns exist
    if not _column_exists(bind, table_name, "emoji_id"):
        # Add emoji_id column as nullable first to avoid failing on existing rows; PK attempt will handle NOT NULL
        op.add_column(table_name, sa.Column("emoji_id", sa.String(length=36), nullable=True))

    if not _column_exists(bind, table_name, "emoji_type"):
        op.add_column(table_name, sa.Column("emoji_type", sa.String(length=32), nullable=False))

    if not _column_exists(bind, table_name, "file_location"):
        op.add_column(table_name, sa.Column("file_location", sa.String(length=256), nullable=False))

    if not _column_exists(bind, table_name, "created_at"):
        op.add_column(
            table_name,
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # Ensure a primary key exists on emoji_id if possible
    _safe_add_primary_key_on_emoji_id(bind, schema, table_name)


def downgrade():
    """
    Non-destructive downgrade: do not drop emoji_assets to avoid data loss in environments
    where the table pre-existed or has been populated. This is consistent with idempotent,
    additive migration philosophy.
    """
    # Intentionally no-op to preserve data and avoid dropping a table that may not have been created by this migration.
    pass
