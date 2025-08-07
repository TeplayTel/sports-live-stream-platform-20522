from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from datetime import date as date_type

class BaseSchedule(BaseModel):
    """Base schedule model with common fields"""
    schedule_id: str = Field(..., description="Unique schedule identifier")
    schedule_date: date_type = Field(..., description="Schedule date", alias="date")
    total_matches: int = Field(default=0, description="Total number of matches for this date")
    schedule_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional schedule metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class ScheduleCreate(BaseModel):
    """Model for creating a new schedule"""
    schedule_date: date_type = Field(..., description="Schedule date", alias="date")
    total_matches: int = Field(default=0, description="Total number of matches for this date")
    schedule_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional schedule metadata")

    class Config:
        allow_population_by_field_name = True

class ScheduleUpdate(BaseModel):
    """Model for updating an existing schedule"""
    schedule_date: Optional[date_type] = Field(None, description="Schedule date", alias="date")
    total_matches: Optional[int] = Field(None, description="Total number of matches for this date")
    schedule_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional schedule metadata")

    class Config:
        allow_population_by_field_name = True

class DailySchedule(BaseModel):
    """Daily schedule with additional metadata"""
    schedule_date: date_type = Field(..., description="Schedule date", alias="date")
    day_name: str = Field(..., description="Day of week name")
    matches_count: int = Field(default=0, description="Number of matches")
    live_matches_count: int = Field(default=0, description="Number of live matches")
    upcoming_matches_count: int = Field(default=0, description="Number of upcoming matches")
    matches: List[Dict[str, Any]] = Field(default_factory=list, description="All matches for this date")

    class Config:
        allow_population_by_field_name = True

class WeeklySchedule(BaseModel):
    """Weekly schedule view"""
    week_start: date_type = Field(..., description="Start of the week")
    week_end: date_type = Field(..., description="End of the week")
    daily_schedules: List[DailySchedule] = Field(default_factory=list, description="Daily schedules for the week")
    total_matches: int = Field(default=0, description="Total matches in the week")

class ScheduleListResponse(BaseModel):
    """Schedule list response model"""
    schedules: List[BaseSchedule] = Field(..., description="List of schedules")
    total: int = Field(..., description="Total number of schedule entries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    date_range: Optional[Dict[str, date_type]] = Field(None, description="Date range covered by schedules")
