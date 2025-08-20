"""
Database maintenance utilities for Sports Telecast Backend.

This module provides utilities to:
- Inspect Postgres locks (including advisory locks)
- Clear/terminate sessions holding a specific advisory lock key
- Reset alembic_version safely and (re)apply migrations
- Diagnose and repair initial migration issues (001)

These functions are used by manage_db.py. They rely on env vars:
- DATABASE_URL or POSTGRES_URL
- ALEMBIC_ADVISORY_LOCK_KEY (optional, default 653210987654321)
- ALEMBIC_LOCK_TIMEOUT (optional; for runtime settings)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
import threading
import time
import uuid

from sqlalchemy import text
from sqlalchemy.engine import Engine
from alembic.config import Config
from alembic import command

from .connection import engine as sync_engine  # uses sync engine for admin ops


def _get_lock_key_pair(key: int) -> Tuple[int, int]:
    """
    Convert bigint advisory lock key to Postgres internal (classid, objid) int4 pair.

    Postgres represents a single BIGINT advisory key as two INT4 values (high, low).
    """
    # Ensure key within 64-bit signed range
    key = int(key) & 0xFFFFFFFFFFFFFFFF
    high = (key >> 32) & 0xFFFFFFFF
    low = key & 0xFFFFFFFF
    return high, low


# PUBLIC_INTERFACE
def inspect_locks(engine: Engine = sync_engine) -> Dict[str, Any]:
    """
    Inspect active Postgres locks and summarize advisory locks and blockers.

    Returns:
        Dict with counts and details for advisory locks and blocked sessions.
    """
    with engine.connect() as conn:
        advisory = conn.execute(
            text(
                """
                SELECT l.pid, l.locktype, l.mode, l.granted, l.classid, l.objid,
                       a.usename, a.application_name, a.state, a.query
                FROM pg_locks l
                JOIN pg_stat_activity a ON a.pid = l.pid
                WHERE l.locktype = 'advisory'
                ORDER BY l.granted DESC, l.pid
                """
            )
        ).mappings().all()

        blocked = conn.execute(
            text(
                """
                SELECT a.pid, a.usename, a.application_name, a.state, a.query, a.wait_event_type, a.wait_event
                FROM pg_stat_activity a
                WHERE a.wait_event_type IS NOT NULL
                ORDER BY a.pid
                """
            )
        ).mappings().all()

        return {
            "advisory_locks_count": len(advisory),
            "advisory_locks": [dict(row) for row in advisory],
            "blocked_sessions_count": len(blocked),
            "blocked_sessions": [dict(row) for row in blocked],
        }


# PUBLIC_INTERFACE
def clear_advisory_lock_holders(lock_key: Optional[str] = None, engine: Engine = sync_engine) -> Dict[str, Any]:
    """
    Terminate backend sessions that currently hold or wait on the specified advisory lock.

    Args:
        lock_key: Advisory lock key (bigint). If None, uses env ALEMBIC_ADVISORY_LOCK_KEY or default.
        engine: SQLAlchemy sync engine.

    Returns:
        Dict summary of terminated PIDs and any errors.
    """
    key = int(lock_key) if lock_key else int(os.getenv("ALEMBIC_ADVISORY_LOCK_KEY", "653210987654321"))
    high, low = _get_lock_key_pair(key)

    terminated: List[int] = []
    errors: List[str] = []

    with engine.begin() as conn:
        holders = conn.execute(
            text(
                """
                SELECT DISTINCT l.pid
                FROM pg_locks l
                WHERE l.locktype = 'advisory'
                  AND l.classid = :high AND l.objid = :low
                """
            ),
            {"high": high, "low": low},
        ).fetchall()

        for (pid,) in holders:
            try:
                conn.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
                terminated.append(pid)
            except Exception as e:
                errors.append(f"Failed to terminate pid {pid}: {e}")

    return {
        "lock_key": key,
        "terminated_pids": terminated,
        "errors": errors,
    }


def _alembic_config() -> Config:
    """
    Build Alembic Config programmatically pointing to this project's alembic directory.
    """
    project_root = Path(__file__).resolve().parents[2]
    alembic_ini = project_root / "alembic.ini"
    alembic_dir = project_root / "alembic"

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(alembic_dir))
    # Also set SQLAlchemy URL for tools that read from config; env.py still reads env vars.
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if url:
        cfg.set_main_option("sqlalchemy.url", url)
    return cfg


# PUBLIC_INTERFACE
def alembic_reset() -> None:
    """
    Reset Alembic version table by truncating alembic_version if it exists.
    """
    with sync_engine.begin() as conn:
        conn.execute(text("DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version') THEN EXECUTE 'TRUNCATE TABLE alembic_version'; END IF; END $$;"))


# PUBLIC_INTERFACE
def alembic_stamp_base() -> None:
    """
    Stamp the database at 'base' revision without running migrations.
    Useful when you want to re-run from the first migration explicitly.
    """
    cfg = _alembic_config()
    command.stamp(cfg, "base")


# PUBLIC_INTERFACE
def alembic_upgrade(revision: str = "head") -> None:
    """
    Run Alembic upgrade to the specified revision (default 'head').
    """
    cfg = _alembic_config()
    command.upgrade(cfg, revision)


def _table_exists(conn, table_name: str) -> bool:
    """
    Helper: check if a table exists in the current database schema.
    """
    res = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :t
            )
            """
        ),
        {"t": table_name},
    ).scalar()
    return bool(res)


