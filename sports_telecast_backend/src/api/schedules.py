from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta

from ..models.schedule import (
    BaseSchedule, ScheduleCreate, ScheduleUpdate, 
    DailySchedule, WeeklySchedule, ScheduleListResponse
)
from ..database.connection import get_db
from ..database.models import ScheduleDB, MatchDB
from ..database.schemas import convert_match_db_to_response
import uuid

router = APIRouter(prefix="/schedules", tags=["Schedules"])

# PUBLIC_INTERFACE
@router.get("/daily/{schedule_date}", response_model=DailySchedule, summary="Get daily schedule")
async def get_daily_schedule(
    schedule_date: date,
    include_matches: bool = Query(True, description="Include match details"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the schedule for a specific date
    
    Returns all matches scheduled for the given date with optional
    match details and team information.
    """
    # Get matches for the date
    start_datetime = datetime.combine(schedule_date, datetime.min.time())
    end_datetime = start_datetime + timedelta(days=1)
    
    query = select(MatchDB).options(
        selectinload(MatchDB.home_team),
        selectinload(MatchDB.away_team),
        selectinload(MatchDB.event)
    ).where(
        and_(
            MatchDB.start_time >= start_datetime,
            MatchDB.start_time < end_datetime
        )
    ).order_by(MatchDB.start_time)
    
    result = await db.execute(query)
    matches = result.scalars().all()
    
    # Count matches by status
    live_count = sum(1 for m in matches if m.status.value == "live")
    upcoming_count = sum(1 for m in matches if m.status.value == "scheduled")
    
    # Convert matches to response format
    match_data = []
    if include_matches:
        match_data = [convert_match_db_to_response(match).dict() for match in matches]
    
    return DailySchedule(
        schedule_date=schedule_date,
        day_name=schedule_date.strftime("%A"),
        matches_count=len(matches),
        live_matches_count=live_count,
        upcoming_matches_count=upcoming_count,
        matches=match_data
    )

# PUBLIC_INTERFACE
@router.get("/weekly", response_model=WeeklySchedule, summary="Get weekly schedule")
async def get_weekly_schedule(
    start_date: Optional[date] = Query(None, description="Week start date (defaults to current week)"),
    include_matches: bool = Query(True, description="Include match details"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the schedule for a week
    
    Returns daily schedules for a 7-day period, starting from the
    specified date or current week if not provided.
    """
    if not start_date:
        today = date.today()
        # Get Monday of current week
        start_date = today - timedelta(days=today.weekday())
    
    end_date = start_date + timedelta(days=6)
    
    daily_schedules = []
    total_matches = 0
    
    # Get schedule for each day of the week
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        daily_schedule = await get_daily_schedule(
            current_date, 
            include_matches=include_matches, 
            db=db
        )
        daily_schedules.append(daily_schedule)
        total_matches += daily_schedule.matches_count
    
    return WeeklySchedule(
        week_start=start_date,
        week_end=end_date,
        daily_schedules=daily_schedules,
        total_matches=total_matches
    )

# PUBLIC_INTERFACE
@router.get("/", response_model=ScheduleListResponse, summary="Get schedules")
async def get_schedules(
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date"),
    sport_type: Optional[str] = Query(None, description="Filter by sport type"),
    limit: int = Query(30, ge=1, le=100, description="Number of schedule entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of schedules
    
    Returns schedule entries with filtering options for date range
    and sport type.
    """
    query = select(ScheduleDB).options(
        selectinload(ScheduleDB.matches).selectinload(MatchDB.home_team),
        selectinload(ScheduleDB.matches).selectinload(MatchDB.away_team),
        selectinload(ScheduleDB.matches).selectinload(MatchDB.event)
    )
    
    # Apply filters
    conditions = []
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        conditions.append(ScheduleDB.date >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        conditions.append(ScheduleDB.date <= end_datetime)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.order_by(ScheduleDB.date.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    schedules = result.scalars().all()
    
    # Convert to response format
    schedule_responses = []
    for schedule in schedules:
        schedule_responses.append(BaseSchedule(
            schedule_id=str(schedule.schedule_id),
            schedule_date=schedule.date.date() if schedule.date else date.today(),
            total_matches=schedule.total_matches,
            schedule_metadata=schedule.schedule_metadata,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at
        ))
    
    # Calculate date range
    date_range = None
    if schedules:
        min_date = min(s.date.date() if s.date else date.today() for s in schedules)
        max_date = max(s.date.date() if s.date else date.today() for s in schedules)
        date_range = {"start": min_date, "end": max_date}
    
    return ScheduleListResponse(
        schedules=schedule_responses,
        total=total,
        page=offset // limit + 1,
        page_size=limit,
        date_range=date_range
    )

# PUBLIC_INTERFACE
@router.get("/upcoming", response_model=List[DailySchedule], summary="Get upcoming schedules")
async def get_upcoming_schedules(
    days: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    include_matches: bool = Query(True, description="Include match details"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get upcoming schedules for the next N days
    
    Returns daily schedules for upcoming days, filtering out
    days with no scheduled matches.
    """
    today = date.today()
    schedules = []
    
    for i in range(days):
        current_date = today + timedelta(days=i)
        daily_schedule = await get_daily_schedule(
            current_date, 
            include_matches=include_matches, 
            db=db
        )
        
        # Only include days with matches
        if daily_schedule.matches_count > 0:
            schedules.append(daily_schedule)
    
    return schedules

# PUBLIC_INTERFACE
@router.get("/live", response_model=DailySchedule, summary="Get live matches schedule")
async def get_live_matches_schedule(
    include_matches: bool = Query(True, description="Include match details"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current live matches
    
    Returns all currently live matches in a daily schedule format.
    """
    from ..database.models import MatchStatusEnum
    
    query = select(MatchDB).options(
        selectinload(MatchDB.home_team),
        selectinload(MatchDB.away_team),
        selectinload(MatchDB.event)
    ).where(MatchDB.status == MatchStatusEnum.LIVE).order_by(MatchDB.start_time)
    
    result = await db.execute(query)
    live_matches = result.scalars().all()
    
    # Convert matches to response format
    match_data = []
    if include_matches:
        match_data = [convert_match_db_to_response(match).dict() for match in live_matches]
    
    return DailySchedule(
        schedule_date=date.today(),
        day_name="Live Now",
        matches_count=len(live_matches),
        live_matches_count=len(live_matches),
        upcoming_matches_count=0,
        matches=match_data
    )

# PUBLIC_INTERFACE
@router.post("/", response_model=BaseSchedule, summary="Create schedule")
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new schedule entry
    
    Creates a schedule entry for a specific date with metadata.
    This is typically used by admin users to organize matches.
    """
    # Check if schedule already exists for the date
    schedule_datetime = datetime.combine(schedule_data.schedule_date, datetime.min.time())
    existing = await db.execute(
        select(ScheduleDB).where(ScheduleDB.date == schedule_datetime)
    )
    
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule already exists for this date"
        )
    
    schedule = ScheduleDB(
        schedule_id=str(uuid.uuid4()),
        date=schedule_datetime,
        total_matches=schedule_data.total_matches,
        schedule_metadata=schedule_data.schedule_metadata,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    
    return BaseSchedule(
        schedule_id=str(schedule.schedule_id),
        schedule_date=schedule.date.date(),
        total_matches=schedule.total_matches,
        schedule_metadata=schedule.schedule_metadata,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )

# PUBLIC_INTERFACE
@router.put("/{schedule_id}", response_model=BaseSchedule, summary="Update schedule")
async def update_schedule(
    schedule_id: str,
    schedule_update: ScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing schedule
    
    Updates schedule metadata and match count for an existing schedule entry.
    """
    result = await db.execute(
        select(ScheduleDB).where(ScheduleDB.schedule_id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Update fields
    if schedule_update.schedule_date is not None:
        schedule.date = datetime.combine(schedule_update.schedule_date, datetime.min.time())
    if schedule_update.total_matches is not None:
        schedule.total_matches = schedule_update.total_matches
    if schedule_update.schedule_metadata is not None:
        schedule.schedule_metadata = schedule_update.schedule_metadata
    
    schedule.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(schedule)
    
    return BaseSchedule(
        schedule_id=str(schedule.schedule_id),
        date=schedule.date.date(),
        total_matches=schedule.total_matches,
        schedule_metadata=schedule.schedule_metadata,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )

# PUBLIC_INTERFACE
@router.delete("/{schedule_id}", summary="Delete schedule")
async def delete_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a schedule entry
    
    Removes a schedule entry and its associated match relationships.
    This does not delete the matches themselves.
    """
    result = await db.execute(
        select(ScheduleDB).where(ScheduleDB.schedule_id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    await db.delete(schedule)
    await db.commit()
    
    return {"message": "Schedule deleted successfully"}
