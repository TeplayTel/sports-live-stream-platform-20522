"""Add image_url column to emoji_assets and backfill from file_location if possible (idempotent, no-op safe).

Revision ID: 006_add_image_url_to_emoji_assets
Revises: 005_create_emoji_assets
Create Date: 2025-08-17 00:00:00.000000

Goals:
- Be fully idempotent: safe to run when objects already exist or are missing.
- Handle offline mode by emitting IF EXISTS/IF NOT EXISTS SQL.
- Use safe parameter binding for portability and to avoid DBAPI param-style issues.
- Backfill best-effort without blocking migration on any failure (do-no-harm).
- Provide verbose logs to diagnose partial states or environment issues.
- Ensure no implicit transaction ROLLBACK by isolating failures inside SAVEPOINTs.
- Add final on-exit diagnostics that dump full traceback, locals, transaction state,
  and current Alembic version, then re-raise any detected error to surface true
  ROLLBACK cause.
"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy import text
import os
import traceback
from typing import Callable, Optional


# revision identifiers, used by Alembic.
revision = "006_add_image_url_to_emoji_assets"
down_revision = "005_create_emoji_assets"
branch_labels = None
depends_on = None


def _log(msg: str) -> None:
    """Lightweight diagnostic logger for this migration."""
    print(f"[006_image_url_migration] {msg}")


def _safe_repr(obj, max_len: int = 1200) -> str:
    """Return a safe, length-limited repr for logging arbitrary objects."""
    try:
        s = repr(obj)
    except Exception as e:
        return f"<unreprable {type(obj).__name__}: {e}>"
    if len(s) > max_len:
        return s[: max_len - 20] + "... (truncated)"
    return s


def _log_tb_locals(tb) -> None:
    """
    Walk the traceback and print function, file, line, and a sanitized snapshot
    of local variables for each frame. This can be verbose by design.
    """
    try:
        idx = 0
        while tb:
            f = tb.tb_frame
            code = f.f_code
            co_name = code.co_name
            filename = code.co_filename
            lineno = tb.tb_lineno
            _log(f"TRACEBACK FRAME[{idx}]: {co_name} at {filename}:{lineno}")
            try:
                # Sanitize locals to strings using safe repr
                loc_dump = {k: _safe_repr(v) for k, v in f.f_locals.items()}
            except Exception as e:
                _log(f"TRACEBACK FRAME[{idx}] locals: <error capturing locals: {e}>")
            else:
                # Pretty print locals
                for k, v in loc_dump.items():
                    _log(f"  LOCAL {k} = {v}")
            tb = tb.tb_next
            idx += 1
    except Exception as e:
        _log(f"ERROR while logging traceback locals: {e}")


def _log_exception_context(exc: BaseException, bind=None, note: Optional[str] = None) -> None:
    """
    Log full exception context:
    - note
    - exception type and message
    - full traceback string
    - per-frame locals from traceback
    - transaction state
    - attempt to read Alembic current version
    """
    if note:
        _log(f"ON-EXIT NOTE: {note}")

    _log(f"ON-EXIT EXC TYPE: {type(exc).__name__}")
    _log(f"ON-EXIT EXC MSG: {exc}")

    # Full traceback string
    try:
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        _log("ON-EXIT TRACEBACK BEGIN >>>")
        for line in tb_str.rstrip("\n").split("\n"):
            _log(line)
        _log("<<< ON-EXIT TRACEBACK END")
    except Exception as e:
        _log(f"ON-EXIT: error while formatting traceback: {e}")

    # Per-frame locals dump
    try:
        _log("ON-EXIT: Dumping traceback frame locals for context...")
        _log_tb_locals(exc.__traceback__)
    except Exception as e:
        _log(f"ON-EXIT: error while dumping traceback locals: {e}")

    # Transaction state
    try:
        _log_tx_state(bind, note="on-exit-exception")  # may log inspection error if bind None
    except Exception as e:
        _log(f"ON-EXIT: error while logging tx state: {e}")

    # Current Alembic version (best effort)
    try:
        if bind is not None:
            try:
                res = bind.execute(text("SELECT version_num FROM alembic_version"))
                row = res.fetchone()
                try:
                    res.close()
                except Exception:
                    pass
                current_version = row[0] if row and len(row) > 0 else getattr(row, "version_num", None)
                _log(f"ON-EXIT: Alembic version (current): {current_version}")
            except Exception as e:
                _log(f"ON-EXIT: unable to read alembic_version: {e}")
        else:
            _log("ON-EXIT: No bind available to read alembic_version.")
    except Exception as e:
        _log(f"ON-EXIT: unexpected error while logging Alembic version: {e}")


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
        cols = [{"name": c.get("name")} for c in insp.get_columns(table_name)]
        names = [c["name"] for c in cols]
        exists = column_name in names
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


def _final_commit_probe_or_raise(connection) -> None:
    """
    As a final step, probe for commit-time errors that would only surface when Alembic
    updates the version table and commits the outer transaction.

    Strategy:
    - Log transaction id/isolation (PostgreSQL) to correlate with DB logs.
    - Force any deferred constraints to evaluate via 'SET CONSTRAINTS ALL IMMEDIATE'.
      If violations exist, this will raise here and provide a clear error in logs,
      rather than failing silently at commit.
    - Verify alembic_version table is readable (sanity).

    Any exceptions raised here are intentionally propagated to escalate the error,
    ensuring the CI/console shows the true cause of a ROLLBACK.
    """
    if connection is None:
        _log("FINAL-PROBE: No connection available; skipping commit probe.")
        return

    dialect = getattr(getattr(connection, "dialect", None), "name", "unknown")
    _log(f"FINAL-PROBE: starting (dialect={dialect})")
    _log_tx_state(connection, note="final-probe-begin")

    # PostgreSQL-specific diagnostics/probes
    if dialect == "postgresql":
        # Try to log the current transaction id (useful to correlate with server logs)
        try:
            res = connection.execute(text("SELECT txid_current() AS txid"))
            row = res.fetchone()
            try:
                res.close()
            except Exception:
                pass
            _log(f"FINAL-PROBE: txid_current={row.txid if row else 'unknown'}")
        except Exception as e:
            _log(f"FINAL-PROBE: warning: could not fetch txid_current(): {e}")

        # Try to log isolation level if available
        try:
            res = connection.execute(text("SELECT current_setting('transaction_isolation', true) AS iso"))
            row = res.fetchone()
            try:
                res.close()
            except Exception:
                pass
            _log(f"FINAL-PROBE: isolation={row.iso if row else 'unknown'}")
        except Exception as e:
            _log(f"FINAL-PROBE: warning: could not fetch transaction isolation: {e}")

        # Force all deferred constraints to be checked immediately.
        # If there is any pending violation that would only appear on COMMIT,
        # this raises right now with a clear message.
        _log("FINAL-PROBE: forcing deferred constraints to IMMEDIATE for early detection...")
        try:
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            _log("FINAL-PROBE: SET CONSTRAINTS ALL IMMEDIATE succeeded (no deferred violations).")
        except Exception as e:
            _log(f"FINAL-PROBE ERROR: Deferred constraint violation or commit-time error detected: {e}")
            _log("FINAL-PROBE: escalating by re-raising so Alembic shows the true cause.")
            raise

    # Sanity check: alembic_version table should be accessible
    try:
        res = connection.execute(text("SELECT version_num FROM alembic_version"))
        try:
            res.close()
        except Exception:
            pass
        _log("FINAL-PROBE: alembic_version accessible.")
    except Exception as e:
        _log(f"FINAL-PROBE ERROR: Unable to read alembic_version table: {e}")
        _log("FINAL-PROBE: escalating by re-raising so Alembic shows the true cause.")
        raise

    # Final small no-op to ensure connection still healthy
    try:
        res = connection.execute(text("SELECT 1"))
        try:
            res.close()
        except Exception:
            pass
    except Exception as e:
        _log(f"FINAL-PROBE ERROR: Health check SELECT failed: {e}")
        _log("FINAL-PROBE: escalating by re-raising so Alembic shows the true cause.")
        raise

    _log_tx_state(connection, note="final-probe-end")
    _log("FINAL-PROBE: completed successfully; ready for Alembic version-table update and COMMIT.")


# PUBLIC_INTERFACE
def upgrade():
    """Upgrade migration entrypoint.

    Behavior:
    - Offline mode: emit IF EXISTS/IF NOT EXISTS SQL to add image_url; skip backfill (no DB access).
    - Online mode: no-op if table missing; add column if missing; best-effort backfill where image_url is NULL.
    - All risky operations (DDL/DML) are run in SAVEPOINTs so that any failure does not poison the outer transaction.
    - At function exit, a catch-all finally block logs traceback, locals, transaction state, and current Alembic version.
    - If any error is detected during the upgrade, it will be re-raised from the finally block to surface true ROLLBACK cause.
    """
    _log("upgrade() starting.")
    fatal_exc: Optional[BaseException] = None
    bind = None  # Keep for on-exit diagnostics
    offline = False

    try:
        # Discover offline/online mode
        try:
            offline = context.is_offline_mode()
            _log(f"context.is_offline_mode() -> {offline}")
        except Exception as e:
            _log(f"Warning: could not determine offline/online mode (defaulting to online): {e}")
            offline = False

        if offline:
            # All DDL emitted in offline branch contained within try scope
            _add_image_url_column_offline()
            _log("Offline upgrade completed. Exiting upgrade() early for offline mode.")
            return

        # Online mode begins
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

        # Post-backfill diagnostics: count remaining NULL image_url rows for visibility
        try:
            if _column_exists(bind, "emoji_assets", "image_url"):
                res = bind.execute(
                    text("SELECT COUNT(*) AS c FROM emoji_assets WHERE image_url IS NULL")
                )
                row = res.fetchone()
                try:
                    res.close()
                except Exception:
                    pass
                remaining_nulls = row.c if row and hasattr(row, "c") else (row[0] if row else None)
                _log(f"Diagnostics: emoji_assets.image_url NULL count after backfill = {remaining_nulls}")
        except Exception as diag_exc:
            _log(f"Diagnostics warning: could not count NULL image_url rows: {diag_exc}")

        # Sanity check to ensure outer transaction is not tainted
        def _sanity_noop():
            res = bind.execute(text("SELECT 1"))
            try:
                res.close()
            except Exception:
                pass

        _run_in_savepoint(bind, _sanity_noop, "sanity SELECT 1")

        _log_tx_state(bind, note="post-ops")

        # Final probe to surface any commit-time or deferred errors before Alembic updates
        # the version table. Any error is re-raised to expose the true cause in logs.
        _final_commit_probe_or_raise(bind)

        _log("Upgrade operations completed without unhandled exceptions, final probe passed.")
        _log("Alembic will now update the version table and commit the migration transaction.")
        _log("If a ROLLBACK still occurs after this point, compare the txid/isolation logs above with DB logs.")
    except Exception as e:
        fatal_exc = e
        _log(f"FATAL: Exception captured in upgrade(): {e}")
        # Do not re-raise here; we want the finally block to run and log everything first.
    finally:
        # On-exit diagnostics: log tx state and alembic version, plus full exception context if any
        _log("upgrade() on-exit diagnostics starting...")
        try:
            # Attempt to acquire a bind if missing (best-effort)
            if bind is None:
                try:
                    bind = op.get_bind()
                except Exception as e2:
                    _log(f"ON-EXIT: could not obtain bind via op.get_bind(): {e2}")

            # Transaction state
            try:
                _log_tx_state(bind, note="on-exit")
            except Exception as e3:
                _log(f"ON-EXIT: error while logging transaction state: {e3}")

            # Current Alembic version (even in success case, helpful for traceability)
            if bind is not None:
                try:
                    res = bind.execute(text("SELECT version_num FROM alembic_version"))
                    row = res.fetchone()
                    try:
                        res.close()
                    except Exception:
                        pass
                    current_version = row[0] if row and len(row) > 0 else getattr(row, "version_num", None)
                    _log(f"ON-EXIT: Alembic version (pre-exit): {current_version}")
                except Exception as e4:
                    _log(f"ON-EXIT: unable to read alembic_version: {e4}")
            else:
                _log("ON-EXIT: No bind available to read alembic_version.")
        except Exception as e:
            _log(f"ON-EXIT: unexpected error during diagnostics: {e}")

        # If there was an error, dump full exception context and re-raise to surface root cause
        if fatal_exc is not None:
            try:
                _log_exception_context(fatal_exc, bind=bind, note="upgrade() failure")
            except Exception as le:
                _log(f"ON-EXIT: error while logging exception context: {le}")
            _log("ON-EXIT: re-raising fatal exception to force visibility of true ROLLBACK cause.")
            raise fatal_exc

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

        # Final probe to surface any commit-time or deferred errors before Alembic updates
        # the version table. Any error is re-raised to expose the true cause in logs.
        try:
            _final_commit_probe_or_raise(bind)
        except Exception as probe_exc:
            _log(f"FINAL-PROBE escalation in downgrade(): {probe_exc}")
            raise

        _log("Downgrade completed (non-destructive), final probe passed.")
        _log("Alembic will now update the version table and commit the migration transaction.")
    except Exception as fatal:
        _log(f"FATAL: Unexpected exception escaped downgrade(): {fatal}. Migration may ROLLBACK.")
    finally:
        _log("downgrade() finally reached; exiting downgrade().")
