"""Ensure users table and constraints exist; prepare for JWT auth

Revision ID: 006_users_table_jwt_prep
Revises: 005_add_image_url_to_emoji_assets
Create Date: 2025-08-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_users_table_jwt_prep"
down_revision = "005_add_image_url_to_emoji_assets"
branch_labels = None
depends_on = None


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    insp = sa.inspect(connection)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def _table_exists(connection, table_name: str) -> bool:
    insp = sa.inspect(connection)
    return table_name in insp.get_table_names()


def upgrade():
    bind = op.get_bind()

    # Ensure user role enum exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userroleenum') THEN
                CREATE TYPE userroleenum AS ENUM ('user', 'admin', 'moderator');
            END IF;
        END$$;
        """
    )

    # Create users table if it doesn't exist
    if not _table_exists(bind, "users"):
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id UUID PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                username VARCHAR(50) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                avatar_url TEXT,
                role userroleenum NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                preferences JSON,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

    # Add any missing columns to align with application model
    columns_spec = [
        ("email", sa.String(255), False),
        ("username", sa.String(50), False),
        ("password_hash", sa.String(255), False),
        ("full_name", sa.String(255), True),
        ("avatar_url", sa.Text(), True),
        ("role", sa.Enum("user", "admin", "moderator", name="userroleenum"), False),
        ("is_active", sa.Boolean(), False),
        ("preferences", sa.JSON(), True),
        ("created_at", sa.DateTime(timezone=True), False),
        ("updated_at", sa.DateTime(timezone=True), False),
    ]

    # Ensure user_id column exists and is UUID
    if not _column_exists(bind, "users", "user_id"):
        op.add_column("users", sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True))

    # Add other columns if missing
    for col_name, col_type, nullable in columns_spec:
        if not _column_exists(bind, "users", col_name):
            op.add_column("users", sa.Column(col_name, col_type, nullable=nullable))

    # Ensure unique indexes on email and username
    # Use raw SQL to support IF NOT EXISTS
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)")


def downgrade():
    # This migration is additive and idempotent; do not drop table to avoid data loss.
    # We will only drop the created indexes if present to revert minimal changes.
    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    # Note: We intentionally keep the users table and enum types to preserve data.
