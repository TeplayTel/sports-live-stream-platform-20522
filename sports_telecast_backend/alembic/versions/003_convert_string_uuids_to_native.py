"""Convert String UUIDs to native PostgreSQL UUIDs with FK-safe mapping and validation

Revision ID: 003
Revises: 002
Create Date: 2024-08-07 13:00:00.000000

This migration:
- Validates and normalizes all string UUID columns to valid UUID strings first (fixing NULL/invalid data).
- Propagates changes to child tables using a temporary mapping approach to maintain referential integrity.
- Drops foreign keys that would block type changes, alters column types in place to UUID using USING casts,
  and re-creates equivalent foreign keys.
- Logs actions and counts at each step to aid debugging and rollback safety.

It avoids half-applied changes by running in a single transaction; any error will rollback the whole migration.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


UUID_REGEX = r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


def _log(msg: str) -> None:
    print(f"[003_uuid_migration] {msg}")


def _choose_uuid_generator(bind) -> str:
    """
    Pick an available server-side UUID generator function string.
    Preference: gen_random_uuid() from pgcrypto; fallback to uuid_generate_v4() from uuid-ossp.
    """
    try:
        has_gen = bind.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'gen_random_uuid')"
        ).scalar()
    except Exception:
        has_gen = False
    try:
        has_ossp = bind.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'uuid_generate_v4')"
        ).scalar()
    except Exception:
        has_ossp = False

    if has_gen:
        return "gen_random_uuid()"
    if has_ossp:
        return "uuid_generate_v4()"
    # Try creating extensions, then re-check
    try:
        bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        has_gen = bind.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'gen_random_uuid')"
        ).scalar()
    except Exception:
        has_gen = False
    if has_gen:
        return "gen_random_uuid()"
    try:
        bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        has_ossp = bind.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'uuid_generate_v4')"
        ).scalar()
    except Exception:
        has_ossp = False
    if has_ossp:
        return "uuid_generate_v4()"

    # Last-resort SQL expression to synthesize a UUID (not cryptographically strong)
    # Uses MD5 of current_timestamp and random() sources to build a UUID v4-like value.
    return "(concat_ws('-', substr(md5(random()::text),1,8), substr(md5(clock_timestamp()::text),1,4), '4'||substr(md5(random()::text),1,3), substr('89ab', (random()*3)::int+1, 1)||substr(md5(random()::text),1,3), substr(md5(clock_timestamp()::text||random()::text),1,12)))::uuid"


def _drop_fk_for_column(bind, table_name: str, column_name: str) -> list[tuple[str, str]]:
    """
    Drop all FK constraints on a given table for a given column (as the FK-holding side).
    Returns a list of (constraint_name, ddl) where ddl holds minimal info to recreate later is not provided;
    constraint recreation is performed explicitly elsewhere with known relationships.
    """
    _log(f"Dropping FK(s) on {table_name}.{column_name} if any.")
    rows = bind.exec_driver_sql(
        """
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name = %s
          AND kcu.column_name = %s
        """,
        (table_name, column_name),
    ).mappings().all()
    dropped = []
    for r in rows:
        cname = r["constraint_name"]
        _log(f"  - Dropping constraint {cname} on {table_name}")
        bind.exec_driver_sql(
            f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{cname}"'
        )
        dropped.append((cname, table_name))
    return dropped


def _ensure_valid_uuid_strings_with_mapping(
    bind,
    parent_table: str,
    parent_col: str,
    child_refs: list[tuple[str, str]],
    uuid_gen_sql: str,
) -> None:
    """
    Ensure parent_table.parent_col contains only valid UUID strings.
    - Creates a temp mapping of invalid/NULL old -> new uuid strings.
    - Updates parent table using mapping.
    - Propagates mapping to child_refs (list of (child_table, child_col)).
    - Removes orphan child rows that reference non-existent parents after update.
    """
    _log(f"Validating and normalizing {parent_table}.{parent_col} as UUID strings")
    # Create temp mapping table (auto-dropped at commit)
    bind.exec_driver_sql(
        f"""
        CREATE TEMP TABLE tmp_map_{parent_table}_{parent_col} (
            old_id TEXT,
            new_id TEXT
        ) ON COMMIT DROP
        """
    )
    # Populate mapping for invalid/NULL IDs
    ins = bind.exec_driver_sql(
        f"""
        WITH invalid_rows AS (
            SELECT {parent_col} AS old_id
            FROM {parent_table}
            WHERE {parent_col} IS NULL
               OR NOT ({parent_col} ~* %s)
        )
        INSERT INTO tmp_map_{parent_table}_{parent_col} (old_id, new_id)
        SELECT old_id,
               CASE
                 WHEN old_id IS NULL THEN ({uuid_gen_sql})::text
                 ELSE ({uuid_gen_sql})::text
               END AS new_id
        FROM invalid_rows
        """,
        (UUID_REGEX,),
    )
    _log(
        f"  - Inserted {ins.rowcount if hasattr(ins, 'rowcount') else 'N/A'} mapping rows for {parent_table}.{parent_col}"
    )

    # Update parent table using mapping
    up_p = bind.exec_driver_sql(
        f"""
        UPDATE {parent_table} p
        SET {parent_col} = m.new_id
        FROM tmp_map_{parent_table}_{parent_col} m
        WHERE p.{parent_col} IS NOT DISTINCT FROM m.old_id
        """
    )
    _log(
        f"  - Parent updates applied: {up_p.rowcount if hasattr(up_p,'rowcount') else 'N/A'}"
    )

    # Propagate to children
    for child_table, child_col in child_refs:
        _log(f"  - Propagating mapping to child {child_table}.{child_col}")
        up_c = bind.exec_driver_sql(
            f"""
            UPDATE {child_table} c
            SET {child_col} = m.new_id
            FROM tmp_map_{parent_table}_{parent_col} m
            WHERE c.{child_col} IS NOT DISTINCT FROM m.old_id
            """
        )
        _log(
            f"    -> Child updates applied: {up_c.rowcount if hasattr(up_c,'rowcount') else 'N/A'}"
        )

        # Remove orphan child rows (no matching parent) and invalid UUID formats in child col
        orphans = bind.exec_driver_sql(
            f"""
            WITH candidates AS (
                SELECT c.*
                FROM {child_table} c
                WHERE c.{child_col} IS NULL
                   OR NOT (c.{child_col} ~* %s)
                   OR NOT EXISTS (
                        SELECT 1 FROM {parent_table} p
                         WHERE p.{parent_col} = c.{child_col}
                   )
            )
            DELETE FROM {child_table} c
            USING candidates d
            WHERE c.ctid = d.ctid
            """,
            (UUID_REGEX,),
        )
        _log(
            f"    -> Deleted orphan/invalid child rows from {child_table}: {orphans.rowcount if hasattr(orphans,'rowcount') else 'N/A'}"
        )

    # Finally ensure parent has only valid UUID strings (defensive)
    fix_p = bind.exec_driver_sql(
        f"""
        UPDATE {parent_table}
        SET {parent_col} = ({uuid_gen_sql})::text
        WHERE {parent_col} IS NULL OR NOT ({parent_col} ~* %s)
        """,
        (UUID_REGEX,),
    )
    _log(
        f"  - Defensive parent fixes (post-propagation): {fix_p.rowcount if hasattr(fix_p,'rowcount') else 'N/A'}"
    )


def _ensure_valid_uuid_strings_simple(bind, table: str, col: str, uuid_gen_sql: str) -> None:
    """
    Ensure a non-FK string UUID column (no children relying on it) contains valid UUID strings.
    """
    _log(f"Validating simple column {table}.{col} as UUID strings")
    fix = bind.exec_driver_sql(
        f"""
        UPDATE {table}
        SET {col} = ({uuid_gen_sql})::text
        WHERE {col} IS NULL OR NOT ({col} ~* %s)
        """,
        (UUID_REGEX,),
    )
    _log(
        f"  - Normalized {fix.rowcount if hasattr(fix,'rowcount') else 'N/A'} rows in {table}.{col}"
    )


def _alter_column_to_uuid(bind, table: str, col: str) -> None:
    _log(f"Altering column type to UUID for {table}.{col}")
    bind.exec_driver_sql(
        f'ALTER TABLE "{table}" ALTER COLUMN "{col}" TYPE uuid USING "{col}"::uuid'
    )


def upgrade() -> None:
    bind = op.get_bind()
    _log("BEGIN upgrade -> 003: Convert String UUIDs to native UUIDs with FK-safe process")

    uuid_gen_sql = _choose_uuid_generator(bind)
    _log(f"Using UUID generator expression: {uuid_gen_sql}")

    # 1) Normalize parent tables and cascade mapping to children
    # users -> children
    _ensure_valid_uuid_strings_with_mapping(
        bind,
        parent_table="users",
        parent_col="user_id",
        child_refs=[("user_profiles", "user_id"), ("user_emoji_reactions", "user_id")],
        uuid_gen_sql=uuid_gen_sql,
    )

    # teams -> children (matches home/away, match_events.team_id used as reference but no FK)
    _ensure_valid_uuid_strings_with_mapping(
        bind,
        parent_table="teams",
        parent_col="team_id",
        child_refs=[("matches", "home_team_id"), ("matches", "away_team_id"), ("match_events", "team_id")],
        uuid_gen_sql=uuid_gen_sql,
    )

    # events -> children (matches.event_id and user_emoji_reactions.event_id as loose ref)
    _ensure_valid_uuid_strings_with_mapping(
        bind,
        parent_table="events",
        parent_col="event_id",
        child_refs=[("matches", "event_id"), ("user_emoji_reactions", "event_id")],
        uuid_gen_sql=uuid_gen_sql,
    )

    # matches -> children (highlights, match_events, schedule_matches)
    _ensure_valid_uuid_strings_with_mapping(
        bind,
        parent_table="matches",
        parent_col="match_id",
        child_refs=[("highlights", "match_id"), ("match_events", "match_id"), ("schedule_matches", "match_id")],
        uuid_gen_sql=uuid_gen_sql,
    )

    # emoji_assets -> children (user_emoji_reactions.emoji_id)
    _ensure_valid_uuid_strings_with_mapping(
        bind,
        parent_table="emoji_assets",
        parent_col="emoji_id",
        child_refs=[("user_emoji_reactions", "emoji_id")],
        uuid_gen_sql=uuid_gen_sql,
    )

    # schedules -> children (schedule_matches)
    _ensure_valid_uuid_strings_with_mapping(
        bind,
        parent_table="schedules",
        parent_col="schedule_id",
        child_refs=[("schedule_matches", "schedule_id")],
        uuid_gen_sql=uuid_gen_sql,
    )

    # Standalone primary keys not referenced by others
    _ensure_valid_uuid_strings_simple(bind, "user_profiles", "profile_id", uuid_gen_sql)
    _ensure_valid_uuid_strings_simple(bind, "user_emoji_reactions", "reaction_id", uuid_gen_sql)
    _ensure_valid_uuid_strings_simple(bind, "highlights", "highlight_id", uuid_gen_sql)
    _ensure_valid_uuid_strings_simple(bind, "match_events", "event_id", uuid_gen_sql)

    # 2) Drop foreign key constraints that would block type change (child side)
    # Explicitly drop known FK constraints by column on each child table
    fk_targets = [
        ("user_profiles", "user_id"),
        ("user_emoji_reactions", "user_id"),
        ("user_emoji_reactions", "emoji_id"),
        ("matches", "event_id"),
        ("matches", "home_team_id"),
        ("matches", "away_team_id"),
        ("highlights", "match_id"),
        ("match_events", "match_id"),
        ("schedule_matches", "match_id"),
        ("schedule_matches", "schedule_id"),
    ]
    for tbl, col in fk_targets:
        _drop_fk_for_column(bind, tbl, col)

    # 3) Alter column types in place using USING casts
    # Parents and their FKs
    to_convert = [
        # users related
        ("users", "user_id"),
        ("user_profiles", "user_id"),
        ("user_emoji_reactions", "user_id"),
        # teams related
        ("teams", "team_id"),
        ("matches", "home_team_id"),
        ("matches", "away_team_id"),
        ("match_events", "team_id"),
        # events related
        ("events", "event_id"),
        ("matches", "event_id"),
        ("user_emoji_reactions", "event_id"),
        # matches related
        ("matches", "match_id"),
        ("highlights", "match_id"),
        ("match_events", "match_id"),
        ("schedule_matches", "match_id"),
        # emoji related
        ("emoji_assets", "emoji_id"),
        ("user_emoji_reactions", "emoji_id"),
        # schedules related
        ("schedules", "schedule_id"),
        ("schedule_matches", "schedule_id"),
        # standalones
        ("user_profiles", "profile_id"),
        ("user_emoji_reactions", "reaction_id"),
        ("highlights", "highlight_id"),
        ("match_events", "event_id"),
    ]
    for tbl, col in to_convert:
        _alter_column_to_uuid(bind, tbl, col)

    # 4) Re-create foreign keys with explicit, deterministic names (no ON DELETE CASCADE to preserve original semantics)
    _log("Re-creating foreign keys")
    bind.exec_driver_sql(
        'ALTER TABLE "user_profiles" ADD CONSTRAINT "fk_user_profiles_user_id_users" FOREIGN KEY ("user_id") REFERENCES "users" ("user_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "user_emoji_reactions" ADD CONSTRAINT "fk_user_emoji_reactions_user_id_users" FOREIGN KEY ("user_id") REFERENCES "users" ("user_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "user_emoji_reactions" ADD CONSTRAINT "fk_user_emoji_reactions_emoji_id_emoji_assets" FOREIGN KEY ("emoji_id") REFERENCES "emoji_assets" ("emoji_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "matches" ADD CONSTRAINT "fk_matches_event_id_events" FOREIGN KEY ("event_id") REFERENCES "events" ("event_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "matches" ADD CONSTRAINT "fk_matches_home_team_id_teams" FOREIGN KEY ("home_team_id") REFERENCES "teams" ("team_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "matches" ADD CONSTRAINT "fk_matches_away_team_id_teams" FOREIGN KEY ("away_team_id") REFERENCES "teams" ("team_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "highlights" ADD CONSTRAINT "fk_highlights_match_id_matches" FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "match_events" ADD CONSTRAINT "fk_match_events_match_id_matches" FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "schedule_matches" ADD CONSTRAINT "fk_schedule_matches_match_id_matches" FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "schedule_matches" ADD CONSTRAINT "fk_schedule_matches_schedule_id_schedules" FOREIGN KEY ("schedule_id") REFERENCES "schedules" ("schedule_id")'
    )

    _log("END upgrade -> 003 completed.")


def downgrade() -> None:
    """
    Reverse: Drop FKs, alter UUID columns back to TEXT, and re-create FKs.
    """
    bind = op.get_bind()
    _log("BEGIN downgrade <- 003: Convert UUIDs back to string")

    # Drop FKs
    fk_targets = [
        ("user_profiles", "user_id"),
        ("user_emoji_reactions", "user_id"),
        ("user_emoji_reactions", "emoji_id"),
        ("matches", "event_id"),
        ("matches", "home_team_id"),
        ("matches", "away_team_id"),
        ("highlights", "match_id"),
        ("match_events", "match_id"),
        ("schedule_matches", "match_id"),
        ("schedule_matches", "schedule_id"),
    ]
    for tbl, col in fk_targets:
        _drop_fk_for_column(bind, tbl, col)

    # Alter types back to TEXT
    to_convert_back = [
        ("users", "user_id"),
        ("user_profiles", "user_id"),
        ("user_profiles", "profile_id"),
        ("user_emoji_reactions", "user_id"),
        ("user_emoji_reactions", "reaction_id"),
        ("user_emoji_reactions", "event_id"),
        ("user_emoji_reactions", "emoji_id"),
        ("teams", "team_id"),
        ("matches", "home_team_id"),
        ("matches", "away_team_id"),
        ("matches", "event_id"),
        ("matches", "match_id"),
        ("match_events", "team_id"),
        ("match_events", "match_id"),
        ("match_events", "event_id"),
        ("events", "event_id"),
        ("highlights", "match_id"),
        ("highlights", "highlight_id"),
        ("emoji_assets", "emoji_id"),
        ("schedules", "schedule_id"),
        ("schedule_matches", "schedule_id"),
        ("schedule_matches", "match_id"),
    ]
    _log("Altering UUID columns back to TEXT")
    for tbl, col in to_convert_back:
        bind.exec_driver_sql(
            f'ALTER TABLE "{tbl}" ALTER COLUMN "{col}" TYPE varchar(36) USING "{col}"::text'
        )

    # Re-create FKs as strings
    _log("Re-creating foreign keys (string types)")
    bind.exec_driver_sql(
        'ALTER TABLE "user_profiles" ADD CONSTRAINT "fk_user_profiles_user_id_users" FOREIGN KEY ("user_id") REFERENCES "users" ("user_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "user_emoji_reactions" ADD CONSTRAINT "fk_user_emoji_reactions_user_id_users" FOREIGN KEY ("user_id") REFERENCES "users" ("user_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "user_emoji_reactions" ADD CONSTRAINT "fk_user_emoji_reactions_emoji_id_emoji_assets" FOREIGN KEY ("emoji_id") REFERENCES "emoji_assets" ("emoji_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "matches" ADD CONSTRAINT "fk_matches_event_id_events" FOREIGN KEY ("event_id") REFERENCES "events" ("event_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "matches" ADD CONSTRAINT "fk_matches_home_team_id_teams" FOREIGN KEY ("home_team_id") REFERENCES "teams" ("team_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "matches" ADD CONSTRAINT "fk_matches_away_team_id_teams" FOREIGN KEY ("away_team_id") REFERENCES "teams" ("team_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "highlights" ADD CONSTRAINT "fk_highlights_match_id_matches" FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "match_events" ADD CONSTRAINT "fk_match_events_match_id_matches" FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "schedule_matches" ADD CONSTRAINT "fk_schedule_matches_match_id_matches" FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id")'
    )
    bind.exec_driver_sql(
        'ALTER TABLE "schedule_matches" ADD CONSTRAINT "fk_schedule_matches_schedule_id_schedules" FOREIGN KEY ("schedule_id") REFERENCES "schedules" ("schedule_id")'
    )

    _log("END downgrade <- 003 completed.")
