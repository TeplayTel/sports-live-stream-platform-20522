"""Create simple users table

This migration resets the schema history to a minimal baseline for diagnostics.
It creates a single 'users' table with:
- user_id: SERIAL PRIMARY KEY
- email: VARCHAR(255) UNIQUE NOT NULL
- password_hash: VARCHAR(255) NOT NULL
- created_at: TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

Stamp base and then upgrade to this head to initialize a clean state.
See README for instructions.

Revision identifiers:
    revision: 001_create_simple_users_table
    down_revision: None
    branch_labels: None
    depends_on: None
"""

from typing import Optional

from alembic import op
import sqlalchemy as sa

# Alembic revision identifiers
revision: str = "001_create_simple_users_table"
down_revision: Optional[str] = None
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the current database schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema="public")


# PUBLIC_INTERFACE
def upgrade() -> None:
    """Apply the migration: create the minimal 'users' table if it does not already exist.

    This function is idempotent with respect to the users table creation; if the table
    already exists (e.g., due to a prior manual setup), it will skip creation.
    """
    # Ensure 'public' schema exists for Postgres (no-op on others)
    op.execute("CREATE SCHEMA IF NOT EXISTS public")

    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("user_id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=False),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            schema="public",
        )
        # Optional: create an explicit unique index for clarity (unique already set on column)
        op.create_index(
            "ix_users_email_unique",
            "users",
            ["email"],
            unique=True,
            schema="public",
            postgresql_where=None,
        )
    else:
        # If table exists, make a best-effort to ensure required columns and constraints exist.
        # This keeps the migration robust in dev environments.
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        columns = {col["name"] for col in inspector.get_columns("users", schema="public")}
        # Add missing columns if any
        if "password_hash" not in columns:
            op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=False), schema="public")
        if "created_at" not in columns:
            op.add_column(
                "users",
                sa.Column(
                    "created_at",
                    sa.TIMESTAMP(timezone=False),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                ),
                schema="public",
            )
        # Ensure email unique constraint/index exists
        indexes = {idx["name"] for idx in inspector.get_indexes("users", schema="public")}
        constraints = {uc.name for uc in inspector.get_unique_constraints("users", schema="public")}
        if "ix_users_email_unique" not in indexes and "users_email_key" not in constraints:
            # Create unique index if neither an index nor a named unique constraint is found
            op.create_index(
                "ix_users_email_unique",
                "users",
                ["email"],
                unique=True,
                schema="public",
            )


# PUBLIC_INTERFACE
def downgrade() -> None:
    """Revert the migration: drop the 'users' table if present."""
    # Drop index explicitly first to avoid dependency issues in some engines
    try:
        op.drop_index("ix_users_email_unique", table_name="users", schema="public")
    except Exception:
        # Index might not exist; ignore
        pass

    if _table_exists("users"):
        op.drop_table("users", schema="public")
