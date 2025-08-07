from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date

from .match import Match

class Schedule(BaseModel):
    """Schedule model for organizing matches by date"""
    schedule_id: str = Field(..., description="Unique schedule identifier")
    date: date = Field(..., description="Schedule date")
    matches: List[Match] = Field(default_factory=list, description="Matches scheduled for this date")
    total_matches: int = Field(default=0, description="Total number of matches for this date")
    featured_matches: List[Match] = Field(default_factory=list, description="Featured matches for this date")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DailySchedule(BaseModel):
    """Daily schedule with additional metadata"""
    date: date = Field(..., description="Schedule date")
    day_name: str = Field(..., description="Day of week name")
    matches_count: int = Field(default=0, description="Number of matches")
    live_matches_count: int = Field(default=0, description="Number of live matches")
    upcoming_matches_count: int = Field(default=0, description="Number of upcoming matches")
    matches: List[Match] = Field(default_factory=list, description="All matches for this date")

class WeeklySchedule(BaseModel):
    """Weekly schedule view"""
    week_start: date = Field(..., description="Start of the week")
    week_end: date = Field(..., description="End of the week")
    daily_schedules: List[DailySchedule] = Field(default_factory=list, description="Daily schedules for the week")
    total_matches: int = Field(default=0, description="Total matches in the week")

class ScheduleListResponse(BaseModel):
    """Schedule list response model"""
    schedules: List[Schedule] = Field(..., description="List of schedules")
    total: int = Field(..., description="Total number of schedule entries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    date_range: Optional[dict] = Field(None, description="Date range covered by schedules")
