#!/usr/bin/env python3
"""
Database maintenance CLI for Sports Telecast Backend.

Provides safe operations to:
- Inspect database locks
- Clear Alembic advisory locks (by lock key)
- Reset alembic_version to a known-good base
- Run Alembic migrations (upgrade/stamp)
- Diagnose and repair initial migration (001)
- Create/drop tables directly from ORM (for dev-only)

Usage:
  python manage_db.py locks
  python manage_db.py clear-locks [lock_key]
  python manage_db.py alembic-reset
  python manage_db.py alembic-stamp-base
  python manage_db.py alembic-upgrade [revision]
  python manage_db.py diagnose-initial
  python manage_db.py repair-initial [lock_key]
  python manage_db.py create
  python manage_db.py drop
"""
import sys
from typing import Optional

from src.database.connection import engine
from src.database.models import Base

# PUBLIC_INTERFACE
def _print_usage() -> None:
    """Print available CLI commands."""
    print(__doc__)


# PUBLIC_INTERFACE
def main(argv: list[str]) -> None:
    """
    Entry point for database maintenance commands.

    Commands:
        locks: Inspect active database locks including advisory locks.
        clear-locks [lock_key]: Clear/terminate sessions holding the specified advisory lock key
            (defaults to ALEMBIC_ADVISORY_LOCK_KEY or 653210987654321).
        alembic-reset: Reset alembic_version table (truncate) so migrations can re-apply cleanly.
        alembic-stamp-base: Stamp the database at 'base' (no migrations applied) without running scripts.
        alembic-upgrade [revision]: Run Alembic upgrade to the specified revision (default 'head').
        diagnose-initial: Inspect locks, alembic_version, and initial (001) schema tables with prominent logs.
        repair-initial [lock_key]: Force-clear advisory locks, repair alembic_version if inconsistent, and re-apply
            the '001' initial migration only when safe (no initial tables exist). Prominently logs actions/results.
        create: Create all tables using ORM metadata (dev only).
        drop: Drop all tables using ORM metadata (dev only).
    """
    if len(argv) < 2:
        _print_usage()
        sys.exit(1)

    cmd = argv[1].strip().lower()
    arg: Optional[str] = argv[2] if len(argv) > 2 else None

    if cmd == "create":
        Base.metadata.create_all(bind=engine)
        print("Database tables created.")
        return

    if cmd == "drop":
        Base.metadata.drop_all(bind=engine)
        print("Database tables dropped.")
        return

    # Lazy imports for Alembic/maintenance to avoid import cost for simple ops
    if cmd in {"locks", "clear-locks", "alembic-reset", "alembic-stamp-base", "alembic-upgrade", "diagnose-initial", "repair-initial"}:
        from src.database.maintenance import (
            inspect_locks,
            clear_advisory_lock_holders,
            alembic_reset,
            alembic_stamp_base,
            alembic_upgrade,
            diagnose_initial_state,
            repair_initial_migration,
        )

        if cmd == "locks":
            summary = inspect_locks()
            print("Lock summary:")
            for k, v in summary.items():
                print(f"  {k}: {v}")
            return

        if cmd == "clear-locks":
            lock_key = arg
            summary = clear_advisory_lock_holders(lock_key=lock_key)
            print("Clear advisory lock result:")
            for k, v in summary.items():
                print(f"  {k}: {v}")
            return

        if cmd == "alembic-reset":
            alembic_reset()
            print("alembic_version reset (TRUNCATE performed if table exists).")
            return

        if cmd == "alembic-stamp-base":
            alembic_stamp_base()
            print("Alembic stamped at base.")
            return

        if cmd == "alembic-upgrade":
            revision = arg or "head"
            alembic_upgrade(revision)
            print(f"Alembic upgrade to {revision} complete.")
            return

        if cmd == "diagnose-initial":
            result = diagnose_initial_state()
            print("Diagnosis complete. Summary:")
            for k, v in result.items():
                print(f"- {k}: {v}")
            return

        if cmd == "repair-initial":
            lock_key = arg  # optional
            result = repair_initial_migration(lock_key=lock_key)
            print("Repair process summary:")
            for k, v in result.items():
                print(f"- {k}: {v}")
            return

    print(f"Unknown command: {cmd}")
    _print_usage()
    sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
