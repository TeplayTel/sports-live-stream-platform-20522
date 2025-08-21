"""Add users.preferences column and align users table with ORM

Revision ID: 002_add_users_preferences_and_align_users_table
Revises: 001_create_simple_users_table
Create Date: 2025-08-21

Purpose:
- Add 'preferences' JSON column to 'users' table to resolve registration error.
- Best-effort alignment of 'users' table with ORM (UUID PK, username, full_name, avatar_url, role enum, is_active, updated_at).
  All changes are written in an idempotent and safe manner for existing minimal schemas.

Notes:
- We avoid dropping/recreating tables. For user_id migration, if it's already Integer, we keep it as-is (compat mode).
- The application code is defensive around role and timestamps.

"""
from typing import Optional

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_add_users_preferences_and_align_users_table"
down_revision: Optional[str] = "001_create_simple_users_table"
branch_labels = None
depends_on = None


def _get_columns_info(table: str, schema: str = "public"):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {}
    for col in insp.get_columns(table, schema=schema):
        cols[col["name"]] = col
    return cols


def _get_indexes(table: str, schema: str = "public"):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return {idx["name"]: idx for idx in insp.get_indexes(table, schema=schema)}


def _get_unique_constraints(table: str, schema: str = "public"):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    ucs = {}
    for uc in insp.get_unique_constraints(table, schema=schema):
        # uc["column_names"] is list
        ucs[uc["name"]] = uc
    return ucs


def _table_exists(table: str, schema: str = "public") -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names(schema=schema)


# PUBLIC_INTERFACE
def upgrade() -> None:
    """Apply migration: add users.preferences and align schema where safe.

    Operations (idempotent):
    - Ensure users table exists (created by 001).
    - Add 'username' (nullable for compatibility) with unique index if missing.
    - Add 'full_name' (nullable) if missing.
    - Add 'avatar_url' (nullable) if missing.
    - Add 'role' enum-like (TEXT fallback) if missing to avoid enum type creation conflicts.
    - Add 'is_active' (BOOLEAN, default True) if missing.
    - Add 'preferences' (JSON/JSONB) if missing.
    - Add 'updated_at' (TIMESTAMPTZ, default now()) if missing.
    - If created_at lacks timezone, leave as-is; app handles it.
    - Keep existing user_id type; we won't alter PK type in this migration for safety.
    """
    schema = "public"
    table = "users"

    op.execute("CREATE SCHEMA IF NOT EXISTS public")

    if not _table_exists(table, schema):
        # As a fallback, create a minimally compatible users table with required cols
        op.create_table(
            table,
            sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("username", sa.String(length=50), nullable=True, unique=True),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column("avatar_url", sa.Text(), nullable=True),
            sa.Column("role", sa.String(length=32), nullable=False, server_default=sa.text("'user'")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            schema=schema,
        )
        # indexes
        op.create_index("ix_users_email_unique", table, ["email"], unique=True, schema=schema)
        op.create_index("ix_users_username_unique", table, ["username"], unique=True, schema=schema)
        return

    # Table exists: patch missing columns safely
    cols = _get_columns_info(table, schema)

    # username
    if "username" not in cols:
        op.add_column(table, sa.Column("username", sa.String(length=50), nullable=True), schema=schema)
        # unique index (nullable column; uniqueness enforced when provided)
        idxs = _get_indexes(table, schema)
        ucs = _get_unique_constraints(table, schema)
        if "ix_users_username_unique" not in idxs and "users_username_key" not in ucs:
            op.create_index("ix_users_username_unique", table, ["username"], unique=True, schema=schema)

    # full_name
    if "full_name" not in cols:
        op.add_column(table, sa.Column("full_name", sa.String(length=255), nullable=True), schema=schema)

    # avatar_url
    if "avatar_url" not in cols:
        op.add_column(table, sa.Column("avatar_url", sa.Text(), nullable=True), schema=schema)

    # role (use VARCHAR/TEXT to avoid enum type conflicts across envs)
    if "role" not in cols:
        op.add_column(
            table,
            sa.Column("role", sa.String(length=32), nullable=False, server_default=sa.text("'user'")),
            schema=schema,
        )

    # is_active
    if "is_active" not in cols:
        op.add_column(
            table,
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            schema=schema,
        )

    # preferences (JSON/JSONB)
    if "preferences" not in cols:
        try:
            # Prefer JSONB on Postgres
            op.add_column(
                table,
                sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                schema=schema,
            )
        except Exception:
            # Fallback to generic JSON if dialect unsupported in some context
            op.add_column(
                table,
                sa.Column("preferences", sa.JSON(), nullable=True),
                schema=schema,
            )

    # updated_at
    if "updated_at" not in cols:
        op.add_column(
            table,
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            schema=schema,
        )

    # Ensure email unique index exists
    idxs = _get_indexes(table, schema)
    ucs = _get_unique_constraints(table, schema)
    if "ix_users_email_unique" not in idxs and "users_email_key" not in ucs:
        op.create_index("ix_users_email_unique", table, ["email"], unique=True, schema=schema)


# PUBLIC_INTERFACE
def downgrade() -> None:
    """Revert preferences and alignment columns where safe.

    We only drop columns that we added in this migration:
    - preferences
    - updated_at
    - is_active
    - role
    - avatar_url
    - full_name
    - username (+ unique index)
    """
    schema = "public"
    table = "users"

    if not _table_exists(table, schema):
        return

    cols = _get_columns_info(table, schema)
    idxs = _get_indexes(table, schema)

    if "ix_users_username_unique" in idxs:
        try:
            op.drop_index("ix_users_username_unique", table_name=table, schema=schema)
        except Exception:
            pass

    for col in ["preferences", "updated_at", "is_active", "role", "avatar_url", "full_name", "username"]:
        if col in cols:
            try:
                op.drop_column(table, col, schema=schema)
            except Exception:
                # Ignore if constrained or used; safe downgrade isn't critical for dev envs
                pass
