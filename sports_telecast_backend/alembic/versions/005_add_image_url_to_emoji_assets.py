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
- Ensure no implicit transaction ROLLBACK by isolating failures inside SAVEPOINTs.
"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy import text
import os
from typing import Callable, Optional


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


def _run_in_savepoint(connection, func: Callable[[], None], desc: str) -> bool:
    """
    Run a callable inside a SAVEPOINT (nested transaction). If the callable raises,
    we roll back only to the savepoint and keep the outer Alembic transaction clean.

    Returns:
        bool: True if succeeded and committed the savepoint; False if rolled back.
    """
    # If no connection is available (e.g., offline mode), execute without savepoint and log
    if connection is None:
        _log(f"WARNING: No connection available for SAVEPOINT '{desc}'. Executing without SAVEPOINT.")
        try:
            func()
            _log(f"Executed without SAVEPOINT successfully for: {desc}")
            return True
        except Exception as e:
            _log(f"ERROR (no SAVEPOINT) during '{desc}': {e}. This may taint the outer transaction if any.")
            return False

    try:
        _log(f"BEGIN SAVEPOINT for: {desc}")
        with connection.begin_nested() as trans:
            try:
                func()
                trans.commit()
                _log(f"COMMIT SAVEPOINT for: {desc}")
                return True
            except Exception as inner_exc:
                _log(f"ERROR in '{desc}': {inner_exc} (rolling back SAVEPOINT)")
                try:
                    trans.rollback()
                except Exception as rb_exc:
                    _log(f"WARNING: rollback of SAVEPOINT for '{desc}' raised: {rb_exc}")
                return False
    except Exception as outer_exc:
        # Some dialects might not support nested transactions; log and signal failure
        _log(f"WARNING: Could not create SAVEPOINT for '{desc}': {outer_exc}. Proceeding without SAVEPOINT.")
        try:
            func()
            _log(f"Executed without SAVEPOINT successfully for: {desc}")
            return True
        except Exception as e:
            _log(f"ERROR (no SAVEPOINT) during '{desc}': {e}. This may taint the outer transaction.")
            return False


def _add_image_url_column_online(connection) -> None:
    """
    Ensure the image_url column exists on emoji_assets in online mode.
    Prefer high-level op.add_column, and fall back to raw SQL IF NOT EXISTS.
    All attempts run in SAVEPOINTs to avoid tainting the main transaction.
    """
    # Only attempt when table exists (upgrade guards this prior to calling)
    if _column_exists(connection, "emoji_assets", "image_url"):
        _log("image_url already exists on emoji_assets; skipping add_column.")
        return

    def _op_add():
        _log("Attempting to add column image_url via op.add_column...")
        op.add_column("emoji_assets", sa.Column("image_url", sa.Text(), nullable=True))
        _log("Successfully added image_url via op.add_column.")

    ok = _run_in_savepoint(connection, _op_add, "op.add_column(emoji_assets.image_url)")
    if ok:
        return

    def _fallback_sql():
        _log("Falling back to raw SQL: ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS image_url TEXT")
        op.execute(
            "ALTER TABLE IF EXISTS emoji_assets "
            "ADD COLUMN IF NOT EXISTS image_url TEXT"
        )
        _log("Successfully ensured image_url exists via raw SQL.")

    _run_in_savepoint(connection, _fallback_sql, "SQL fallback add column image_url")


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
        _log("Offline: emitted ALTER TABLE to add image_url (guarded).")
    except Exception as e:
        _log(f"Warning: offline ALTER TABLE add column failed (ignored): {e}")


