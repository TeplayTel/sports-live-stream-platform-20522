"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (idempotently, to avoid race conditions and re-run failures)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sporttypeenum') THEN
            CREATE TYPE sporttypeenum AS ENUM ('football', 'basketball', 'tennis', 'cricket', 'rugby', 'hockey', 'baseball');
        END IF;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'matchstatusenum') THEN
            CREATE TYPE matchstatusenum AS ENUM ('scheduled', 'live', 'finished', 'cancelled', 'postponed');
        END IF;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userroleenum') THEN
            CREATE TYPE userroleenum AS ENUM ('user', 'admin', 'moderator');
        END IF;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'emojitypeenum') THEN
            CREATE TYPE emojitypeenum AS ENUM ('clap', 'fire', 'heart', 'thumbs_up', 'celebration', 'shocked', 'angry', 'sad', 'laugh', 'goal');
        END IF;
    END$$;
    """)
    
    # Create users table
    op.create_table('users',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=True),
    sa.Column('avatar_url', sa.Text(), nullable=True),
    sa.Column('role', postgresql.ENUM('user', 'admin', 'moderator', name='userroleenum'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('preferences', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # Create teams table
    op.create_table('teams',
    sa.Column('team_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('short_name', sa.String(length=10), nullable=False),
    sa.Column('logo_url', sa.Text(), nullable=True),
    sa.Column('colors', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('team_id')
    )
    
    # Create events table
    op.create_table('events',
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('sport_type', postgresql.ENUM('football', 'basketball', 'tennis', 'cricket', 'rugby', 'hockey', 'baseball', name='sporttypeenum'), nullable=False),
    sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('organizer', sa.String(length=255), nullable=True),
    sa.Column('logo_url', sa.Text(), nullable=True),
    sa.Column('banner_url', sa.Text(), nullable=True),
    sa.Column('is_featured', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('event_id')
    )
    
    # Create emoji_assets table
    op.create_table('emoji_assets',
    sa.Column('emoji_id', sa.String(length=36), nullable=False),
    sa.Column('emoji_type', postgresql.ENUM('clap', 'fire', 'heart', 'thumbs_up', 'celebration', 'shocked', 'angry', 'sad', 'laugh', 'goal', name='emojitypeenum'), nullable=False),
    sa.Column('image_url', sa.Text(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('emoji_id')
    )
    
    # Create matches table
    op.create_table('matches',
    sa.Column('match_id', sa.String(length=36), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('home_team_id', sa.String(length=36), nullable=False),
    sa.Column('away_team_id', sa.String(length=36), nullable=False),
    sa.Column('sport_type', postgresql.ENUM('football', 'basketball', 'tennis', 'cricket', 'rugby', 'hockey', 'baseball', name='sporttypeenum'), nullable=False),
    sa.Column('status', postgresql.ENUM('scheduled', 'live', 'finished', 'cancelled', 'postponed', name='matchstatusenum'), nullable=False),
    sa.Column('home_score', sa.Integer(), nullable=False),
    sa.Column('away_score', sa.Integer(), nullable=False),
    sa.Column('period_scores', sa.JSON(), nullable=True),
    sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('venue', sa.String(length=255), nullable=True),
    sa.Column('competition', sa.String(length=255), nullable=True),
    sa.Column('round', sa.String(length=100), nullable=True),
    sa.Column('stream_url', sa.Text(), nullable=True),
    sa.Column('statistics', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['away_team_id'], ['teams.team_id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ),
    sa.ForeignKeyConstraint(['home_team_id'], ['teams.team_id'], ),
    sa.PrimaryKeyConstraint('match_id')
    )
    
    # Create user_emoji_reactions table
    op.create_table('user_emoji_reactions',
    sa.Column('reaction_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('emoji_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['emoji_id'], ['emoji_assets.emoji_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
    sa.PrimaryKeyConstraint('reaction_id')
    )
    
    # Create highlights table
    op.create_table('highlights',
    sa.Column('highlight_id', sa.String(length=36), nullable=False),
    sa.Column('match_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('video_url', sa.Text(), nullable=False),
    sa.Column('thumbnail_url', sa.Text(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=False),
    sa.Column('tags', sa.JSON(), nullable=True),
    sa.Column('view_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['match_id'], ['matches.match_id'], ),
    sa.PrimaryKeyConstraint('highlight_id')
    )
    
    # Create match_events table
    op.create_table('match_events',
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('match_id', sa.String(length=36), nullable=False),
    sa.Column('event_type', sa.String(length=50), nullable=False),
    sa.Column('minute', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.String(length=36), nullable=False),
    sa.Column('player_name', sa.String(length=255), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['match_id'], ['matches.match_id'], ),
    sa.PrimaryKeyConstraint('event_id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('match_events')
    op.drop_table('highlights')
    op.drop_table('user_emoji_reactions')
    op.drop_table('matches')
    op.drop_table('emoji_assets')
    op.drop_table('events')
    op.drop_table('teams')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Drop enum types (safe if they exist)
    op.execute("DROP TYPE IF EXISTS emojitypeenum")
    op.execute("DROP TYPE IF EXISTS userroleenum")
    op.execute("DROP TYPE IF EXISTS matchstatusenum")
    op.execute("DROP TYPE IF EXISTS sporttypeenum")
