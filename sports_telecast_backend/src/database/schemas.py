"""
Database schema conversion utilities

This module provides functions to convert between Pydantic models and SQLAlchemy ORM models,
ensuring proper data transformation and relationship handling.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel
import os
import os.path

from .models import (
    UserDB, EventDB, MatchDB, TeamDB, HighlightDB, EmojiAssetDB
)

# Base response models
class BaseResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class TeamResponse(BaseResponse):
    name: str
    short_name: str
    logo_url: Optional[str] = None
    colors: Dict[str, Any] = {}

class EventResponse(BaseResponse):
    name: str
    description: Optional[str] = None
    sport_type: str
    start_date: datetime
    end_date: datetime
    location: Optional[str] = None
    organizer: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_featured: bool = False
    matches: List[Dict[str, Any]] = []

class MatchResponse(BaseResponse):
    event_id: str
    home_team: TeamResponse
    away_team: TeamResponse
    sport_type: str
    status: str
    home_score: int
    away_score: int
    period_scores: Optional[List[Dict[str, Any]]] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    venue: Optional[str] = None
    competition: Optional[str] = None
    round: Optional[str] = None
    stream_url: Optional[str] = None
    statistics: Dict[str, Any] = {}

class HighlightResponse(BaseResponse):
    match_id: str
    title: str
    description: Optional[str] = None
    video_url: str
    thumbnail_url: Optional[str] = None
    duration: int
    tags: Optional[List[str]] = None
    view_count: int = 0

class ScheduleResponse(BaseResponse):
    date: datetime
    total_matches: int = 0
    schedule_metadata: Optional[Dict[str, Any]] = None
    matches: List[MatchResponse] = []

# Conversion functions
# PUBLIC_INTERFACE
def convert_user_db_to_response(user_db: UserDB) -> Dict[str, Any]:
    """Convert a UserDB ORM object to a serializable response dict.

    Behavior:
    - Normalizes role to a lowercase string ('user', 'admin', 'moderator') matching DB/OpenAPI.
    - Note: This normalization is for response payloads only; DB-level normalization is enforced in UserRepository.create_user.
    - Coerces preferences None -> {} to satisfy API schema.
    - Provides timestamp fallbacks if DB defaults aren't hydrated yet.

    Returns a dict compliant with UserResponse schema.
    """
    # Normalize role to lowercase string value (ORM now stores role as a string with a DB CHECK constraint)
    raw_role = getattr(user_db, "role", None)
    role_value = getattr(raw_role, "value", raw_role) if raw_role is not None else "user"
    if not isinstance(role_value, str):
        role_value = str(role_value)
    role_value = (role_value or "user").lower()
    if role_value not in {"user", "admin", "moderator"}:
        # Final guard against invalid values
        role_value = "user"

    # Ensure preferences is a dict for API response validation
    preferences_value = user_db.preferences or {}

    # Timestamps: provide safe fallbacks if not set yet
    from datetime import datetime as _dt  # local import to avoid polluting module namespace
    created_at_value = user_db.created_at or _dt.utcnow()
    updated_at_value = user_db.updated_at or created_at_value

    return {
        "user_id": str(user_db.user_id),
        "email": user_db.email,
        "username": user_db.username,
        "full_name": user_db.full_name,
        "avatar_url": user_db.avatar_url,
        "role": role_value,  # guaranteed lowercase: 'user'|'admin'|'moderator'
        "preferences": preferences_value,
        "is_active": user_db.is_active,
        "created_at": created_at_value,
        "updated_at": updated_at_value,
    }

def convert_team_db_to_response(team_db: TeamDB) -> TeamResponse:
    """Convert TeamDB to TeamResponse"""
    return TeamResponse(
        id=str(team_db.team_id),
        name=team_db.name,
        short_name=team_db.short_name,
        logo_url=team_db.logo_url,
        colors=team_db.colors or {},
        created_at=team_db.created_at,
        updated_at=team_db.updated_at
    )

def convert_event_db_to_response(event_db: EventDB, include_matches: bool = False) -> EventResponse:
    """Convert EventDB to EventResponse"""
    matches = []
    if include_matches and event_db.matches:
        matches = [convert_match_db_to_response(match).dict() for match in event_db.matches]
    
    return EventResponse(
        id=str(event_db.event_id),
        name=event_db.name,
        description=event_db.description,
        sport_type=event_db.sport_type.value,
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

def convert_match_db_to_response(match_db: MatchDB) -> MatchResponse:
    """Convert MatchDB to MatchResponse"""
    return MatchResponse(
        id=str(match_db.match_id),
        event_id=str(match_db.event_id),
        home_team=convert_team_db_to_response(match_db.home_team),
        away_team=convert_team_db_to_response(match_db.away_team),
        sport_type=match_db.sport_type.value,
        status=match_db.status.value,
        home_score=match_db.home_score,
        away_score=match_db.away_score,
        period_scores=match_db.period_scores,
        start_time=match_db.start_time,
        end_time=match_db.end_time,
        venue=match_db.venue,
        competition=match_db.competition,
        round=match_db.round,
        stream_url=match_db.stream_url,
        statistics=match_db.statistics or {},
        created_at=match_db.created_at,
        updated_at=match_db.updated_at
    )

def convert_highlight_db_to_response(highlight_db: HighlightDB) -> HighlightResponse:
    """Convert HighlightDB to HighlightResponse"""
    return HighlightResponse(
        id=str(highlight_db.highlight_id),
        match_id=str(highlight_db.match_id),
        title=highlight_db.title,
        description=highlight_db.description,
        video_url=highlight_db.video_url,
        thumbnail_url=highlight_db.thumbnail_url,
        duration=highlight_db.duration,
        tags=highlight_db.tags,
        view_count=highlight_db.view_count,
        created_at=highlight_db.created_at,
        updated_at=highlight_db.updated_at
    )

def convert_schedule_db_to_response(schedule_db: MatchDB) -> ScheduleResponse:
    """Convert ScheduleDB to ScheduleResponse"""
    matches = [convert_match_db_to_response(match) for match in schedule_db.matches]
    
    return ScheduleResponse(
        id=str(schedule_db.schedule_id),
        date=schedule_db.date,
        total_matches=schedule_db.total_matches,
        schedule_metadata=schedule_db.schedule_metadata,
        matches=matches,
        created_at=schedule_db.created_at,
        updated_at=schedule_db.updated_at
    )

def _get_cdn_base_url() -> str:
    """
    Returns the base CDN URL for constructing emoji image URLs.
    Reads EMOJI_CDN_BASE_URL from environment, falling back to a placeholder CDN path.
    """
    base = os.getenv("EMOJI_CDN_BASE_URL", "https://cdn.placeholderdomain.com/emojis/")
    return base.rstrip("/") + "/"

def _coalesce_image_url(record: Any) -> Optional[str]:
    """
    Compute or retrieve image_url from a record that may or may not have the 'image_url' column.
    If image_url is missing or empty, try to derive it from 'file_location' if present.
    """
    # Try direct attribute or dict access
    img = getattr(record, "image_url", None)
    if img is None and isinstance(record, dict):
        img = record.get("image_url")

    # Normalize empty string to None
    if isinstance(img, str) and img.strip() == "":
        img = None

    if img:
        return img

    # Fallback: build from file_location (basename)
    file_location = getattr(record, "file_location", None)
    if file_location is None and isinstance(record, dict):
        file_location = record.get("file_location")

    if isinstance(file_location, str) and file_location.strip():
        filename = os.path.basename(file_location.strip())
        if filename:
            return _get_cdn_base_url() + filename

    return None

def _get_attr_or_default(record: Any, name: str, default: Any = None) -> Any:
    """
    Helper to read an attribute from either ORM object or dict-like with default.
    """
    if hasattr(record, name):
        return getattr(record, name)
    if isinstance(record, dict) and name in record:
        return record[name]
    return default

def _normalize_emoji_type(value: Any) -> str:
    """
    Accepts an Enum or string and returns the underlying string value.
    """
    if value is None:
        return "clap"
    return getattr(value, "value", value)

def convert_emoji_db_to_pydantic(emoji_db: Union[EmojiAssetDB, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert EmojiAssetDB (or a dict-like fallback row) to a response dict compatible with Pydantic model.
    Provides robust fallbacks if columns are missing (older/minimal schema).

    Fields:
    - image_url: if missing, derive from 'file_location' using EMOJI_CDN_BASE_URL + basename(file)
    - name: default from emoji_type title-case if missing
    - is_active: defaults to True if missing
    - sort_order: defaults to 0 if missing
    - created_at: defaults to now if missing
    """
    emoji_id = _get_attr_or_default(emoji_db, "emoji_id")
    emoji_type_raw = _get_attr_or_default(emoji_db, "emoji_type", "clap")
    emoji_type = _normalize_emoji_type(emoji_type_raw)
    image_url = _coalesce_image_url(emoji_db)

    # Sensible defaults for older schema
    name = _get_attr_or_default(emoji_db, "name", str(emoji_type).replace("_", " ").title())
    description = _get_attr_or_default(emoji_db, "description", None)
    is_active = _get_attr_or_default(emoji_db, "is_active", True)
    sort_order = _get_attr_or_default(emoji_db, "sort_order", 0)
    created_at = _get_attr_or_default(emoji_db, "created_at", datetime.utcnow())

    return {
        "emoji_id": str(emoji_id),
        "emoji_type": emoji_type,
        "image_url": image_url or _get_cdn_base_url() + f"{emoji_id}.png",
        "name": name,
        "description": description,
        "is_active": is_active,
        "sort_order": sort_order,
        "created_at": created_at
    }
