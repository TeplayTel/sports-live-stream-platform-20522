"""
Database schema conversion utilities

This module provides functions to convert between Pydantic models and SQLAlchemy ORM models,
ensuring proper data transformation and relationship handling.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

from .models import (
    UserDB, EventDB, MatchDB, TeamDB
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

class ScheduleResponse(BaseResponse):
    date: datetime
    total_matches: int = 0
    schedule_metadata: Optional[Dict[str, Any]] = None
    matches: List[MatchResponse] = []

# Conversion functions
def convert_user_db_to_response(user_db: UserDB) -> Dict[str, Any]:
    """Convert UserDB to response dict"""
    return {
        "user_id": str(user_db.user_id),
        "email": user_db.email,
        "username": user_db.username,
        "full_name": user_db.full_name,
        "avatar_url": user_db.avatar_url,
        "role": user_db.role.value,
        "preferences": user_db.preferences,
        "is_active": user_db.is_active,
        "created_at": user_db.created_at,
        "updated_at": user_db.updated_at
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
