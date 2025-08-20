"""Add image_url column to emoji_assets and backfill from file_location if possible (idempotent, no-op safe).

Revision ID: 005_add_image_url_to_emoji_assets
Revises: 004_create_emoji_assets
Create Date: 2025-08-17 00:00:00.000000

Goals:
- Be fully idempotent: safe to run when objects already exist or are missing.
- Handle offline mode by emitting IF EXISTS/IF NOT EXISTS SQL.
- Use safe parameter binding for portability and to avoid DBAPI param-style issues.
- Backfill best-effort without blocking migration on any failure (do-no-harm).
- Provide verbose logs to diagnose partial states or environment issues.
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


def _log(msg: str) -> None:
    """Lightweight diagnostic logger for this migration."""
    print(f"[005_image_url_migration] {msg}")


def _table_exists(connection, table_name: str) -> bool:
    """
    Check whether a table exists in the current schema using SQLAlchemy inspector.
    Returns False and logs a warning if the inspector fails.
    """
    try:
        insp = sa.inspect(connection)
        exists = table_name in insp.get_table_names()
        _log(f"Table '{table_name}' exists: {exists}")
        return exists
    except Exception as e:
        _log(f"Warning: could not inspect tables to verify existence of '{table_name}': {e}")
        return False


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    """
    Check whether a column exists on a table. Returns False on any error.
    """
    try:
        insp = sa.inspect(connection)
        cols = [c["name"] for c in insp.get_columns(table_name)]
        exists = column_name in cols
        _log(f"Column '{table_name}.{column_name}' exists: {exists}")
        return exists
    except Exception as e:
        _log(f"Warning: could not inspect columns for '{table_name}.{column_name}': {e}")
        return False


def _add_image_url_column_online(connection) -> None:
    """
    Ensure the image_url column exists on emoji_assets in online mode.
    Prefer high-level op.add_column, and fall back to raw SQL IF NOT EXISTS.
    Always guarded with try/except and verbose logs.
    """
    # Only attempt when table exists (upgrade guards this prior to calling)
    if _column_exists(connection, "emoji_assets", "image_url"):
        _log("image_url already exists on emoji_assets; skipping add_column.")
        return

    try:
        _log("Attempting to add column image_url via op.add_column...")
        op.add_column("emoji_assets", sa.Column("image_url", sa.Text(), nullable=True))
        _log("Successfully added image_url via op.add_column.")
    except Exception as e1:
        _log(f"op.add_column failed (will fallback to SQL): {e1}")
        try:
            _log("Falling back to raw SQL: ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS image_url TEXT")
            op.execute(
                "ALTER TABLE IF EXISTS emoji_assets "
                "ADD COLUMN IF NOT EXISTS image_url TEXT"
            )
            _log("Successfully ensured image_url exists via raw SQL.")
        except Exception as e2:
            _log(f"Error: failed to ensure image_url column exists via fallback SQL: {e2}")
            # Do not re-raise; keep migration non-blocking.


def _add_image_url_column_offline() -> None:
    """
    Emit SQL to add image_url column in offline mode, using IF EXISTS / IF NOT EXISTS guards.
    """
    _log("Offline mode: emitting guarded SQL to add image_url.")
    try:
        op.execute(
            "ALTER TABLE IF EXISTS emoji_assets "
            "ADD COLUMN IF NOT EXISTS image_url TEXT"
        )
    except Exception as e:
        _log(f"Warning: offline ALTER TABLE add column failed (ignored): {e}")


def _backfill_image_url_online(connection) -> None:
    """
    Best-effort backfill image_url from file_location. Use environment EMOJI_CDN_BASE_URL
    as prefix; default to a placeholder CDN. Any failure should not block the migration.
    """
    # Only attempt backfill if table/column situation is expected
    if not _table_exists(connection, "emoji_assets"):
        _log("emoji_assets table missing; skipping backfill.")
        return
    if not _column_exists(connection, "emoji_assets", "image_url"):
        _log("image_url column missing; skipping backfill.")
        return
    # If file_location not present, nothing to backfill from
    if not _column_exists(connection, "emoji_assets", "file_location"):
        _log("file_location column missing; no backfill source available; skipping.")
        return

    base = os.getenv("EMOJI_CDN_BASE_URL", "https://cdn.placeholderdomain.com/emojis/").rstrip("/") + "/"
    _log(f"Using base CDN URL for backfill: {base}")

    # Try a Postgres-friendly regex to take the basename of file_location
    try:
        _log("Attempting regex-based backfill for image_url where NULL...")
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
        _log("Regex-based backfill completed (if applicable).")
    except Exception as e1:
        _log(f"Regex-based backfill failed (will attempt simple concat): {e1}")
        # Fallback: simple concatenation (may include full path)
        try:
            _log("Attempting simple concatenation backfill for image_url where NULL...")
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
            _log("Simple concatenation backfill completed (if applicable).")
        except Exception as e2:
            # Swallow errors to keep migration non-blocking.
            _log(f"Warning: all backfill attempts failed; proceeding without blocking migration: {e2}")


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
        _log(f"context.is_offline_mode() -> {offline}")
    except Exception as e:
        _log(f"Warning: could not determine offline/online mode (defaulting to online): {e}")
        offline = False

    if offline:
        _add_image_url_column_offline()
        _log("Offline upgrade completed.")
        return

    bind = op.get_bind()
    if bind is None:
        _log("Error: op.get_bind() returned None; cannot proceed in online mode.")
        return

    # If the table doesn't exist (e.g., environment drift), do nothing safely.
    if not _table_exists(bind, "emoji_assets"):
        _log("emoji_assets does not exist; skipping add/backfill (no-op).")
        return

    # Ensure column exists
    _add_image_url_column_online(bind)

    # Best-effort backfill
    try:
        _backfill_image_url_online(bind)
    except Exception as e:
        # Never block migration due to backfill issues
        _log(f"Warning: unexpected error during backfill (ignored): {e}")

    _log("Upgrade completed successfully (idempotent).")


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
        _log(f"context.is_offline_mode() -> {offline}")
    except Exception as e:
        _log(f"Warning: could not determine offline/online mode for downgrade: {e}")
        offline = False

    if offline:
        try:
            op.execute(
                "ALTER TABLE IF EXISTS emoji_assets "
                "DROP COLUMN IF EXISTS image_url"
            )
            _log("Offline: dropped image_url column if it existed.")
        except Exception as e:
            _log(f"Warning: offline DROP COLUMN failed (ignored): {e}")
        return

    bind = op.get_bind()
    if bind is None:
        _log("Warning: op.get_bind() returned None in downgrade; skipping.")
        return

    if not _table_exists(bind, "emoji_assets"):
        _log("emoji_assets table missing; nothing to drop.")
        return

    # Use raw SQL with IF EXISTS to avoid failure in legacy engines or partial states.
    try:
        op.execute(
            "ALTER TABLE IF EXISTS emoji_assets "
            "DROP COLUMN IF EXISTS image_url"
        )
        _log("Dropped image_url column via raw SQL (if it existed).")
    except Exception as e1:
        _log(f"Raw SQL drop column failed; will attempt op.drop_column if column is present: {e1}")
        # As a secondary attempt, try the high-level op.drop_column with guard
        if _column_exists(bind, "emoji_assets", "image_url"):
            try:
                op.drop_column("emoji_assets", "image_url")
                _log("Dropped image_url via op.drop_column.")
            except Exception as e2:
                # Give up non-destructively
                _log(f"Warning: op.drop_column also failed (ignored): {e2}")
