# Implementation Summary

- Migration resilience: Added/verified an idempotent and cross-dialect migration (007_expand_alembic_version_length) to widen `alembic_version.version_num` from `VARCHAR(32)` to `VARCHAR(64)` to avoid failures when revision IDs exceed 32 characters.
- Alembic env pre-checks: `alembic/env.py` proactively widens the version column before Alembic writes/reads revision IDs and applies an in-memory truncation compatibility patch only when necessary (does not shorten real revision IDs in the DB).
- Diagnostics: Additional logging and advisory lock usage were implemented to improve visibility and avoid concurrent migration issues.

New migrations:
- 002_add_users_preferences_and_align_users_table: Adds users.preferences (JSONB) and ensures presence of username, full_name, avatar_url, role (text), is_active, and updated_at columns on the users table. This resolves registration failures caused by missing preferences. The migration is idempotent and safe against pre-existing minimal schemas from 001.

Operational tips:
- If you still encounter errors about `alembic_version.version_num` width, run `alembic upgrade head` to apply migration `007_expand_alembic_version_length`.
- Ensure the DB user has permissions to ALTER the `alembic_version` table.
- Apply the latest schema with: `python sports_telecast_backend/init_db.py` or by starting the FastAPI app which runs migrations on startup.
