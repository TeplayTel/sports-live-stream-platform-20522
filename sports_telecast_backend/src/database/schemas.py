"""
Database schema conversion utilities

This module provides functions to convert between Pydantic models and SQLAlchemy ORM models,
ensuring proper data transformation and relationship handling.
"""


from models.user import UserResponse, UserPreferences, UserRole
from models.match import (
    Match, Event, Team, Score, MatchEvent, Highlight,
    SportType, MatchStatus
)
from models.emoji import EmojiAsset, UserEmojiReaction, EmojiType
from .models import (
    UserDB, EventDB, MatchDB, TeamDB, MatchEventDB, HighlightDB,
    EmojiAssetDB, UserEmojiReactionDB,
    SportTypeEnum, MatchStatusEnum, UserRoleEnum, EmojiTypeEnum
)

# PUBLIC_INTERFACE
def convert_user_db_to_response(user_db: UserDB) -> UserResponse:
    """
    Convert UserDB SQLAlchemy model to UserResponse Pydantic model
    
    Args:
        user_db: SQLAlchemy user model
        
    Returns:
        UserResponse: Pydantic user response model
    """
    preferences = UserPreferences()
    if user_db.preferences:
        preferences = UserPreferences(**user_db.preferences)
    
    return UserResponse(
        user_id=user_db.user_id,
        email=user_db.email,
        username=user_db.username,
        full_name=user_db.full_name,
        avatar_url=user_db.avatar_url,
        role=UserRole(user_db.role.value),
        preferences=preferences,
        is_active=user_db.is_active,
        created_at=user_db.created_at,
        updated_at=user_db.updated_at
    )

# PUBLIC_INTERFACE
def convert_team_db_to_pydantic(team_db: TeamDB) -> Team:
    """
    Convert TeamDB SQLAlchemy model to Team Pydantic model
    
    Args:
        team_db: SQLAlchemy team model
        
    Returns:
        Team: Pydantic team model
    """
    return Team(
        team_id=team_db.team_id,
        name=team_db.name,
        short_name=team_db.short_name,
        logo_url=team_db.logo_url,
        colors=team_db.colors or {}
    )

# PUBLIC_INTERFACE
def convert_event_db_to_pydantic(event_db: EventDB, include_matches: bool = False) -> Event:
    """
    Convert EventDB SQLAlchemy model to Event Pydantic model
    
    Args:
        event_db: SQLAlchemy event model
        include_matches: Whether to include match data
        
    Returns:
        Event: Pydantic event model
    """
    matches = []
    if include_matches and event_db.matches:
        matches = [convert_match_db_to_pydantic(match) for match in event_db.matches]
    
    return Event(
        event_id=event_db.event_id,
        name=event_db.name,
        description=event_db.description,
        sport_type=SportType(event_db.sport_type.value),
        start_date=event_db.start_date,
        end_date=event_db.end_date,
        location=event_db.location,
        organizer=event_db.organizer,
        logo_url=event_db.logo_url,
        banner_url=event_db.banner_url,
        is_featured=event_db.is_featured,
        matches=matches,
        created_at=event_db.created_at,
        updated_at=event_db.updated_at
    )

# PUBLIC_INTERFACE
def convert_match_event_db_to_pydantic(match_event_db: MatchEventDB) -> MatchEvent:
    """
    Convert MatchEventDB SQLAlchemy model to MatchEvent Pydantic model
    
    Args:
        match_event_db: SQLAlchemy match event model
        
    Returns:
        MatchEvent: Pydantic match event model
    """
    return MatchEvent(
        event_id=match_event_db.event_id,
        match_id=match_event_db.match_id,
        event_type=match_event_db.event_type,
        minute=match_event_db.minute,
        team_id=match_event_db.team_id,
        player_name=match_event_db.player_name,
        description=match_event_db.description,
        created_at=match_event_db.created_at
    )

# PUBLIC_INTERFACE
def convert_match_db_to_pydantic(match_db: MatchDB) -> Match:
    """
    Convert MatchDB SQLAlchemy model to Match Pydantic model
    
    Args:
        match_db: SQLAlchemy match model
        
    Returns:
        Match: Pydantic match model
    """
    # Convert teams
    home_team = convert_team_db_to_pydantic(match_db.home_team)
    away_team = convert_team_db_to_pydantic(match_db.away_team)
    
    # Convert score
    period_scores = []
    if match_db.period_scores:
        if isinstance(match_db.period_scores, list):
            period_scores = match_db.period_scores
        elif isinstance(match_db.period_scores, dict):
            # Convert dict to list format if needed
            period_scores = [match_db.period_scores]
    
    score = Score(
        home_score=match_db.home_score,
        away_score=match_db.away_score,
        period_scores=period_scores
    )
    
    # Convert match events
    events = []
    if hasattr(match_db, 'match_events') and match_db.match_events:
        events = [convert_match_event_db_to_pydantic(event) for event in match_db.match_events]
    
    return Match(
        match_id=match_db.match_id,
        event_id=match_db.event_id,
        home_team=home_team,
        away_team=away_team,
        sport_type=SportType(match_db.sport_type.value),
        status=MatchStatus(match_db.status.value),
        score=score,
        start_time=match_db.start_time,
        end_time=match_db.end_time,
        venue=match_db.venue,
        competition=match_db.competition,
        round=match_db.round,
        stream_url=match_db.stream_url,
        events=events,
        statistics=match_db.statistics or {},
        created_at=match_db.created_at,
        updated_at=match_db.updated_at
    )

