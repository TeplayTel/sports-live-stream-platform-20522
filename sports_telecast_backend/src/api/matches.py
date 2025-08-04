from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from datetime import datetime, timedelta

from ..models.match import (
    Match, Event, MatchListResponse, EventListResponse, 
    HighlightListResponse, MatchStatus, SportType
)
from ..auth.jwt_auth import optional_auth
from ..database.connection import db

router = APIRouter(prefix="/matches", tags=["Matches"])

# PUBLIC_INTERFACE
@router.get("/", response_model=MatchListResponse, summary="Get matches list")
def get_matches(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[MatchStatus] = Query(None, description="Filter by match status"),
    sport: Optional[SportType] = Query(None, description="Filter by sport type"),
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get paginated list of matches
    
    Returns a paginated list of matches with optional filtering by status and sport type.
    Authentication is optional - authenticated users may see personalized results.
    """
    offset = (page - 1) * page_size
    matches = db.get_matches(limit=page_size, offset=offset)
    
    # Apply filters
    if status:
        matches = [m for m in matches if m.status == status]
    
    if sport:
        matches = [m for m in matches if m.sport_type == sport]
    
    # Sort by start time
    matches.sort(key=lambda x: x.start_time)
    
    return MatchListResponse(
        matches=matches,
        total=len(matches),
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@router.get("/live", response_model=MatchListResponse, summary="Get live matches")  
def get_live_matches(user_id: Optional[str] = Depends(optional_auth)):
    """
    Get all currently live matches
    
    Returns all matches that are currently in progress.
    """
    live_matches = db.get_live_matches()
    
    return MatchListResponse(
        matches=live_matches,
        total=len(live_matches),
        page=1,
        page_size=len(live_matches)
    )

# PUBLIC_INTERFACE
@router.get("/{match_id}", response_model=Match, summary="Get match details")
def get_match_details(
    match_id: str,
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get detailed information about a specific match
    
    Returns comprehensive match data including teams, score, events, and statistics.
    """
    match = db.get_match_by_id(match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    return match

# PUBLIC_INTERFACE
@router.get("/{match_id}/highlights", response_model=HighlightListResponse, summary="Get match highlights")
def get_match_highlights(
    match_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Page size"),
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get highlights for a specific match
    
    Returns video highlights and key moments from the match.
    """
    match = db.get_match_by_id(match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    highlights = db.get_highlights_by_match(match_id)
    
    # Apply pagination
    offset = (page - 1) * page_size
    paginated_highlights = highlights[offset:offset + page_size]
    
    return HighlightListResponse(
        highlights=paginated_highlights,
        total=len(highlights),
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@router.get("/schedule/upcoming", response_model=MatchListResponse, summary="Get upcoming matches")
def get_upcoming_matches(
    days: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get upcoming scheduled matches
    
    Returns matches scheduled within the specified number of days.
    """
    end_date = datetime.utcnow() + timedelta(days=days)
    
    offset = (page - 1) * page_size
    all_matches = db.get_matches(limit=1000, offset=0)  # Get more to filter
    
    # Filter for scheduled matches within date range
    upcoming_matches = [
        match for match in all_matches
        if match.status == MatchStatus.SCHEDULED and 
        match.start_time <= end_date and
        match.start_time >= datetime.utcnow()
    ]
    
    # Sort by start time
    upcoming_matches.sort(key=lambda x: x.start_time)
    
    # Apply pagination
    paginated_matches = upcoming_matches[offset:offset + page_size]
    
    return MatchListResponse(
        matches=paginated_matches,
        total=len(upcoming_matches),
        page=page,
        page_size=page_size
    )

# Events endpoints
events_router = APIRouter(prefix="/events", tags=["Events"])

# PUBLIC_INTERFACE
@events_router.get("/", response_model=EventListResponse, summary="Get events list")
def get_events(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    sport: Optional[SportType] = Query(None, description="Filter by sport type"),
    featured: Optional[bool] = Query(None, description="Filter featured events"),
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get paginated list of sports events
    
    Returns a list of sports events/tournaments with optional filtering.
    """
    offset = (page - 1) * page_size
    events = db.get_events(limit=page_size, offset=offset)
    
    # Apply filters
    if sport:
        events = [e for e in events if e.sport_type == sport]
    
    if featured is not None:
        events = [e for e in events if e.is_featured == featured]
    
    return EventListResponse(
        events=events,
        total=len(events),
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@events_router.get("/{event_id}", response_model=Event, summary="Get event details")
def get_event_details(
    event_id: str,
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get detailed information about a specific event
    
    Returns comprehensive event data including matches and tournament information.
    """
    event = db.get_event_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return event

# PUBLIC_INTERFACE
@events_router.get("/{event_id}/matches", response_model=MatchListResponse, summary="Get event matches")
def get_event_matches(
    event_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[MatchStatus] = Query(None, description="Filter by match status"),
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get matches for a specific event
    
    Returns all matches that belong to the specified event/tournament.
    """
    event = db.get_event_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get all matches for this event
    all_matches = db.get_matches(limit=1000, offset=0)
    event_matches = [m for m in all_matches if m.event_id == event_id]
    
    # Apply status filter
    if status:
        event_matches = [m for m in event_matches if m.status == status]
    
    # Sort by start time
    event_matches.sort(key=lambda x: x.start_time)
    
    # Apply pagination
    offset = (page - 1) * page_size
    paginated_matches = event_matches[offset:offset + page_size]
    
    return MatchListResponse(
        matches=paginated_matches,
        total=len(event_matches),
        page=page,
        page_size=page_size
    )

# Include events router
router.include_router(events_router)
