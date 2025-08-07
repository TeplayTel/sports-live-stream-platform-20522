"""Convert String UUIDs to native PostgreSQL UUIDs

Revision ID: 003
Revises: 002
Create Date: 2024-08-07 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Helper function to convert String UUID to native UUID
    def convert_column_to_uuid(table_name: str, column_name: str) -> None:
        # Create a temporary column with UUID type
        op.add_column(table_name, sa.Column(f'{column_name}_new', postgresql.UUID(as_uuid=True), nullable=True))
        
        # Copy data with type conversion
        op.execute(f'UPDATE {table_name} SET {column_name}_new = {column_name}::uuid')
        
        # Drop old column and rename new column
        op.drop_column(table_name, column_name)
        op.alter_column(table_name, f'{column_name}_new', new_column_name=column_name, nullable=False)

    # Convert primary and foreign key columns to UUID type
    
    # Users table
    convert_column_to_uuid('users', 'user_id')
    
    # Teams table
    convert_column_to_uuid('teams', 'team_id')
    
    # Events table
    convert_column_to_uuid('events', 'event_id')
    
    # Matches table
    convert_column_to_uuid('matches', 'match_id')
    convert_column_to_uuid('matches', 'event_id')
    convert_column_to_uuid('matches', 'home_team_id')
    convert_column_to_uuid('matches', 'away_team_id')
    
    # Match events table
    convert_column_to_uuid('match_events', 'event_id')
    convert_column_to_uuid('match_events', 'match_id')
    convert_column_to_uuid('match_events', 'team_id')
    
    # Emoji assets table
    convert_column_to_uuid('emoji_assets', 'emoji_id')
    
    # User emoji reactions table
    convert_column_to_uuid('user_emoji_reactions', 'reaction_id')
    convert_column_to_uuid('user_emoji_reactions', 'user_id')
    convert_column_to_uuid('user_emoji_reactions', 'event_id')
    convert_column_to_uuid('user_emoji_reactions', 'emoji_id')
    
    # Highlights table
    convert_column_to_uuid('highlights', 'highlight_id')
    convert_column_to_uuid('highlights', 'match_id')
    
    # User profiles table
    convert_column_to_uuid('user_profiles', 'profile_id')
    convert_column_to_uuid('user_profiles', 'user_id')
    
    # Schedules table
    convert_column_to_uuid('schedules', 'schedule_id')
    
    # Schedule matches table
    convert_column_to_uuid('schedule_matches', 'schedule_id')
    convert_column_to_uuid('schedule_matches', 'match_id')

def downgrade() -> None:
    # Helper function to convert UUID back to String
    def convert_column_to_string(table_name: str, column_name: str) -> None:
        # Create a temporary column with String type
        op.add_column(table_name, sa.Column(f'{column_name}_new', sa.String(36), nullable=True))
        
        # Copy data with type conversion
        op.execute(f'UPDATE {table_name} SET {column_name}_new = {column_name}::text')
        
        # Drop old column and rename new column
        op.drop_column(table_name, column_name)
        op.alter_column(table_name, f'{column_name}_new', new_column_name=column_name, nullable=False)

    # Convert back all UUID columns to String type
    convert_column_to_string('schedule_matches', 'match_id')
    convert_column_to_string('schedule_matches', 'schedule_id')
    convert_column_to_string('schedules', 'schedule_id')
    convert_column_to_string('user_profiles', 'user_id')
    convert_column_to_string('user_profiles', 'profile_id')
    convert_column_to_string('highlights', 'match_id')
    convert_column_to_string('highlights', 'highlight_id')
    convert_column_to_string('user_emoji_reactions', 'emoji_id')
    convert_column_to_string('user_emoji_reactions', 'event_id')
    convert_column_to_string('user_emoji_reactions', 'user_id')
    convert_column_to_string('user_emoji_reactions', 'reaction_id')
    convert_column_to_string('emoji_assets', 'emoji_id')
    convert_column_to_string('match_events', 'team_id')
    convert_column_to_string('match_events', 'match_id')
    convert_column_to_string('match_events', 'event_id')
    convert_column_to_string('matches', 'away_team_id')
    convert_column_to_string('matches', 'home_team_id')
    convert_column_to_string('matches', 'event_id')
    convert_column_to_string('matches', 'match_id')
    convert_column_to_string('events', 'event_id')
    convert_column_to_string('teams', 'team_id')
    convert_column_to_string('users', 'user_id')
