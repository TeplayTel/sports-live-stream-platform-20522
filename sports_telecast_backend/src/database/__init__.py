"""
Database package initialization
"""

from .connection import Base, get_db, init_database, close_database_connections, check_database_connection, get_database_health
from .models import (
    UserDB,
    TeamDB,
    EventDB,
    MatchDB,
    EmojiAssetDB,
    UserEmojiReactionDB,
    HighlightDB,
    UserProfileDB,
    ScheduleDB,
    ScheduleMatchDB,
)
from .schemas import (
    BaseResponse,
    TeamResponse,
    EventResponse,
    MatchResponse,
    ScheduleResponse,
    convert_user_db_to_response,
    convert_team_db_to_response,
    convert_event_db_to_response,
    convert_match_db_to_response,
    convert_schedule_db_to_response
)

__all__ = [
    'Base',
    'get_db',
    'init_database',
    'close_database_connections',
    'check_database_connection',
    'get_database_health',
    # Models
    'UserDB',
    'TeamDB',
    'EventDB',
    'MatchDB',
    'EmojiAssetDB',
    'UserEmojiReactionDB',
    'HighlightDB',
    'UserProfileDB',
    'ScheduleDB',
    'ScheduleMatchDB',
    # Response models
    'BaseResponse',
    'TeamResponse',
    'EventResponse',
    'MatchResponse',
    'ScheduleResponse',
    # Conversion functions
    'convert_user_db_to_response',
    'convert_team_db_to_response',
    'convert_event_db_to_response',
    'convert_match_db_to_response',
    'convert_schedule_db_to_response'
]
