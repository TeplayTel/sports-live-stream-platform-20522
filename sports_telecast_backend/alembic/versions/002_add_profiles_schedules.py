"""Add user profiles and schedules tables

Revision ID: 002
Revises: 001
Create Date: 2024-08-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ProfileVisibilityEnum (idempotent)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'profilevisibilityenum') THEN
            CREATE TYPE profilevisibilityenum AS ENUM ('public', 'friends', 'private');
        END IF;
    END$$;
    """)
    
    # Create user_profiles table
    op.create_table('user_profiles',
    sa.Column('profile_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=True),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('website', sa.Text(), nullable=True),
    sa.Column('avatar_url', sa.Text(), nullable=True),
    sa.Column('cover_image_url', sa.Text(), nullable=True),
    sa.Column('favorite_teams', sa.JSON(), nullable=True),
    sa.Column('favorite_sports', sa.JSON(), nullable=True),
    sa.Column('favorite_players', sa.JSON(), nullable=True),
    sa.Column('favorite_leagues', sa.JSON(), nullable=True),
    sa.Column('notification_preferences', sa.JSON(), nullable=True),
    sa.Column('profile_visibility', postgresql.ENUM('public', 'friends', 'private', name='profilevisibilityenum', create_type=False), nullable=False),
    sa.Column('show_favorite_teams', sa.Boolean(), nullable=False),
    sa.Column('show_activity', sa.Boolean(), nullable=False),
    sa.Column('allow_friend_requests', sa.Boolean(), nullable=False),
    sa.Column('total_reactions', sa.Integer(), nullable=False),
    sa.Column('matches_watched', sa.Integer(), nullable=False),
    sa.Column('highlights_watched', sa.Integer(), nullable=False),
    sa.Column('preferred_language', sa.String(length=10), nullable=False),
    sa.Column('timezone', sa.String(length=50), nullable=False),
    sa.Column('date_format', sa.String(length=20), nullable=False),
    sa.Column('time_format', sa.String(length=10), nullable=False),
    sa.Column('is_verified', sa.Boolean(), nullable=False),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
    sa.PrimaryKeyConstraint('profile_id'),
    sa.UniqueConstraint('user_id')
    )
    
    # Create schedules table
    op.create_table('schedules',
    sa.Column('schedule_id', sa.String(length=36), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('total_matches', sa.Integer(), nullable=False),
    sa.Column('schedule_metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('schedule_id')
    )
    op.create_index(op.f('ix_schedules_date'), 'schedules', ['date'], unique=False)
    
    # Create schedule_matches association table
    op.create_table('schedule_matches',
    sa.Column('schedule_id', sa.String(length=36), nullable=False),
    sa.Column('match_id', sa.String(length=36), nullable=False),
    sa.Column('is_featured', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['match_id'], ['matches.match_id'], ),
    sa.ForeignKeyConstraint(['schedule_id'], ['schedules.schedule_id'], ),
    sa.PrimaryKeyConstraint('schedule_id', 'match_id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('schedule_matches')
    op.drop_index(op.f('ix_schedules_date'), table_name='schedules')
    op.drop_table('schedules')
    op.drop_table('user_profiles')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS profilevisibilityenum")
