from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy.orm import Session

from ..models.match import (
    Match, Event, MatchListResponse, EventListResponse, 
    HighlightListResponse, MatchStatus, SportType, Team, Score, MatchEvent
)
<<<<<<< HEAD
from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user_optional
from ..database.session import get_db
from ..database.service import DatabaseService
=======
from ..auth.jwt_auth import optional_auth
from ..database.connection import get_db
from ..database.repositories import MatchRepository, EventRepository, HighlightRepository
from ..database.schemas import (
    convert_match_db_to_pydantic, convert_event_db_to_pydantic, 
    convert_highlight_db_to_pydantic
)
>>>>>>> cga-cg908b179b

router = APIRouter(prefix="/matches", tags=["Matches"])

def convert_db_match_to_pydantic(db_match, db_service: DatabaseService) -> Match:
    """Convert database match model to Pydantic model"""
    home_team = db_service.get_team_by_id(db_match.home_team_id)
    away_team = db_service.get_team_by_id(db_match.away_team_id)
    
    if not home_team or not away_team:
        raise HTTPException(status_code=500, detail="Team information not found")
    
    # Get match events
    match_events = []
    for event in db_match.match_events:
        match_events.append(MatchEvent(
            event_id=event.event_id,
            match_id=event.match_id,
            event_type=event.event_type,
            minute=event.minute,
            team_id=event.team_id,
            player_name=event.player_name,
            description=event.description,
            created_at=event.created_at
        ))
    
    return Match(
        match_id=db_match.match_id,
        event_id=db_match.event_id,
        home_team=Team(
            team_id=home_team.team_id,
            name=home_team.name,
            short_name=home_team.short_name,
            logo_url=home_team.logo_url,
            colors=home_team.colors or {}
        ),
        away_team=Team(
            team_id=away_team.team_id,
            name=away_team.name,
            short_name=away_team.short_name,
            logo_url=away_team.logo_url,
            colors=away_team.colors or {}
        ),
        sport_type=SportType(db_match.sport_type),
        status=MatchStatus(db_match.status),
        score=Score(
            home_score=db_match.home_score,
            away_score=db_match.away_score,
            period_scores=db_match.period_scores or []
        ),
        start_time=db_match.start_time,
        end_time=db_match.end_time,
        venue=db_match.venue,
        competition=db_match.competition,
        round=db_match.round,
        stream_url=db_match.stream_url,
        events=match_events,
        statistics=db_match.statistics or {},
        created_at=db_match.created_at,
        updated_at=db_match.updated_at
    )