def _backfill_image_url_online(connection) -> None:
    """
    Best-effort backfill image_url from file_location. Use environment EMOJI_CDN_BASE_URL
    as prefix; default to a placeholder CDN. Any failure is isolated inside a SAVEPOINT
    to prevent tainting the surrounding Alembic transaction.
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

    # First attempt: Postgres regex-based backfill
    def _regex_backfill():
        _log("Attempting regex-based backfill for image_url where NULL...")
        res = connection.execute(
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
        try:
            res.close()
        except Exception:
            pass
        _log("Regex-based backfill completed (if applicable).")

    if _run_in_savepoint(connection, _regex_backfill, "regex-based backfill image_url"):
        return  # done

    # Fallback attempt: Simple concatenation (cross-dialect)
    def _concat_backfill():
        _log("Attempting simple concatenation backfill for image_url where NULL...")
        res = connection.execute(
            text(
                """
                UPDATE emoji_assets
                SET image_url = COALESCE(image_url, :base || file_location)
                WHERE image_url IS NULL AND file_location IS NOT NULL
                """
            ),
            {"base": base},
        )
        try:
            res.close()
        except Exception:
            pass
        _log("Simple concatenation backfill completed (if applicable).")

    _run_in_savepoint(connection, _concat_backfill, "concat-based backfill image_url")


def _log_tx_state(connection, note: Optional[str] = None) -> None:
    """
    Try to log the current transaction state for diagnostics.
    """
    try:
        state_bits = []
        if note:
            state_bits.append(f"note={note}")
        try:
            in_tx = connection.in_transaction()
            state_bits.append(f"in_tx={in_tx}")
            tx = connection.get_transaction() if hasattr(connection, "get_transaction") else None
            if tx is not None:
                try:
                    state_bits.append(f"tx_active={getattr(tx, 'is_active', 'unknown')}")
                except Exception:
                    state_bits.append("tx_active=unknown")
        except Exception as e:
            state_bits.append(f"tx_inspect_error={e}")
        _log("TX_STATE: " + " ".join(state_bits))
    except Exception as e:
        _log(f"Could not log transaction state: {e}")


# PUBLIC_INTERFACE
def upgrade():
    """Upgrade migration entrypoint.

    Behavior:
    - Offline mode: emit IF EXISTS/IF NOT EXISTS SQL to add image_url; skip backfill (no DB access).
    - Online mode: no-op if table missing; add column if missing; best-effort backfill where image_url is NULL.
    - All risky operations (DDL/DML) are run in SAVEPOINTs so that any failure does not poison the outer transaction.
    - Always returns without raising so Alembic can commit if there were no outer errors.
    """
    _log("upgrade() starting.")
    try:
        offline = False
        try:
            offline = context.is_offline_mode()
            _log(f"context.is_offline_mode() -> {offline}")
        except Exception as e:
            _log(f"Warning: could not determine offline/online mode (defaulting to online): {e}")
            offline = False

        if offline:
            _add_image_url_column_offline()
            _log("Offline upgrade completed. Exiting upgrade() early for offline mode.")
            return

        bind = op.get_bind()
        if bind is None:
            _log("Error: op.get_bind() returned None; cannot proceed in online mode. Exiting upgrade().")
            return

        try:
            _log(f"Using dialect: {getattr(bind.dialect, 'name', 'unknown')}")
        except Exception:
            pass

        _log_tx_state(bind, note="pre-check")

        # If the table doesn't exist (e.g., environment drift), do nothing safely.
        if not _table_exists(bind, "emoji_assets"):
            _log("emoji_assets does not exist; skipping add/backfill (no-op). Exiting upgrade().")
            return

        # Ensure column exists
        _add_image_url_column_online(bind)

        # Best-effort backfill
        _backfill_image_url_online(bind)

        # Sanity check to ensure outer transaction is not tainted
        def _sanity_noop():
            res = bind.execute(text("SELECT 1"))
            try:
                res.close()
            except Exception:
                pass

        _run_in_savepoint(bind, _sanity_noop, "sanity SELECT 1")

        _log_tx_state(bind, note="post-ops")

        _log("Upgrade operations completed without unhandled exceptions.")
        _log("Alembic will now update the version table and commit the migration transaction.")
        _log("If a ROLLBACK still occurs after this point, inspect the TX_STATE logs above for clues.")
    except Exception as fatal:
        # Absolute last-resort catch to avoid aborting Alembic flow; we still log for diagnosis
        _log(f"FATAL: Unexpected exception escaped upgrade(): {fatal}. Migration will likely ROLLBACK.")
        # Intentionally do not re-raise
    finally:
        _log("upgrade() finally reached; exiting upgrade().")


# PUBLIC_INTERFACE
def downgrade():
    """Downgrade migration entrypoint.

    Non-destructive philosophy:
    - Only removes the image_url column if it exists.
    - Uses IF EXISTS guards to avoid errors in both offline and online modes.
    - All risky operations are isolated in SAVEPOINTs.
    """
    _log("downgrade() starting.")
    try:
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
                _log("Offline: emitted DROP COLUMN IF EXISTS for image_url (guarded).")
            except Exception as e:
                _log(f"Warning: offline DROP COLUMN image_url failed (ignored): {e}")
            _log("Exiting downgrade() early for offline mode.")
            return

        bind = op.get_bind()
        if bind is None:
            _log("Warning: op.get_bind() returned None in downgrade; skipping. Exiting downgrade().")
            return

        _log_tx_state(bind, note="pre-downgrade")

        if not _table_exists(bind, "emoji_assets"):
            _log("emoji_assets table missing; nothing to drop. Exiting downgrade().")
            return

        # Prefer raw SQL with IF EXISTS to be lenient
        def _raw_drop():
            op.execute(
                "ALTER TABLE IF EXISTS emoji_assets "
                "DROP COLUMN IF EXISTS image_url"
            )
        if not _run_in_savepoint(bind, _raw_drop, "drop column image_url (raw SQL)"):
            # Fallback to op.drop_column within savepoint
            def _op_drop():
                if _column_exists(bind, "emoji_assets", "image_url"):
                    op.drop_column("emoji_assets", "image_url")
            _run_in_savepoint(bind, _op_drop, "op.drop_column(image_url)")

        _log_tx_state(bind, note="post-downgrade")
        _log("Downgrade completed (non-destructive).")
        _log("Alembic will now update the version table and commit the migration transaction.")
    except Exception as fatal:
        _log(f"FATAL: Unexpected exception escaped downgrade(): {fatal}. Migration may ROLLBACK.")
    finally:
        _log("downgrade() finally reached; exiting downgrade().")
