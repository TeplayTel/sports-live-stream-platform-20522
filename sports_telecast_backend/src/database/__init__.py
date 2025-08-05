"""
Database package for Sports Telecast Backend

This package provides:
- Database connection management with SQLAlchemy and asyncpg
- Database models for all application entities
- Database session management for FastAPI dependency injection
"""

from .connection import (
    get_db,
    get_database_session,
    get_db_session,
    init_database,
    check_database_connection,
    close_database_connections,
    get_database_health,
    Base,
    engine,
    AsyncSessionLocal
)

from .models import (
    UserDB,
    TeamDB,
    EventDB,
    MatchDB,
    MatchEventDB,
    EmojiAssetDB,
    UserEmojiReactionDB,
    HighlightDB,
    SportTypeEnum,
    MatchStatusEnum,
    UserRoleEnum,
    EmojiTypeEnum
)

from .schemas import (
    convert_user_db_to_response,
    convert_team_db_to_pydantic,
    convert_event_db_to_pydantic,
    convert_match_db_to_pydantic,
    convert_match_event_db_to_pydantic,
    convert_highlight_db_to_pydantic,
    convert_emoji_db_to_pydantic,
    convert_reaction_db_to_pydantic,
    convert_enum_to_pydantic,
    convert_enum_to_sqlalchemy,
    get_enum_mapping,
    ENUM_MAPPINGS
)

__all__ = [
    # Connection components
    "get_db",
    "get_database_session", 
    "get_db_session",
    "init_database",
    "check_database_connection",
    "close_database_connections",
    "get_database_health",
    "Base",
    "engine",
    "AsyncSessionLocal",
    
    # Database models
    "UserDB",
    "TeamDB", 
    "EventDB",
    "MatchDB",
    "MatchEventDB",
    "EmojiAssetDB",
    "UserEmojiReactionDB",
    "HighlightDB",
    
    # Enums
    "SportTypeEnum",
    "MatchStatusEnum", 
    "UserRoleEnum",
    "EmojiTypeEnum",
    
    # Schema conversion utilities
    "convert_user_db_to_response",
    "convert_team_db_to_pydantic",
    "convert_event_db_to_pydantic",
    "convert_match_db_to_pydantic",
    "convert_match_event_db_to_pydantic",
    "convert_highlight_db_to_pydantic",
    "convert_emoji_db_to_pydantic",
    "convert_reaction_db_to_pydantic",
    "convert_enum_to_pydantic",
    "convert_enum_to_sqlalchemy",
    "get_enum_mapping",
    "ENUM_MAPPINGS"
]