# PUBLIC_INTERFACE
@router.get("/", response_model=MatchListResponse, summary="Get matches list")
async def get_matches(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[MatchStatus] = Query(None, description="Filter by match status"),
    sport: Optional[SportType] = Query(None, description="Filter by sport type"),
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get paginated list of matches
    
    Returns a paginated list of matches with optional filtering by status and sport type.
    Authentication is optional - authenticated users may see personalized results.
    """
<<<<<<< HEAD
    try:
        db_service = DatabaseService(db)
        offset = (page - 1) * page_size
        matches, total = db_service.get_matches(
            limit=page_size, 
            offset=offset,
            status=status,
            sport=sport
        )
        
        # Convert database models to Pydantic models
        match_list = []
        for match in matches:
            try:
                match_data = convert_db_match_to_pydantic(match, db_service)
                match_list.append(match_data)
            except Exception as e:
                print(f"Error converting match {match.match_id}: {e}")
                continue
        
        return MatchListResponse(
            matches=match_list,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving matches: {str(e)}")

# PUBLIC_INTERFACE
@router.get("/live", response_model=MatchListResponse, summary="Get live matches")  
def get_live_matches(
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    match_repo = MatchRepository(db)
    offset = (page - 1) * page_size
    
    matches_db = await match_repo.get_matches(
        limit=page_size,
        offset=offset,
        status=status,
        sport=sport
    )
    
    # Convert to Pydantic models
    matches = [convert_match_db_to_pydantic(match_db) for match_db in matches_db]
    
    # Get total count for pagination (this is a simplified approach)
    # In production, you might want a separate count query
    total = len(matches) if len(matches) < page_size else page_size * page + 1
    
    return MatchListResponse(
        matches=matches,
        total=total,
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@router.get("/live", response_model=MatchListResponse, summary="Get live matches")  
async def get_live_matches(
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get all currently live matches
    
    Returns all matches that are currently in progress.
    """
<<<<<<< HEAD
    try:
        db_service = DatabaseService(db)
        matches = db_service.get_live_matches()
        
        # Convert database models to Pydantic models
        match_list = []
        for match in matches:
            try:
                match_data = convert_db_match_to_pydantic(match, db_service)
                match_list.append(match_data)
            except Exception as e:
                print(f"Error converting live match {match.match_id}: {e}")
                continue
        
        return MatchListResponse(
            matches=match_list,
            total=len(match_list),
            page=1,
            page_size=len(match_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving live matches: {str(e)}")
=======
    match_repo = MatchRepository(db)
    live_matches_db = await match_repo.get_live_matches()
    
    # Convert to Pydantic models
    live_matches = [convert_match_db_to_pydantic(match_db) for match_db in live_matches_db]
    
    return MatchListResponse(
        matches=live_matches,
        total=len(live_matches),
        page=1,
        page_size=len(live_matches)
    )
>>>>>>> cga-cg908b179b

# PUBLIC_INTERFACE
@router.get("/{match_id}", response_model=Match, summary="Get match details")
async def get_match_details(
    match_id: str,
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get detailed information about a specific match
    
    Returns comprehensive match data including teams, score, events, and statistics.
    """
<<<<<<< HEAD
    try:
        db_service = DatabaseService(db)
        match = db_service.get_match_by_id(match_id)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found"
            )
        
        match_data = convert_db_match_to_pydantic(match, db_service)
        return match_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving match: {str(e)}")
=======
    match_repo = MatchRepository(db)
    match_db = await match_repo.get_match_by_id(match_id)
    
    if not match_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    return convert_match_db_to_pydantic(match_db)
>>>>>>> cga-cg908b179b

# PUBLIC_INTERFACE
@router.get("/{match_id}/highlights", response_model=HighlightListResponse, summary="Get match highlights")
async def get_match_highlights(
    match_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Page size"),
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get highlights for a specific match
    
    Returns video highlights and key moments from the match.
    """
<<<<<<< HEAD
    try:
        db_service = DatabaseService(db)
        match = db_service.get_match_by_id(match_id)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found"
            )
        
        offset = (page - 1) * page_size
        highlights, total = db_service.get_highlights(
            limit=page_size,
            offset=offset,
            match_id=match_id
        )
        
        # Convert to Pydantic models
        from ..models.match import Highlight
        highlight_list = []
        for highlight in highlights:
            highlight_data = Highlight(
                highlight_id=highlight.highlight_id,
                match_id=highlight.match_id,
                title=highlight.title,
                description=highlight.description,
                video_url=highlight.video_url,
                thumbnail_url=highlight.thumbnail_url,
                duration=highlight.duration,
                tags=highlight.tags or [],
                view_count=highlight.view_count,
                created_at=highlight.created_at
            )
            highlight_list.append(highlight_data)
        
        return HighlightListResponse(
            highlights=highlight_list,
            total=total,
            page=page,
            page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving highlights: {str(e)}")
=======
    # First verify match exists
    match_repo = MatchRepository(db)
    match_db = await match_repo.get_match_by_id(match_id)
    if not match_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    # Get highlights for the match
    highlight_repo = HighlightRepository(db)
    offset = (page - 1) * page_size
    highlights_db = await highlight_repo.get_highlights(
        limit=page_size,
        offset=offset,
        match_id=match_id
    )
    
    # Convert to Pydantic models
    highlights = [convert_highlight_db_to_pydantic(highlight_db) for highlight_db in highlights_db]
    
    return HighlightListResponse(
        highlights=highlights,
        total=len(highlights) if len(highlights) < page_size else page_size * page + 1,
        page=page,
        page_size=page_size
    )
>>>>>>> cga-cg908b179b

# PUBLIC_INTERFACE
@router.get("/schedule/upcoming", response_model=MatchListResponse, summary="Get upcoming matches")
async def get_upcoming_matches(
    days: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get upcoming scheduled matches
    
    Returns matches scheduled within the specified number of days.
    """
<<<<<<< HEAD
    try:
        db_service = DatabaseService(db)
        offset = (page - 1) * page_size
        matches, total = db_service.get_upcoming_matches(
            days=days,
            limit=page_size,
            offset=offset
        )
        
        # Convert database models to Pydantic models
        match_list = []
        for match in matches:
            try:
                match_data = convert_db_match_to_pydantic(match, db_service)
                match_list.append(match_data)
            except Exception as e:
                print(f"Error converting upcoming match {match.match_id}: {e}")
                continue
        
        return MatchListResponse(
            matches=match_list,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving upcoming matches: {str(e)}")
=======
    match_repo = MatchRepository(db)
    offset = (page - 1) * page_size
    
    upcoming_matches_db = await match_repo.get_upcoming_matches(
        days=days,
        limit=page_size,
        offset=offset
    )
    
    # Convert to Pydantic models
    upcoming_matches = [convert_match_db_to_pydantic(match_db) for match_db in upcoming_matches_db]
    
    return MatchListResponse(
        matches=upcoming_matches,
        total=len(upcoming_matches) if len(upcoming_matches) < page_size else page_size * page + 1,
        page=page,
        page_size=page_size
    )
>>>>>>> cga-cg908b179b

# Events endpoints
events_router = APIRouter(prefix="/events", tags=["Events"])

# PUBLIC_INTERFACE
@events_router.get("/", response_model=EventListResponse, summary="Get events list")
async def get_events(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    sport: Optional[SportType] = Query(None, description="Filter by sport type"),
    featured: Optional[bool] = Query(None, description="Filter featured events"),
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get paginated list of sports events
    
    Returns a list of sports events/tournaments with optional filtering.
    """
<<<<<<< HEAD
    try:
        db_service = DatabaseService(db)
        offset = (page - 1) * page_size
        events, total = db_service.get_events(
            limit=page_size,
            offset=offset,
            sport=sport,
            featured=featured
        )
        
        # Convert database models to Pydantic models
        event_list = []
        for event in events:
            event_data = Event(
                event_id=event.event_id,
                name=event.name,
                description=event.description,
                sport_type=SportType(event.sport_type),
                start_date=event.start_date,
                end_date=event.end_date,
                location=event.location,
                organizer=event.organizer,
                logo_url=event.logo_url,
                banner_url=event.banner_url,
                is_featured=event.is_featured,
                matches=[],  # Will be populated separately if needed
                created_at=event.created_at,
                updated_at=event.updated_at
            )
            event_list.append(event_data)
        
        return EventListResponse(
            events=event_list,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events: {str(e)}")
=======
    event_repo = EventRepository(db)
    offset = (page - 1) * page_size
    
    events_db = await event_repo.get_events(
        limit=page_size,
        offset=offset,
        sport=sport,
        featured=featured
    )
    
    # Convert to Pydantic models
    events = [convert_event_db_to_pydantic(event_db) for event_db in events_db]
    
    return EventListResponse(
        events=events,
        total=len(events) if len(events) < page_size else page_size * page + 1,
        page=page,
        page_size=page_size
    )
>>>>>>> cga-cg908b179b

# PUBLIC_INTERFACE
@events_router.get("/{event_id}", response_model=Event, summary="Get event details")
async def get_event_details(
    event_id: str,
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get detailed information about a specific event
    
    Returns comprehensive event data including matches and tournament information.
    """
<<<<<<< HEAD
    try:
        db_service = DatabaseService(db)
        event = db_service.get_event_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Get matches for this event
        event_matches, _ = db_service.get_event_matches(event_id, limit=100, offset=0)
        
        matches_list = []
        for match in event_matches:
            try:
                match_data = convert_db_match_to_pydantic(match, db_service)
                matches_list.append(match_data)
            except Exception as e:
                print(f"Error converting event match {match.match_id}: {e}")
                continue
        
        event_data = Event(
            event_id=event.event_id,
            name=event.name,
            description=event.description,
            sport_type=SportType(event.sport_type),
            start_date=event.start_date,
            end_date=event.end_date,
            location=event.location,
            organizer=event.organizer,
            logo_url=event.logo_url,
            banner_url=event.banner_url,
            is_featured=event.is_featured,
            matches=matches_list,
            created_at=event.created_at,
            updated_at=event.updated_at
        )
        
        return event_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving event: {str(e)}")
=======
    event_repo = EventRepository(db)
    event_db = await event_repo.get_event_by_id(event_id)
    
    if not event_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return convert_event_db_to_pydantic(event_db, include_matches=True)
>>>>>>> cga-cg908b179b

# PUBLIC_INTERFACE
@events_router.get("/{event_id}/matches", response_model=MatchListResponse, summary="Get event matches")
async def get_event_matches(
    event_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[MatchStatus] = Query(None, description="Filter by match status"),
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get matches for a specific event
    
    Returns all matches that belong to the specified event/tournament.
    """
<<<<<<< HEAD
    try:
        db_service = DatabaseService(db)
        event = db_service.get_event_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        offset = (page - 1) * page_size
        matches, total = db_service.get_event_matches(
            event_id=event_id,
            limit=page_size,
            offset=offset,
            status=status
        )
        
        # Convert database models to Pydantic models
        match_list = []
        for match in matches:
            try:
                match_data = convert_db_match_to_pydantic(match, db_service)
                match_list.append(match_data)
            except Exception as e:
                print(f"Error converting event match {match.match_id}: {e}")
                continue
        
        return MatchListResponse(
            matches=match_list,
            total=total,
            page=page,
            page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving event matches: {str(e)}")
=======
    # First verify event exists
    event_repo = EventRepository(db)
    event_db = await event_repo.get_event_by_id(event_id)
    if not event_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get matches for this event
    match_repo = MatchRepository(db)
    offset = (page - 1) * page_size
    
    # Use the dedicated method for getting matches by event ID
    event_matches_db = await match_repo.get_matches_by_event_id(
        event_id=event_id,
        limit=page_size,
        offset=offset,
        status=status
    )
    
    # Convert to Pydantic models
    matches = [convert_match_db_to_pydantic(match_db) for match_db in event_matches_db]
    
    # For total count, this is simplified - in production you'd want a separate count query
    total = len(matches) if len(matches) < page_size else page_size * page + 1
    
    return MatchListResponse(
        matches=matches,
        total=total,
        page=page,
        page_size=page_size
    )
>>>>>>> cga-cg908b179b

# Include events router
router.include_router(events_router)