def _fetch_alembic_versions(conn) -> List[str]:
    """
    Helper: fetch all revision ids from alembic_version (typically 0 or 1 row).
    """
    exists = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='alembic_version'
            )
            """
        )
    ).scalar()
    if not exists:
        return []
    rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    return [r[0] for r in rows]


def _initial_expected_tables() -> Set[str]:
    """
    List of tables expected from the 001 initial migration.
    """
    return {
        "users",
        "teams",
        "events",
        "emoji_assets",
        "matches",
        "user_emoji_reactions",
        "highlights",
        "match_events",
    }


def _inspect_initial_schema(conn) -> Dict[str, Any]:
    """
    Check presence of tables expected from initial migration.
    """
    expected = _initial_expected_tables()
    present: Set[str] = set()
    missing: Set[str] = set()
    for t in expected:
        if _table_exists(conn, t):
            present.add(t)
        else:
            missing.add(t)
    return {
        "expected_tables": sorted(list(expected)),
        "present_tables": sorted(list(present)),
        "missing_tables": sorted(list(missing)),
        "all_absent": len(present) == 0,
        "all_present": len(missing) == 0,
        "partial": (len(present) > 0 and len(missing) > 0),
    }


# PUBLIC_INTERFACE
# PUBLIC_INTERFACE
def run_diagnose_001_migration(timeout_seconds: int = 180, engine: Engine = sync_engine) -> Dict[str, Any]:
    """
    Run 'alembic upgrade 001' while continuously monitoring pg_stat_activity and pg_locks.
    This identifies which DDL statement starts and which one does not return, and whether
    it is blocked by another session/transaction or previous schema state.

    Returns:
        Dict summary including:
            - application_name: Name used for Alembic connection so monitoring can filter
            - started: bool
            - completed: bool
            - duration_seconds: float
            - last_seen_query: str (trimmed)
            - lock_samples: list of brief snapshots collected periodically
            - error: str if any exception occurred
            - note: additional info
    """
    app_name = f"sports_telecast_alembic_diag_{uuid.uuid4().hex[:8]}"
    # Set env vars to improve observability and avoid infinite waits
    os.environ["ALEMBIC_APPLICATION_NAME"] = app_name
    os.environ.setdefault("ALEMBIC_PG_LOCK_TIMEOUT", "15s")
    os.environ.setdefault("ALEMBIC_STATEMENT_TIMEOUT", "5min")
    os.environ.setdefault("ALEMBIC_IDLE_TX_TIMEOUT", "2min")
    os.environ.setdefault("ALEMBIC_SQL_ECHO", "true")

    cfg = _alembic_config()

    stop_evt = threading.Event()
    samples: List[Dict[str, Any]] = []

    def _monitor():
        with engine.connect() as conn:
            while not stop_evt.is_set():
                try:
                    # Collect current Alembic queries for this app
                    rows = conn.execute(
                        text(
                            """
                            SELECT now() AS ts, pid, state, wait_event_type, wait_event, query
                            FROM pg_stat_activity
                            WHERE application_name = :app
                            ORDER BY pid
                            """
                        ),
                        {"app": app_name},
                    ).mappings().all()

                    # Count waiters (not granted locks)
                    waiters = conn.execute(
                        text(
                            """
                            SELECT count(*) AS waiting
                            FROM pg_locks w
                            WHERE NOT w.granted
                            """
                        )
                    ).scalar()

                    # Count advisory locks
                    advisories = conn.execute(
                        text(
                            """
                            SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'
                            """
                        )
                    ).scalar()

                    sample = {
                        "ts": time.time(),
                        "alembic_sessions": [
                            {
                                "pid": r["pid"],
                                "state": r["state"],
                                "wait_event_type": r["wait_event_type"],
                                "wait_event": r["wait_event"],
                                "query": (" ".join((r.get("query") or "").split()))[:300],
                            }
                            for r in rows
                        ],
                        "waiting_locks": int(waiters or 0),
                        "advisory_locks": int(advisories or 0),
                    }
                    samples.append(sample)
                    # Print a concise line for real-time visibility
                    print(
                        f"[diagnose-001] sessions={len(sample['alembic_sessions'])} "
                        f"waiting_locks={sample['waiting_locks']} advisory={sample['advisory_locks']} "
                        f"last_query=\"{(sample['alembic_sessions'][0]['query'] if sample['alembic_sessions'] else '')}\""
                    )
                except Exception as e:
                    print(f"[diagnose-001] monitor error (ignored): {e}")
                # Polling interval
                stop_evt.wait(timeout=1.0)

    t = threading.Thread(target=_monitor, daemon=True)
    t.start()

    started = False
    completed = False
    error: Optional[str] = None
    start_time = time.time()
    last_query = ""

    try:
        started = True
        # Run only up to 001 to pinpoint the first problematic DDL
        command.upgrade(cfg, "001")
        completed = True
    except Exception as e:
        error = str(e)
    finally:
        duration = time.time() - start_time
        stop_evt.set()
        t.join(timeout=5)

        # Determine last seen query if available
        if samples and samples[-1]["alembic_sessions"]:
            last_query = samples[-1]["alembic_sessions"][0]["query"]

    # Provide a human hint based on last_query and waits
    note = ""
    if not completed and samples:
        # If waiting_locks is consistently > 0, likely blocked by another transaction
        waiting_counts = [s["waiting_locks"] for s in samples[-10:]]
        if any(c > 0 for c in waiting_counts):
            note = "The DDL appears blocked by existing locks. Check pg_stat_activity for blockers."
        elif "CREATE TYPE" in last_query.upper():
            note = "Hanging during enum type creation; ensure no concurrent transactions referencing or altering this type."
        elif "CREATE TABLE" in last_query.upper():
            note = "Hanging during table creation; verify no conflicting table or lock on pg_class/relations."
        else:
            note = "Hanging during an unclassified step; see monitor logs above for more details."

    return {
        "application_name": app_name,
        "started": started,
        "completed": completed,
        "duration_seconds": round(duration, 3),
        "last_seen_query": last_query,
        "lock_samples": samples[:50],  # limit to keep output reasonable
        "error": error,
        "note": note,
    }


def diagnose_initial_state(engine: Engine = sync_engine) -> Dict[str, Any]:
    """
    Diagnose current DB state related to advisory locks and initial migration (001).

    Returns:
        Dict with:
            - lock_summary: details of advisory/blocked sessions
            - alembic_versions: list of version rows (can be empty if table doesn't exist)
            - initial_schema_summary: presence of 001 tables and partial state flags
    """
    print("==== Diagnose: Inspecting Postgres for locks and initial migration state ====")
    lock_summary = inspect_locks(engine=engine)
    print(f"Locks -> advisory_locks_count={lock_summary['advisory_locks_count']} blocked_sessions_count={lock_summary['blocked_sessions_count']}")
    with engine.connect() as conn:
        versions = _fetch_alembic_versions(conn)
        print(f"Alembic versions row(s): {versions if versions else 'None'}")
        schema_summary = _inspect_initial_schema(conn)
        print(f"Initial schema present tables: {schema_summary['present_tables']}")
        print(f"Initial schema missing tables: {schema_summary['missing_tables']}")
        if schema_summary["partial"]:
            print("WARNING: Partial initial schema detected (some tables present, some missing).")
    return {
        "lock_summary": lock_summary,
        "alembic_versions": versions,
        "initial_schema_summary": schema_summary,
    }


# PUBLIC_INTERFACE
def repair_initial_migration(lock_key: Optional[str] = None, engine: Engine = sync_engine) -> Dict[str, Any]:
    """
    Diagnose and attempt repair of the initial migration (001) and clear advisory locks.

    Strategy:
    1) Inspect and log advisory locks and blocked sessions.
    2) Forcibly clear advisory lock holders using ALEMBIC_ADVISORY_LOCK_KEY (or provided lock_key).
    3) Analyze alembic_version and presence of initial migration tables.
    4) If alembic_version is inconsistent or partial AND there are no initial tables present,
       reset alembic_version, stamp base, and run alembic upgrade to '001'.
       If partial initial tables are present, we will NOT attempt to re-create 001 tables to avoid
       collisions; instead we will stamp to '001' if needed and log the manual remediation guidance.
    5) Log all actions prominently for diagnosis.

    Returns:
        Dict summary of actions and final state.
    """
    print("=======================================================================")
    print("🔧 Repair: Inspecting and repairing initial migration (001) if needed")
    print("=======================================================================")

    # 1) Inspect locks/state
    state_before = diagnose_initial_state(engine=engine)

    # 2) Clear advisory locks
    print("---- Clearing advisory lock holders (if any) ----")
    clear_result = clear_advisory_lock_holders(lock_key=lock_key, engine=engine)
    print(f"Advisory lock key: {clear_result['lock_key']}")
    print(f"Terminated PIDs: {clear_result['terminated_pids']}")
    if clear_result["errors"]:
        print(f"Terminate errors: {clear_result['errors']}")

    # 3) Re-check alembic_version and initial schema
    print("---- Re-checking Alembic version and initial schema state ----")
    with engine.begin() as conn:
        versions = _fetch_alembic_versions(conn)
        schema_summary = _inspect_initial_schema(conn)

    print(f"Alembic versions row(s) now: {versions if versions else 'None'}")
    print(f"Present initial tables: {schema_summary['present_tables']}")
    print(f"Missing initial tables: {schema_summary['missing_tables']}")

    action_taken = []
    upgrade_status = {"applied_001": False, "error": None, "note": ""}

    # 4) Decide and act
    try:
        if schema_summary["all_absent"]:
            print("No initial tables present; safe to reset and re-apply 001.")
            alembic_reset()
            print("Alembic version table truncated (if existed).")
            alembic_stamp_base()
            print("Alembic stamped to base.")
            alembic_upgrade("001")
            print("✅ Alembic upgraded to '001' successfully.")
            upgrade_status["applied_001"] = True
            action_taken += ["alembic_reset", "alembic_stamp_base", "alembic_upgrade_001"]
        elif schema_summary["partial"]:
            print("⚠️ Partial initial migration detected. NOT re-applying 001 to avoid DDL conflicts.")
            if "001" not in versions:
                # Stamp to 001 if not already
                alembic_stamp_base()
                print("Stamped base; stamping 001 to sync alembic_version with existing partial schema.")
                cfg = _alembic_config()
                command.stamp(cfg, "001")
                action_taken += ["alembic_stamp_base", "alembic_stamp_001"]
            upgrade_status["note"] = (
                "Partial initial schema detected. Skipped re-applying 001 to avoid table conflicts. "
                "Consider manually dropping conflicting tables or restoring from backup, then rerun."
            )
        else:
            # all_present
            print("Initial tables already present.")
            if "001" not in versions:
                print("Alembic version not at 001; stamping to 001 for consistency.")
                alembic_stamp_base()
                cfg = _alembic_config()
                command.stamp(cfg, "001")
                action_taken += ["alembic_stamp_base", "alembic_stamp_001"]
            else:
                print("Alembic version indicates 001 already applied. No action needed on 001.")
    except Exception as e:
        upgrade_status["error"] = str(e)
        print(f"❌ Error while attempting to repair/apply 001: {e}")

    # 5) Summarize final state
    print("---- Final state summary ----")
    final_state = diagnose_initial_state(engine=engine)

    print("=======================================================================")
    print("Repair operation completed.")
    print("=======================================================================")

    return {
        "state_before": state_before,
        "clear_result": clear_result,
        "actions": action_taken,
        "apply_001_result": upgrade_status,
        "state_after": final_state,
    }
