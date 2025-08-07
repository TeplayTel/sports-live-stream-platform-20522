from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ProfileVisibility(str, Enum):
    """Profile visibility settings"""
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class NotificationPreference(BaseModel):
    """Individual notification preference"""
    type: str = Field(..., description="Notification type")
    enabled: bool = Field(default=True, description="Whether this notification is enabled")
    frequency: Optional[str] = Field(None, description="Notification frequency (immediate, daily, weekly)")

class UserProfile(BaseModel):
    """Extended user profile model"""
    profile_id: str = Field(..., description="Unique profile identifier")
    user_id: str = Field(..., description="Associated user identifier")
    display_name: Optional[str] = Field(None, description="Public display name")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    location: Optional[str] = Field(None, description="User location")
    website: Optional[HttpUrl] = Field(None, description="User website URL")
    avatar_url: Optional[HttpUrl] = Field(None, description="Profile avatar URL")
    cover_image_url: Optional[HttpUrl] = Field(None, description="Profile cover image URL")
    
    # Sports preferences
    favorite_teams: List[str] = Field(default_factory=list, description="List of favorite team IDs")
    favorite_sports: List[str] = Field(default_factory=list, description="List of favorite sports")
    favorite_players: List[str] = Field(default_factory=list, description="List of favorite player names")
    favorite_leagues: List[str] = Field(default_factory=list, description="List of favorite league IDs")
    
    # Notification preferences
    notification_preferences: List[NotificationPreference] = Field(
        default_factory=lambda: [
            NotificationPreference(type="match_start", enabled=True, frequency="immediate"),
            NotificationPreference(type="score_update", enabled=True, frequency="immediate"),
            NotificationPreference(type="match_end", enabled=True, frequency="immediate"),
            NotificationPreference(type="highlights_available", enabled=True, frequency="immediate"),
            NotificationPreference(type="team_news", enabled=False, frequency="daily"),
            NotificationPreference(type="weekly_summary", enabled=True, frequency="weekly")
        ],
        description="User notification preferences"
    )
    
    # Privacy settings
    profile_visibility: ProfileVisibility = Field(default=ProfileVisibility.PUBLIC, description="Profile visibility setting")
    show_favorite_teams: bool = Field(default=True, description="Whether to show favorite teams publicly")
    show_activity: bool = Field(default=True, description="Whether to show user activity")
    allow_friend_requests: bool = Field(default=True, description="Whether to allow friend requests")
    
    # Activity tracking
    total_reactions: int = Field(default=0, description="Total emoji reactions given")
    matches_watched: int = Field(default=0, description="Number of matches watched")
    highlights_watched: int = Field(default=0, description="Number of highlights watched")
    
    # Localization
    preferred_language: str = Field(default="en", description="Preferred language code")
    timezone: str = Field(default="UTC", description="User timezone")
    date_format: str = Field(default="MM/DD/YYYY", description="Preferred date format")
    time_format: str = Field(default="12h", description="Preferred time format (12h/24h)")
    
    # Metadata
    is_verified: bool = Field(default=False, description="Whether profile is verified")
    is_public: bool = Field(default=True, description="Whether profile is publicly visible")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Profile creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

class UserProfileCreate(BaseModel):
    """User profile creation model"""
    user_id: str = Field(..., description="Associated user identifier")
    display_name: Optional[str] = Field(None, description="Public display name")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    location: Optional[str] = Field(None, description="User location")
    website: Optional[HttpUrl] = Field(None, description="User website URL")
    favorite_teams: List[str] = Field(default_factory=list, description="List of favorite team IDs")
    favorite_sports: List[str] = Field(default_factory=list, description="List of favorite sports")

class UserProfileUpdate(BaseModel):
    """User profile update model"""
    display_name: Optional[str] = Field(None, description="Public display name")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    location: Optional[str] = Field(None, description="User location")
    website: Optional[HttpUrl] = Field(None, description="User website URL")
    avatar_url: Optional[HttpUrl] = Field(None, description="Profile avatar URL")
    cover_image_url: Optional[HttpUrl] = Field(None, description="Profile cover image URL")
    favorite_teams: Optional[List[str]] = Field(None, description="List of favorite team IDs")
    favorite_sports: Optional[List[str]] = Field(None, description="List of favorite sports")
    favorite_players: Optional[List[str]] = Field(None, description="List of favorite player names")
    favorite_leagues: Optional[List[str]] = Field(None, description="List of favorite league IDs")
    notification_preferences: Optional[List[NotificationPreference]] = Field(None, description="Notification preferences")
    profile_visibility: Optional[ProfileVisibility] = Field(None, description="Profile visibility setting")
    show_favorite_teams: Optional[bool] = Field(None, description="Whether to show favorite teams publicly")
    show_activity: Optional[bool] = Field(None, description="Whether to show user activity")
    preferred_language: Optional[str] = Field(None, description="Preferred language code")
    timezone: Optional[str] = Field(None, description="User timezone")

class UserProfileResponse(BaseModel):
    """User profile response model"""
    profile_id: str = Field(..., description="Unique profile identifier")
    user_id: str = Field(..., description="Associated user identifier")
    display_name: Optional[str] = Field(None, description="Public display name")
    bio: Optional[str] = Field(None, description="User biography")
    location: Optional[str] = Field(None, description="User location")
    website: Optional[HttpUrl] = Field(None, description="User website URL")
    avatar_url: Optional[HttpUrl] = Field(None, description="Profile avatar URL")
    cover_image_url: Optional[HttpUrl] = Field(None, description="Profile cover image URL")
    favorite_teams: List[str] = Field(..., description="List of favorite team IDs")
    favorite_sports: List[str] = Field(..., description="List of favorite sports")
    favorite_players: List[str] = Field(..., description="List of favorite player names")
    favorite_leagues: List[str] = Field(..., description="List of favorite league IDs")
    profile_visibility: ProfileVisibility = Field(..., description="Profile visibility setting")
    total_reactions: int = Field(..., description="Total emoji reactions given")
    matches_watched: int = Field(..., description="Number of matches watched")
    highlights_watched: int = Field(..., description="Number of highlights watched")
    is_verified: bool = Field(..., description="Whether profile is verified")
    preferred_language: str = Field(..., description="Preferred language code")
    timezone: str = Field(..., description="User timezone")
    created_at: datetime = Field(..., description="Profile creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
