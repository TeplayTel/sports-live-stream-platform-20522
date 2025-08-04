from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MatchStatus(str, Enum):
    """Match status enumeration"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"

class SportType(str, Enum):
    """Sport type enumeration"""
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    CRICKET = "cricket"
    RUGBY = "rugby"
    HOCKEY = "hockey"
    BASEBALL = "baseball"

class Team(BaseModel):
    """Team model"""
    team_id: str = Field(..., description="Unique team identifier")
    name: str = Field(..., description="Team name")
    short_name: str = Field(..., description="Team short name or abbreviation")
    logo_url: Optional[HttpUrl] = Field(None, description="URL to team logo")
    colors: Dict[str, str] = Field(
        default_factory=dict,
        description="Team colors (primary, secondary, etc.)"
    )

class Score(BaseModel):
    """Score model"""
    home_score: int = Field(default=0, description="Home team score")
    away_score: int = Field(default=0, description="Away team score")
    period_scores: List[Dict[str, int]] = Field(
        default_factory=list,
        description="Period-wise scores"
    )

class MatchEvent(BaseModel):
    """Match event model (goals, cards, substitutions, etc.)"""
    event_id: str = Field(..., description="Unique event identifier")
    match_id: str = Field(..., description="Match identifier")
    event_type: str = Field(..., description="Type of event (goal, card, substitution, etc.)")
    minute: int = Field(..., description="Minute when event occurred")
    team_id: str = Field(..., description="Team involved in the event")
    player_name: Optional[str] = Field(None, description="Player involved")
    description: str = Field(..., description="Event description")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Match(BaseModel):
    """Match model"""
    match_id: str = Field(..., description="Unique match identifier")
    event_id: str = Field(..., description="Event identifier this match belongs to")
    home_team: Team = Field(..., description="Home team")
    away_team: Team = Field(..., description="Away team")
    sport_type: SportType = Field(..., description="Type of sport")
    status: MatchStatus = Field(..., description="Match status")
    score: Score = Field(default_factory=Score, description="Current score")
    start_time: datetime = Field(..., description="Match start time")
    end_time: Optional[datetime] = Field(None, description="Match end time")
    venue: Optional[str] = Field(None, description="Match venue")
    competition: Optional[str] = Field(None, description="Competition/league name")
    round: Optional[str] = Field(None, description="Round or matchday")
    stream_url: Optional[HttpUrl] = Field(None, description="Live stream URL")
    events: List[MatchEvent] = Field(default_factory=list, description="Match events")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Match statistics")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Event(BaseModel):
    """Sports event model (tournament, league, etc.)"""
    event_id: str = Field(..., description="Unique event identifier")
    name: str = Field(..., description="Event name")
    description: Optional[str] = Field(None, description="Event description")
    sport_type: SportType = Field(..., description="Type of sport")
    start_date: datetime = Field(..., description="Event start date")
    end_date: datetime = Field(..., description="Event end date")
    location: Optional[str] = Field(None, description="Event location")
    organizer: Optional[str] = Field(None, description="Event organizer")
    logo_url: Optional[HttpUrl] = Field(None, description="Event logo URL")
    banner_url: Optional[HttpUrl] = Field(None, description="Event banner URL")
    is_featured: bool = Field(default=False, description="Whether event is featured")
    matches: List[Match] = Field(default_factory=list, description="Matches in this event")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Schedule(BaseModel):
    """Schedule model for upcoming matches"""
    schedule_id: str = Field(..., description="Unique schedule identifier")
    date: datetime = Field(..., description="Schedule date")
    matches: List[Match] = Field(default_factory=list, description="Matches scheduled for this date")

class Highlight(BaseModel):
    """Match highlight model"""
    highlight_id: str = Field(..., description="Unique highlight identifier")
    match_id: str = Field(..., description="Match identifier")
    title: str = Field(..., description="Highlight title")
    description: Optional[str] = Field(None, description="Highlight description")
    video_url: HttpUrl = Field(..., description="Highlight video URL")
    thumbnail_url: Optional[HttpUrl] = Field(None, description="Highlight thumbnail URL")
    duration: int = Field(..., description="Highlight duration in seconds")
    tags: List[str] = Field(default_factory=list, description="Highlight tags")
    view_count: int = Field(default=0, description="Number of views")
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Request/Response models
class MatchListResponse(BaseModel):
    """Match list response model"""
    matches: List[Match] = Field(..., description="List of matches")
    total: int = Field(..., description="Total number of matches")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")

class EventListResponse(BaseModel):
    """Event list response model"""
    events: List[Event] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")

class HighlightListResponse(BaseModel):
    """Highlight list response model"""
    highlights: List[Highlight] = Field(..., description="List of highlights")
    total: int = Field(..., description="Total number of highlights")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
