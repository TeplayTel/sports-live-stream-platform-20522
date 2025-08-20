"""Add image_url column to emoji_assets and backfill from file_location if possible (idempotent, no-op safe).

Revision ID: 005_add_image_url_to_emoji_assets
Revises: 004_create_emoji_assets
Create Date: 2025-08-17 00:00:00.000000

Goals:
- Be fully idempotent: safe to run when objects already exist or are missing.
- Handle offline mode by emitting IF EXISTS/IF NOT EXISTS SQL.
- Use safe parameter binding for portability and to avoid DBAPI param-style issues.
- Backfill best-effort without blocking migration on any failure (do-no-harm).
"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy import text
import os

# revision identifiers, used by Alembic.
revision = "005_add_image_url_to_emoji_assets"
down_revision = "004_create_emoji_assets"
branch_labels = None
depends_on = None


def _table_exists(connection, table_name: str) -> bool:
    """
    Check whether a table exists in the current schema using SQLAlchemy inspector.
    """
    try:
        insp = sa.inspect(connection)
        return table_name in insp.get_table_names()
    except Exception:
        return False


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    """
    Check whether a column exists on a table. Returns False on any error.
    """
    try:
        insp = sa.inspect(connection)
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return column_name in cols
    except Exception:
        return False


def _add_image_url_column_online(connection) -> None:
    """
    Ensure the image_url column exists on emoji_assets in online mode.
    Prefer high-level op.add_column, and fall back to raw SQL IF NOT EXISTS.
    """
    if not _column_exists(connection, "emoji_assets", "image_url"):
        try:
            op.add_column("emoji_assets", sa.Column("image_url", sa.Text(), nullable=True))
        except Exception:
            # Fallback: use raw SQL to avoid DDL conflicts or type issues
            op.execute(
                "ALTER TABLE IF EXISTS emoji_assets "
                "ADD COLUMN IF NOT EXISTS image_url TEXT"
            )


def _add_image_url_column_offline() -> None:
    """
    Emit SQL to add image_url column in offline mode, using IF EXISTS / IF NOT EXISTS guards.
    """
    op.execute(
        "ALTER TABLE IF EXISTS emoji_assets "
        "ADD COLUMN IF NOT EXISTS image_url TEXT"
    )


def _backfill_image_url_online(connection) -> None:
    """
    Best-effort backfill image_url from file_location. Use environment EMOJI_CDN_BASE_URL
    as prefix; default to a placeholder CDN. Any failure should not block the migration.
    """
    # Only attempt backfill if table/column situation is expected
    if not _table_exists(connection, "emoji_assets"):
        return
    if not _column_exists(connection, "emoji_assets", "image_url"):
        return
    # If file_location not present, nothing to backfill from
    if not _column_exists(connection, "emoji_assets", "file_location"):
        return

    base = os.getenv("EMOJI_CDN_BASE_URL", "https://cdn.placeholderdomain.com/emojis/").rstrip("/") + "/"

    # Try a Postgres-friendly regex to take the basename of file_location
    try:
        connection.execute(
            text(
                """
                UPDATE emoji_assets
                SET image_url = CASE
                    WHEN file_location IS NOT NULL AND file_location <> ''
                         THEN :base || regexp_replace(file_location, '^.*/', '')
                    ELSE image_url
                END
                WHERE image_url IS NULL
                """
            ),
            {"base": base},
        )
    except Exception:
        # Fallback: simple concatenation (may include full path)
        try:
            connection.execute(
                text(
                    """
                    UPDATE emoji_assets
                    SET image_url = COALESCE(image_url, :base || file_location)
                    WHERE image_url IS NULL AND file_location IS NOT NULL
                    """
                ),
                {"base": base},
            )
        except Exception:
            # Swallow errors to keep migration non-blocking.
            pass


# PUBLIC_INTERFACE
def upgrade():
    """Upgrade migration entrypoint.

    Behavior:
    - Offline mode: emit IF EXISTS/IF NOT EXISTS SQL to add image_url; skip backfill (no DB access).
    - Online mode: no-op if table missing; add column if missing; best-effort backfill where image_url is NULL.
    Never raises on backfill failures; safe to re-run without harm.
    """
    offline = False
    try:
        offline = context.is_offline_mode()
    except Exception:
        offline = False

    if offline:
        _add_image_url_column_offline()
        return

    bind = op.get_bind()

    # If the table doesn't exist (e.g., environment drift), do nothing safely.
    if not _table_exists(bind, "emoji_assets"):
        return

    # Ensure column exists
    _add_image_url_column_online(bind)

    # Best-effort backfill
    try:
        _backfill_image_url_online(bind)
    except Exception:
        # Never block migration due to backfill issues
        pass


# PUBLIC_INTERFACE
def downgrade():
    """Downgrade migration entrypoint.

    Non-destructive philosophy:
    - Only removes the image_url column if it exists.
    - Uses IF EXISTS guards to avoid errors in both offline and online modes.
    """
    offline = False
    try:
        offline = context.is_offline_mode()
    except Exception:
        offline = False

    if offline:
        op.execute(
            "ALTER TABLE IF EXISTS emoji_assets "
            "DROP COLUMN IF EXISTS image_url"
        )
        return

    bind = op.get_bind()
    if not _table_exists(bind, "emoji_assets"):
        return

    # Use raw SQL with IF EXISTS to avoid failure in legacy engines or partial states.
    try:
        op.execute(
            "ALTER TABLE IF EXISTS emoji_assets "
            "DROP COLUMN IF EXISTS image_url"
        )
    except Exception:
        # As a secondary attempt, try the high-level op.drop_column with guard
        if _column_exists(bind, "emoji_assets", "image_url"):
            try:
                op.drop_column("emoji_assets", "image_url")
            except Exception:
                # Give up non-destructively
                pass
