This project includes additional diagnostics to surface hidden Alembic rollback causes:

- alembic/env.py enhanced:
  - Extra try/except around run_migrations to log full tracebacks.
  - Post-run integrity probe executes SELECT 1 and SET CONSTRAINTS ALL IMMEDIATE before Alembic updates version table.
  - Clear BEGIN/END prints around Alembic transaction in do_run_migrations().

Operational tips:
- To enable SQL echo for deeper visibility set ALEMBIC_SQL_ECHO=1 (or LOG_SQL=true) in environment.
- Verify that the database role used by Alembic has SELECT/UPDATE permissions on alembic_version.
- Ensure no triggers exist on alembic_version and check for deferred triggers on emoji_assets that might fail only at commit.
- Compare the printed FINAL-PROBE txid_current in migration logs with PostgreSQL server logs for matching error entries at commit time.

If rollbacks persist with no in-migration errors:
- Temporarily set PostgreSQL server log_min_messages to INFO and log_statement='all' for the migration session (or enable pgaudit) to capture the exact failing statement.
- Run: ALEMBIC_SQL_ECHO=1 LOG_SQL=1 to see SQL emitted by Alembic and SQLAlchemy.
