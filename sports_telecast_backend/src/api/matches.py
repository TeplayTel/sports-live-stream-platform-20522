from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.match import (
    Match, Event, MatchListResponse, EventListResponse, 
    HighlightListResponse, MatchStatus, SportType
)
from ..auth.jwt_auth import optional_auth
from ..database import get_db
from ..database.repositories import MatchRepository, EventRepository, HighlightRepository
from ..database.schemas import convert_match_db_to_response, convert_event_db_to_response, convert_highlight_db_to_response

router = APIRouter(prefix="/matches", tags=["Matches"])

# PUBLIC_INTERFACE
@router.get("/", response_model=MatchListResponse, summary="Get matches list")
async def get_matches(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[MatchStatus] = Query(None, description="Filter by match status"),
    sport: Optional[SportType] = Query(None, description="Filter by sport type"),
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of matches
    
    Returns a paginated list of matches with optional filtering by status and sport type.
    Authentication is optional - authenticated users may see personalized results.
    """
    offset = (page - 1) * page_size
    match_repo = MatchRepository(db_session)
    matches_db = await match_repo.get_matches(limit=page_size, offset=offset, status=status, sport=sport)
    
    # Convert to Pydantic models
    matches = [convert_match_db_to_response(match) for match in matches_db]
    
    return MatchListResponse(
        matches=matches,
        total=len(matches),
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@router.get("/live", response_model=MatchListResponse, summary="Get live matches")  
async def get_live_matches(
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get all currently live matches
    
    Returns all matches that are currently in progress.
    """
    match_repo = MatchRepository(db_session)
    live_matches_db = await match_repo.get_live_matches()
    
    # Convert to Pydantic models
    live_matches = [convert_match_db_to_response(match) for match in live_matches_db]
    
    return MatchListResponse(
        matches=live_matches,
        total=len(live_matches),
        page=1,
        page_size=len(live_matches)
    )

# PUBLIC_INTERFACE
@router.get("/more", response_model=MatchListResponse, summary="Get more matches")
async def get_more_matches(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=50, description="Page size"),
    exclude_ids: str = Query("", description="Comma-separated match IDs to exclude"),
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get additional matches for "more matches" section
    
    Returns a curated list of matches excluding already shown matches.
    Includes a mix of live, upcoming, and recently finished matches.
    """
    match_repo = MatchRepository(db_session)
    
    # Parse excluded match IDs
    excluded_match_ids = [mid.strip() for mid in exclude_ids.split(",") if mid.strip()]
    
    # Get more matches with variety (live, upcoming, finished)
    offset = (page - 1) * page_size
    more_matches_db = await match_repo.get_more_matches(
        limit=page_size, 
        offset=offset, 
        exclude_ids=excluded_match_ids
    )
    
    # Convert to Pydantic models
    more_matches = [convert_match_db_to_response(match) for match in more_matches_db]
    
    return MatchListResponse(
        matches=more_matches,
        total=len(more_matches),
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@router.get("/{match_id}", response_model=Match, summary="Get match details")
async def get_match_details(
    match_id: str,
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific match
    
    Returns comprehensive match data including teams, score, events, and statistics.
    """
    match_repo = MatchRepository(db_session)
    match_db = await match_repo.get_match_by_id(match_id)
    if not match_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    return convert_match_db_to_response(match_db)

# PUBLIC_INTERFACE
@router.get("/{match_id}/highlights", response_model=HighlightListResponse, summary="Get match highlights")
async def get_match_highlights(
    match_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Page size"),
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get highlights for a specific match
    
    Returns video highlights and key moments from the match.
    """
    match_repo = MatchRepository(db_session)
    match_db = await match_repo.get_match_by_id(match_id)
    if not match_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    highlight_repo = HighlightRepository(db_session)
    offset = (page - 1) * page_size
    highlights_db = await highlight_repo.get_highlights(limit=page_size, offset=offset, match_id=match_id)
    
    # Convert to Pydantic models
    highlights = [convert_highlight_db_to_response(highlight) for highlight in highlights_db]
    
    return HighlightListResponse(
        highlights=highlights,
        total=len(highlights),
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@router.get("/schedule/upcoming", response_model=MatchListResponse, summary="Get upcoming matches")
async def get_upcoming_matches(
    days: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get upcoming scheduled matches
    
    Returns matches scheduled within the specified number of days.
    """
    offset = (page - 1) * page_size
    match_repo = MatchRepository(db_session)
    upcoming_matches_db = await match_repo.get_upcoming_matches(days=days, limit=page_size, offset=offset)
    
    # Convert to Pydantic models
    upcoming_matches = [convert_match_db_to_response(match) for match in upcoming_matches_db]
    
    return MatchListResponse(
        matches=upcoming_matches,
        total=len(upcoming_matches),
        page=page,
        page_size=page_size
    )

# Events endpoints
events_router = APIRouter(prefix="/events", tags=["Events"])

# PUBLIC_INTERFACE
@events_router.get("/", response_model=EventListResponse, summary="Get events list")
async def get_events(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    sport: Optional[SportType] = Query(None, description="Filter by sport type"),
    featured: Optional[bool] = Query(None, description="Filter featured events"),
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of sports events
    
    Returns a list of sports events/tournaments with optional filtering.
    """
    offset = (page - 1) * page_size
    event_repo = EventRepository(db_session)
    events_db = await event_repo.get_events(limit=page_size, offset=offset, sport=sport, featured=featured)
    
    # Convert to Pydantic models
    events = [convert_event_db_to_response(event) for event in events_db]
    
    return EventListResponse(
        events=events,
        total=len(events),
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@events_router.get("/{event_id}", response_model=Event, summary="Get event details")
async def get_event_details(
    event_id: str,
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific event
    
    Returns comprehensive event data including matches and tournament information.
    """
    event_repo = EventRepository(db_session)
    event_db = await event_repo.get_event_by_id(event_id)
    if not event_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return convert_event_db_to_response(event_db)

# PUBLIC_INTERFACE
@events_router.get("/{event_id}/matches", response_model=MatchListResponse, summary="Get event matches")
async def get_event_matches(
    event_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[MatchStatus] = Query(None, description="Filter by match status"),
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get matches for a specific event
    
    Returns all matches that belong to the specified event/tournament.
    """
    event_repo = EventRepository(db_session)
    event_db = await event_repo.get_event_by_id(event_id)
    if not event_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get all matches for this event
    offset = (page - 1) * page_size
    match_repo = MatchRepository(db_session)
    event_matches_db = await match_repo.get_matches(limit=page_size, offset=offset, status=status)
    
    # Filter for this event (this could be optimized with a specific repository method)
    event_matches_db = [m for m in event_matches_db if m.event_id == event_id]
    
    # Convert to Pydantic models
    event_matches = [convert_match_db_to_response(match) for match in event_matches_db]
    
    return MatchListResponse(
        matches=event_matches,
        total=len(event_matches),
        page=page,
        page_size=page_size
    )

# Include events router
router.include_router(events_router)
