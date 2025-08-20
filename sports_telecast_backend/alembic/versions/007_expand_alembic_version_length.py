"""Expand alembic_version.version_num length to 64 chars

Revision ID: 007_expand_alembic_version_length
Revises: 006_users_table_jwt_prep
Create Date: 2025-08-20

This migration alters the alembic internal tracking table `alembic_version`
to support longer revision identifiers by expanding the `version_num`
column from VARCHAR(32) to VARCHAR(64).

Note:
- This is a no-op for some databases that store alembic_version as TEXT,
  but on backends where it is VARCHAR(32), this ensures compatibility with
  longer revision ids.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "007_expand_alembic_version_length"
down_revision = "006_users_table_jwt_prep"
branch_labels = None
depends_on = None


# PUBLIC_INTERFACE
def upgrade() -> None:
    """Upgrade: alter alembic_version.version_num to VARCHAR(64)."""
    # Some dialects (e.g., PostgreSQL) require USING clause or type casting is implicit.
    # alembic.op.alter_column is dialect-aware and will generate the proper DDL.
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


# PUBLIC_INTERFACE
def downgrade() -> None:
    """Downgrade: revert alembic_version.version_num to VARCHAR(32)."""
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
