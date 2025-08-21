from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    """User role enumeration (lowercase values to match DB and OpenAPI)"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

    @classmethod
    def _missing_(cls, value):
        """
        Normalize arbitrary input into a valid lowercase user role.
        Accepts uppercase/mixed-case strings or enum-like inputs and coerces
        to the first matching lowercase enum value. Defaults to 'user'.
        """
        try:
            if isinstance(value, str):
                lower = value.lower()
                for member in cls:
                    if member.value == lower:
                        return member
        except Exception:
            pass
        return cls.USER

class UserPreferences(BaseModel):
    """User preferences model"""
    favorite_teams: List[str] = Field(default_factory=list, description="List of favorite team IDs")
    favorite_sports: List[str] = Field(default_factory=list, description="List of favorite sports")
    notification_settings: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email_notifications": True,
            "push_notifications": True,
            "match_reminders": True,
            "score_updates": True
        },
        description="Notification preferences"
    )
    preferred_language: str = Field(default="en", description="Preferred language code")
    timezone: str = Field(default="UTC", description="User timezone")

class User(BaseModel):
    """User model"""
    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    full_name: Optional[str] = Field(None, description="User's full name")
    avatar_url: Optional[str] = Field(None, description="URL to user avatar image")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")
    is_active: bool = Field(default=True, description="Whether user account is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

class UserCreate(BaseModel):
    """User creation model"""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="User password")
    full_name: Optional[str] = Field(None, description="User's full name")

class UserUpdate(BaseModel):
    """User update model"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    full_name: Optional[str] = Field(None, description="User's full name")
    avatar_url: Optional[str] = Field(None, description="URL to user avatar image")
    preferences: Optional[UserPreferences] = Field(None, description="User preferences")

class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class UserResponse(BaseModel):
    """User response model (without sensitive data)"""
    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="User's full name")
    avatar_url: Optional[str] = Field(None, description="URL to user avatar image")
    role: UserRole = Field(..., description="User role")
    preferences: UserPreferences = Field(..., description="User preferences")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class TokenData(BaseModel):
    """JWT token data model"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")
