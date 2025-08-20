"""
Database maintenance utilities for Sports Telecast Backend.

This module provides utilities to:
- Inspect Postgres locks (including advisory locks)
- Clear/terminate sessions holding a specific advisory lock key
- Reset alembic_version safely and (re)apply migrations

These functions are used by manage_db.py. They rely on env vars:
- DATABASE_URL or POSTGRES_URL
- ALEMBIC_ADVISORY_LOCK_KEY (optional, default 653210987654321)
- ALEMBIC_LOCK_TIMEOUT (optional; for runtime settings)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

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
