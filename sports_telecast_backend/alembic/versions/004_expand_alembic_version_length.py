"""Expand alembic_version.version_num to VARCHAR(64)

This migration widens the alembic_version.version_num column to 64 characters
to prevent failures when revision IDs exceed 32 characters.

It is written to be cross-database friendly (PostgreSQL, SQLite) and idempotent.

Revision ID: 004_expand_alembic_version_length
Revises: 003
Create Date: 2025-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "004_expand_alembic_version_length"
down_revision = "003"
branch_labels = None
depends_on = None


# PUBLIC_INTERFACE
def get_migration_summary() -> str:
    """Return a human-readable summary of what this migration does."""
    return (
        "Widen alembic_version.version_num from VARCHAR(32) to VARCHAR(64) "
        "to support longer Alembic revision IDs."
    )


def _get_bind_dialect_name() -> str:
    """Return the name of the current DB dialect ('postgresql', 'sqlite', etc.)."""
    bind = op.get_bind()
    return bind.dialect.name if bind is not None else ""


def _current_version_num_length():
    """Inspect current alembic_version.version_num length, if determinable.
    Returns an integer length if known, else None.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    try:
        if dialect == "postgresql":
            # Postgres: query information_schema
            result = conn.execute(
                text(
                    """
                    SELECT character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = 'alembic_version'
                      AND column_name = 'version_num'
                    """
                )
            ).fetchone()
            if result and result[0] is not None:
                return int(result[0])
            return None
        elif dialect == "sqlite":
            # SQLite doesn't enforce varchar length, return None (skip check)
            return None
        else:
            # Fallback: unknown dialect, skip check
            return None
    except Exception:
        # In case the table doesn't exist yet or inspection fails, skip
        return None


# PUBLIC_INTERFACE
def upgrade() -> None:
    """Upgrade: alter alembic_version.version_num to VARCHAR(64), idempotently."""
    # If the column is already >= 64, do nothing for idempotence
    current_len = _current_version_num_length()
    if current_len is not None and current_len >= 64:
        return

    # Perform a simple alter; SQLAlchemy/Alembic will handle the correct DDL per dialect
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


# PUBLIC_INTERFACE
def downgrade() -> None:
    """Downgrade: revert alembic_version.version_num to VARCHAR(32)."""
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