# PUBLIC_INTERFACE
def convert_highlight_db_to_pydantic(highlight_db: HighlightDB) -> Highlight:
    """
    Convert HighlightDB SQLAlchemy model to Highlight Pydantic model
    
    Args:
        highlight_db: SQLAlchemy highlight model
        
    Returns:
        Highlight: Pydantic highlight model
    """
    # Handle tags conversion - ensure it's a list of strings
    tags = []
    if highlight_db.tags:
        if isinstance(highlight_db.tags, list):
            tags = highlight_db.tags
        elif isinstance(highlight_db.tags, dict):
            # If it was stored as dict, extract values or keys as needed
            tags = list(highlight_db.tags.keys()) if highlight_db.tags else []
    
    return Highlight(
        highlight_id=highlight_db.highlight_id,
        match_id=highlight_db.match_id,
        title=highlight_db.title,
        description=highlight_db.description,
        video_url=highlight_db.video_url,
        thumbnail_url=highlight_db.thumbnail_url,
        duration=highlight_db.duration,
        tags=tags,
        view_count=highlight_db.view_count,
        created_at=highlight_db.created_at
    )

# PUBLIC_INTERFACE
def convert_emoji_db_to_pydantic(emoji_db: EmojiAssetDB) -> EmojiAsset:
    """
    Convert EmojiAssetDB SQLAlchemy model to EmojiAsset Pydantic model
    
    Args:
        emoji_db: SQLAlchemy emoji asset model
        
    Returns:
        EmojiAsset: Pydantic emoji asset model
    """
    return EmojiAsset(
        emoji_id=emoji_db.emoji_id,
        emoji_type=EmojiType(emoji_db.emoji_type.value),
        image_url=emoji_db.image_url,
        name=emoji_db.name,
        description=emoji_db.description,
        is_active=emoji_db.is_active,
        sort_order=emoji_db.sort_order,
        created_at=emoji_db.created_at
    )

# PUBLIC_INTERFACE
def convert_reaction_db_to_pydantic(reaction_db: UserEmojiReactionDB) -> UserEmojiReaction:
    """
    Convert UserEmojiReactionDB SQLAlchemy model to UserEmojiReaction Pydantic model
    
    Args:
        reaction_db: SQLAlchemy user emoji reaction model
        
    Returns:
        UserEmojiReaction: Pydantic user emoji reaction model
    """
    return UserEmojiReaction(
        user_id=reaction_db.user_id,
        event_id=reaction_db.event_id,
        emoji_id=reaction_db.emoji_id,
        created_at=reaction_db.created_at
    )

# PUBLIC_INTERFACE
def convert_enum_to_pydantic(enum_value, target_enum_class):
    """
    Convert SQLAlchemy enum to Pydantic enum
    
    Args:
        enum_value: SQLAlchemy enum value
        target_enum_class: Target Pydantic enum class
        
    Returns:
        Pydantic enum value
    """
    if enum_value is None:
        return None
    
    if hasattr(enum_value, 'value'):
        return target_enum_class(enum_value.value)
    else:
        return target_enum_class(enum_value)

# PUBLIC_INTERFACE
def convert_enum_to_sqlalchemy(enum_value, target_enum_class):
    """
    Convert Pydantic enum to SQLAlchemy enum
    
    Args:
        enum_value: Pydantic enum value
        target_enum_class: Target SQLAlchemy enum class
        
    Returns:
        SQLAlchemy enum value
    """
    if enum_value is None:
        return None
    
    if hasattr(enum_value, 'value'):
        return target_enum_class(enum_value.value)
    else:
        return target_enum_class(enum_value)

# Enum conversion mappings
ENUM_MAPPINGS = {
    # Pydantic to SQLAlchemy
    SportType: SportTypeEnum,
    MatchStatus: MatchStatusEnum,
    UserRole: UserRoleEnum,
    EmojiType: EmojiTypeEnum,
    
    # SQLAlchemy to Pydantic
    SportTypeEnum: SportType,
    MatchStatusEnum: MatchStatus,
    UserRoleEnum: UserRole,
    EmojiTypeEnum: EmojiType,
}

# PUBLIC_INTERFACE
def get_enum_mapping(source_enum_class):
    """
    Get the corresponding enum class for conversion
    
    Args:
        source_enum_class: Source enum class
        
    Returns:
        Target enum class for conversion
    """
    return ENUM_MAPPINGS.get(source_enum_class)
