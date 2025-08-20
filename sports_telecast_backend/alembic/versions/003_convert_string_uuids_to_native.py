"""Convert String UUIDs to native PostgreSQL UUIDs with Python-side UUID generation and FK-safe mapping

Revision ID: 003
Revises: 002
Create Date: 2024-08-07 13:00:00.000000

This migration:
- Validates and normalizes all string UUID columns to valid UUID strings first (fixing NULL/invalid data).
- All new UUIDs are generated in Python using uuid.uuid4(); no server-side generation is used.
- Propagates changes to child tables using a temporary mapping approach to maintain referential integrity.
- Drops foreign keys prior to updating IDs to avoid FK violations, alters column types to UUID using USING casts,
  and re-creates equivalent foreign keys.
- Logs actions and counts at each step to aid debugging and rollback safety.

It avoids half-applied changes by running in a single transaction; any error will rollback the whole migration.
"""
from alembic import op
from typing import List, Optional, Set, Tuple
import uuid

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


# Regex used in Postgres to test for valid canonical UUID strings (lowercase hex is tolerated by ~*).
UUID_REGEX = r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


def _log(msg: str) -> None:
    print(f"[003_uuid_migration] {msg}")


def _drop_fk_for_column(bind, table_name: str, column_name: str) -> List[Tuple[str, str]]:
    """
    Drop all FK constraints on a given table for a given column (as the FK-holding side).
    Returns a list of (constraint_name, table_name). Constraint recreation is handled explicitly later.
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
    dropped: List[Tuple[str, str]] = []
    for r in rows:
        cname = r["constraint_name"]
        _log(f"  - Dropping constraint {cname} on {table_name}")
        bind.exec_driver_sql(
            f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{cname}"'
        )
        dropped.append((cname, table_name))
    return dropped


def _get_invalid_ids(bind, table: str, col: str) -> List[Optional[str]]:
    """
    Return list of DISTINCT invalid (or NULL) values from table.col.
    """
    res = bind.exec_driver_sql(
        f"""
        SELECT DISTINCT {col} AS old_id
        FROM {table}
        WHERE {col} IS NULL
           OR NOT ({col} ~* %s)
        """,
        (UUID_REGEX,),
    )
    rows = res.mappings().all()
    return [row["old_id"] for row in rows]


def _get_existing_valid_ids(bind, table: str, col: str) -> Set[str]:
    """
    Return set of existing valid UUID string values in table.col.
    """
    res = bind.exec_driver_sql(
        f"""
        SELECT DISTINCT {col} AS id
        FROM {table}
        WHERE {col} IS NOT NULL
          AND ({col} ~* %s)
        """,
        (UUID_REGEX,),
    )
    return {row["id"] for row in res.mappings().all()}


def _generate_python_mapping(
    invalid_ids: List[Optional[str]], existing_ids: Set[str]
) -> List[Tuple[Optional[str], str]]:
    """
    Generate a mapping list of (old_id, new_id_string) for the provided invalid_ids.
    Ensures new IDs do not collide with existing_ids or previously generated IDs.
    """
    mapping: List[Tuple[Optional[str], str]] = []
    used: Set[str] = set(existing_ids)  # guard against collisions
    for old in invalid_ids:
        new_val = str(uuid.uuid4())
        while new_val in used:
            new_val = str(uuid.uuid4())
        used.add(new_val)
        mapping.append((old, new_val))
    return mapping


def _apply_mapping_via_temp_table(
    bind,
    mapping: List[Tuple[Optional[str], str]],
    parent_table: str,
    parent_col: str,
    child_refs: List[Tuple[str, str]],
) -> None:
    """
    Create a temporary mapping table and apply updates to parent and child tables.
    Optionally remove orphan/invalid child rows after propagation.

    mapping is a list of (old_id, new_id) where old_id can be None.
    """
    _log(
        f"Applying mapping for {parent_table}.{parent_col} using temp table; rows={len(mapping)}"
    )
    # Create temp mapping table (auto-dropped at commit)
    bind.exec_driver_sql(
        f"""
        CREATE TEMP TABLE tmp_map_{parent_table}_{parent_col} (
            old_id TEXT,
            new_id TEXT
        ) ON COMMIT DROP
        """
    )

    # Insert mapping rows (row-by-row to avoid driver differences)
    for old_id, new_id in mapping:
        bind.exec_driver_sql(
            f"""
            INSERT INTO tmp_map_{parent_table}_{parent_col} (old_id, new_id)
            VALUES (%s, %s)
            """,
            (old_id, new_id),
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

    # Propagate to child tables
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

        # Remove orphan child rows and invalid UUID formats in child col (defensive cleanup)
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


def _ensure_valid_uuid_strings_with_mapping_python(
    bind,
    parent_table: str,
    parent_col: str,
    child_refs: List[Tuple[str, str]],
) -> None:
    """
    Ensure parent_table.parent_col contains only valid UUID strings.
    Uses Python to generate new UUIDs for NULL/invalid values and propagates the mapping to children.
    """
    _log(f"Validating and normalizing {parent_table}.{parent_col} as UUID strings (Python-side UUIDs)")
    invalids = _get_invalid_ids(bind, parent_table, parent_col)
    if not invalids:
        _log(f"  - No invalid/NULL IDs found in {parent_table}.{parent_col}")
        return

    existing_valid = _get_existing_valid_ids(bind, parent_table, parent_col)
    mapping = _generate_python_mapping(invalids, existing_valid)
    _apply_mapping_via_temp_table(bind, mapping, parent_table, parent_col, child_refs)

    # Defensive: verify no remaining invalids; if any, generate again
    remaining = _get_invalid_ids(bind, parent_table, parent_col)
    if remaining:
        _log(f"  - Defensive pass: fixing {len(remaining)} remaining invalid IDs in {parent_table}.{parent_col}")
        existing_valid = _get_existing_valid_ids(bind, parent_table, parent_col)
        mapping2 = _generate_python_mapping(remaining, existing_valid)
        _apply_mapping_via_temp_table(bind, mapping2, parent_table, parent_col, child_refs)


def _ensure_valid_uuid_strings_simple_python(bind, table: str, col: str) -> None:
    """
    Ensure a non-FK string UUID column (no children relying on it) contains valid UUID strings.
    Generates new UUIDs in Python and updates rows individually via a temp mapping for efficiency.
    """
    _log(f"Validating simple column {table}.{col} as UUID strings (Python-side UUIDs)")
    invalids = _get_invalid_ids(bind, table, col)
    if not invalids:
        _log(f"  - No invalid/NULL IDs found in {table}.{col}")
        return

    existing_valid = _get_existing_valid_ids(bind, table, col)
    mapping = _generate_python_mapping(invalids, existing_valid)
    _apply_mapping_via_temp_table(bind, mapping, table, col, child_refs=[])

    # Defensive second pass
    remaining = _get_invalid_ids(bind, table, col)
    if remaining:
        _log(f"  - Defensive pass: fixing {len(remaining)} remaining invalid IDs in {table}.{col}")
        existing_valid = _get_existing_valid_ids(bind, table, col)
        mapping2 = _generate_python_mapping(remaining, existing_valid)
        _apply_mapping_via_temp_table(bind, mapping2, table, col, child_refs=[])


def _alter_column_to_uuid(bind, table: str, col: str) -> None:
    _log(f'Altering column type to UUID for {table}.{col}')
    bind.exec_driver_sql(
        f'ALTER TABLE "{table}" ALTER COLUMN "{col}" TYPE uuid USING "{col}"::uuid'
    )


def upgrade() -> None:
    """
    Upgrade: Convert string(36) UUID-like columns to native UUID using Python-side generation for any missing/invalid IDs.
    Steps:
      1) Drop foreign keys that might block updates and type changes.
      2) Normalize/propagate IDs using Python-generated UUIDs.
      3) Alter all relevant columns to UUID type.
      4) Re-create foreign keys with deterministic names.
    """
    bind = op.get_bind()
    _log("BEGIN upgrade -> 003: Convert String UUIDs to native UUIDs using Python-side uuid4()")

    # 1) Drop foreign key constraints on child tables prior to any updates to prevent FK violations
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

    # 2) Normalize parent tables and cascade mapping to children (Python-generated UUIDs)
    _ensure_valid_uuid_strings_with_mapping_python(
        bind,
        parent_table="users",
        parent_col="user_id",
        child_refs=[("user_profiles", "user_id"), ("user_emoji_reactions", "user_id")],
    )

    _ensure_valid_uuid_strings_with_mapping_python(
        bind,
        parent_table="teams",
        parent_col="team_id",
        child_refs=[("matches", "home_team_id"), ("matches", "away_team_id"), ("match_events", "team_id")],
    )

    _ensure_valid_uuid_strings_with_mapping_python(
        bind,
        parent_table="events",
        parent_col="event_id",
        child_refs=[("matches", "event_id"), ("user_emoji_reactions", "event_id")],
    )

    _ensure_valid_uuid_strings_with_mapping_python(
        bind,
        parent_table="matches",
        parent_col="match_id",
        child_refs=[("highlights", "match_id"), ("match_events", "match_id"), ("schedule_matches", "match_id")],
    )

    _ensure_valid_uuid_strings_with_mapping_python(
        bind,
        parent_table="emoji_assets",
        parent_col="emoji_id",
        child_refs=[("user_emoji_reactions", "emoji_id")],
    )

    _ensure_valid_uuid_strings_with_mapping_python(
        bind,
        parent_table="schedules",
        parent_col="schedule_id",
        child_refs=[("schedule_matches", "schedule_id")],
    )

    # Standalone primary keys not referenced by others
    _ensure_valid_uuid_strings_simple_python(bind, "user_profiles", "profile_id")
    _ensure_valid_uuid_strings_simple_python(bind, "user_emoji_reactions", "reaction_id")
    _ensure_valid_uuid_strings_simple_python(bind, "highlights", "highlight_id")
    _ensure_valid_uuid_strings_simple_python(bind, "match_events", "event_id")

    # 3) Alter column types in place using USING casts
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
