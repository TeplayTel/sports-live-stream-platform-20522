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


def _diag(msg: str) -> None:
    """
    Diagnostic print helper to clearly annotate migration progress.
    """
    print(f"[001_initial] {msg}")


def _lock_snapshot(bind, note: str = "") -> None:
    """
    Print a brief snapshot of current lock waiters and blockers, plus active Alembic session queries.
    Safe best-effort; exceptions are ignored to avoid failing the migration.
    """
    try:
        _diag(f"Lock snapshot start {f'({note})' if note else ''} ...")
        # Waiters and blockers
        waiters = bind.exec_driver_sql(
            """
            SELECT w.pid AS waiting_pid,
                   w.locktype,
                   w.mode AS waiting_mode,
                   w.relation,
                   w.classid, w.objid,
                   a_wait.application_name AS waiting_app,
                   a_wait.state AS waiting_state,
                   a_wait.wait_event_type, a_wait.wait_event,
                   b.pid AS blocking_pid,
                   a_block.application_name AS blocking_app,
                   a_block.state AS blocking_state
            FROM pg_locks w
            JOIN pg_stat_activity a_wait ON a_wait.pid = w.pid
            JOIN pg_locks b
              ON b.locktype = w.locktype
             AND b.database IS NOT DISTINCT FROM w.database
             AND b.relation IS NOT DISTINCT FROM w.relation
             AND b.page IS NOT DISTINCT FROM w.page
             AND b.tuple IS NOT DISTINCT FROM w.tuple
             AND b.classid IS NOT DISTINCT FROM w.classid
             AND b.objid IS NOT DISTINCT FROM w.objid
             AND b.objsubid IS NOT DISTINCT FROM w.objsubid
             AND b.pid <> w.pid
            JOIN pg_stat_activity a_block ON a_block.pid = b.pid
            WHERE NOT w.granted AND b.granted
            ORDER BY w.pid
            """
        ).mappings().all()
        _diag(f"Lock waiters count: {len(waiters)}")
        for row in waiters[:10]:
            _diag(
                f"  waiter pid={row['waiting_pid']} app={row['waiting_app']} "
                f"mode={row['waiting_mode']} locktype={row['locktype']} "
                f"blocked_by pid={row['blocking_pid']} app={row['blocking_app']} "
                f"wait={row['wait_event_type']}/{row['wait_event']}"
            )

        # Active Alembic-related sessions
        alembic_sessions = bind.exec_driver_sql(
            """
            SELECT pid, application_name, state, wait_event_type, wait_event, query
            FROM pg_stat_activity
            WHERE application_name LIKE 'sports_telecast_alembic%'
            ORDER BY pid
            """
        ).mappings().all()
        _diag(f"Alembic sessions observed: {len(alembic_sessions)}")
        for s in alembic_sessions[:10]:
            q = s.get("query") or ""
            q_trim = " ".join(q.split())[:200]
            _diag(
                f"  pid={s['pid']} state={s['state']} wait={s['wait_event_type']}/{s['wait_event']} query=\"{q_trim}\""
            )
        _diag("Lock snapshot end.")
    except Exception as _e:
        # Do not fail the migration if snapshot fails
        _diag(f"Lock snapshot error ignored: {_e}")


def upgrade() -> None:
    bind = op.get_bind()
    _diag("BEGIN upgrade -> 001, Initial database schema")

    # Create enum types (idempotently, to avoid race conditions and re-run failures)
    _diag("Creating enum type: sporttypeenum")
    _lock_snapshot(bind, "before sporttypeenum")
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sporttypeenum') THEN
            CREATE TYPE sporttypeenum AS ENUM ('football', 'basketball', 'tennis', 'cricket', 'rugby', 'hockey', 'baseball');
        END IF;
    END$$;
    """)
    _diag("Created enum type: sporttypeenum")

    _diag("Creating enum type: matchstatusenum")
    _lock_snapshot(bind, "before matchstatusenum")
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'matchstatusenum') THEN
            CREATE TYPE matchstatusenum AS ENUM ('scheduled', 'live', 'finished', 'cancelled', 'postponed');
        END IF;
    END$$;
    """)
    _diag("Created enum type: matchstatusenum")

    _diag("Creating enum type: userroleenum")
    _lock_snapshot(bind, "before userroleenum")
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userroleenum') THEN
            CREATE TYPE userroleenum AS ENUM ('user', 'admin', 'moderator');
        END IF;
    END$$;
    """)
    _diag("Created enum type: userroleenum")

    _diag("Creating enum type: emojitypeenum")
    _lock_snapshot(bind, "before emojitypeenum")
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'emojitypeenum') THEN
            CREATE TYPE emojitypeenum AS ENUM ('clap', 'fire', 'heart', 'thumbs_up', 'celebration', 'shocked', 'angry', 'sad', 'laugh', 'goal');
        END IF;
    END$$;
    """)
    _diag("Created enum type: emojitypeenum")

    # Create users table
    _diag("Creating table: users")
    _lock_snapshot(bind, "before users")
    op.create_table('users',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('role', postgresql.ENUM('user', 'admin', 'moderator', name='userroleenum', create_type=False), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )
    _diag("Created table: users")

    _diag("Creating index: ix_users_email")
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    _diag("Created index: ix_users_email")

    _diag("Creating index: ix_users_username")
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    _diag("Created index: ix_users_username")

    # Create teams table
    _diag("Creating table: teams")
    _lock_snapshot(bind, "before teams")
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
    _diag("Created table: teams")

    # Create events table
    _diag("Creating table: events")
    _lock_snapshot(bind, "before events")
    op.create_table('events',
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sport_type', postgresql.ENUM('football', 'basketball', 'tennis', 'cricket', 'rugby', 'hockey', 'baseball', name='sporttypeenum', create_type=False), nullable=False),
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
    _diag("Created table: events")

    # Create emoji_assets table
    _diag("Creating table: emoji_assets")
    _lock_snapshot(bind, "before emoji_assets")
    op.create_table('emoji_assets',
        sa.Column('emoji_id', sa.String(length=36), nullable=False),
        sa.Column('emoji_type', postgresql.ENUM('clap', 'fire', 'heart', 'thumbs_up', 'celebration', 'shocked', 'angry', 'sad', 'laugh', 'goal', name='emojitypeenum', create_type=False), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('emoji_id')
    )
    _diag("Created table: emoji_assets")

    # Create matches table
    _diag("Creating table: matches")
    _lock_snapshot(bind, "before matches")
    op.create_table('matches',
        sa.Column('match_id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('home_team_id', sa.String(length=36), nullable=False),
        sa.Column('away_team_id', sa.String(length=36), nullable=False),
        sa.Column('sport_type', postgresql.ENUM('football', 'basketball', 'tennis', 'cricket', 'rugby', 'hockey', 'baseball', name='sporttypeenum'), nullable=False),
        sa.Column('status', postgresql.ENUM('scheduled', 'live', 'finished', 'cancelled', 'postponed', name='matchstatusenum', create_type=False), nullable=False),
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
    _diag("Created table: matches")

    # Create user_emoji_reactions table
    _diag("Creating table: user_emoji_reactions")
    _lock_snapshot(bind, "before user_emoji_reactions")
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
    _diag("Created table: user_emoji_reactions")

    # Create highlights table
    _diag("Creating table: highlights")
    _lock_snapshot(bind, "before highlights")
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
    _diag("Created table: highlights")

    # Create match_events table
    _diag("Creating table: match_events")
    _lock_snapshot(bind, "before match_events")
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
    _diag("Created table: match_events")

    _diag("END upgrade -> 001")


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
