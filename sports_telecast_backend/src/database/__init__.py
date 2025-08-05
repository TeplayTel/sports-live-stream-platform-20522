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
    "EmojiTypeEnum"
]
