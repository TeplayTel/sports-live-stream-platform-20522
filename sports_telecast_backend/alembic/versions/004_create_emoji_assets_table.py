"""create emoji_assets table for emoji uploads

Revision ID: 004_create_emoji_assets
Revises: 003_convert_string_uuids_to_native
Create Date: 2024-06-25 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_create_emoji_assets'
down_revision = '003_convert_string_uuids_to_native'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'emoji_assets',
        sa.Column('emoji_id', sa.String(length=36), primary_key=True, nullable=False, index=True),
        sa.Column('emoji_type', sa.String(length=32), nullable=False),
        sa.Column('file_location', sa.String(length=256), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('emoji_assets')
