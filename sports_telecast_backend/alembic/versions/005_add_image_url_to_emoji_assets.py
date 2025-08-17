"""Add image_url column to emoji_assets and backfill from file_location if possible.

Revision ID: 005_add_image_url_to_emoji_assets
Revises: 004_create_emoji_assets
Create Date: 2025-08-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
import os

# revision identifiers, used by Alembic.
revision = "005_add_image_url_to_emoji_assets"
down_revision = "004_create_emoji_assets"
branch_labels = None
depends_on = None

def _column_exists(connection, table_name: str, column_name: str) -> bool:
    insp = sa.inspect(connection)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols

def upgrade():
    bind = op.get_bind()
    if not _column_exists(bind, "emoji_assets", "image_url"):
        op.add_column("emoji_assets", sa.Column("image_url", sa.Text(), nullable=True))
        # Best-effort backfill using EMOJI_CDN_BASE_URL + basename(file_location)
        cdn_base = os.getenv("EMOJI_CDN_BASE_URL", "https://cdn.placeholderdomain.com/emojis/").rstrip("/") + "/"
        try:
            # Use regex to extract basename in SQL; fallback to file_location if regex not available
            bind.exec_driver_sql(
                """
                UPDATE emoji_assets
                SET image_url = CASE
                    WHEN file_location IS NOT NULL AND file_location <> ''
                    THEN %s || regexp_replace(file_location, '^.*/', '')
                    ELSE image_url
                END
                WHERE image_url IS NULL
                """,
                (cdn_base,),
            )
        except Exception:
            # Fallback simple update without regex (may include full path)
            try:
                bind.exec_driver_sql(
                    """
                    UPDATE emoji_assets
                    SET image_url = COALESCE(image_url, %s || file_location)
                    WHERE image_url IS NULL AND file_location IS NOT NULL
                    """,
                    (cdn_base,),
                )
            except Exception:
                # Ignore backfill failure to avoid blocking migration
                pass

def downgrade():
    bind = op.get_bind()
    if _column_exists(bind, "emoji_assets", "image_url"):
        op.drop_column("emoji_assets", "image_url")
