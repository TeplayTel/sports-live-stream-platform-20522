from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date

class BaseSchedule(BaseModel):
    """Base schedule model with common fields"""
    schedule_id: str = Field(..., description="Unique schedule identifier")
    date: date = Field(..., description="Schedule date")
    total_matches: int = Field(default=0, description="Total number of matches for this date")
    schedule_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional schedule metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ScheduleCreate(BaseSchedule):
    """Model for creating a new schedule"""
    pass

class ScheduleUpdate(BaseModel):
    """Model for updating an existing schedule"""
    date: Optional[date] = Field(None, description="Schedule date")
    total_matches: Optional[int] = Field(None, description="Total number of matches for this date")
    schedule_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional schedule metadata")

class DailySchedule(BaseModel):
    """Daily schedule with additional metadata"""
    date: date = Field(..., description="Schedule date")
    day_name: str = Field(..., description="Day of week name")
    matches_count: int = Field(default=0, description="Number of matches")
    live_matches_count: int = Field(default=0, description="Number of live matches")
    upcoming_matches_count: int = Field(default=0, description="Number of upcoming matches")
    matches: List[Dict[str, Any]] = Field(default_factory=list, description="All matches for this date")

class WeeklySchedule(BaseModel):
    """Weekly schedule view"""
    week_start: date = Field(..., description="Start of the week")
    week_end: date = Field(..., description="End of the week")
    daily_schedules: List[DailySchedule] = Field(default_factory=list, description="Daily schedules for the week")
    total_matches: int = Field(default=0, description="Total matches in the week")

class ScheduleListResponse(BaseModel):
    """Schedule list response model"""
    schedules: List[BaseSchedule] = Field(..., description="List of schedules")
    total: int = Field(..., description="Total number of schedule entries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    date_range: Optional[Dict[str, date]] = Field(None, description="Date range covered by schedules")
