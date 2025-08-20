"""create emoji_assets table for emoji uploads

Revision ID: 004_create_emoji_assets
Revises: 003
Create Date: 2024-06-25 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "004_create_emoji_assets"
down_revision = "003"
branch_labels = None
depends_on = None


def _table_exists(connection, table_name: str) -> bool:
    insp = sa.inspect(connection)
    return table_name in insp.get_table_names()


def upgrade():
    """
    Historical migration to introduce emoji_assets.

    Note:
    - The initial migration (001) in this project already creates a richer emoji_assets table.
      Therefore, this migration is written idempotently to NO-OP if the table already exists.
    """
    bind = op.get_bind()
    if not _table_exists(bind, "emoji_assets"):
        # Minimal schema used by legacy upload endpoint; richer columns are added by other migrations
        op.create_table(
            "emoji_assets",
            sa.Column("emoji_id", sa.String(length=36), primary_key=True, nullable=False, index=True),
            sa.Column("emoji_type", sa.String(length=32), nullable=False),
            sa.Column("file_location", sa.String(length=256), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    # else: Table already exists from 001; do nothing.


def downgrade():
    bind = op.get_bind()
    if _table_exists(bind, "emoji_assets"):
        op.drop_table("emoji_assets")
    # else: Nothing to drop; maintain idempotency.
