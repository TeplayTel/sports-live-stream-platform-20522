from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.profile import (
    UserProfileCreate, UserProfileUpdate, UserProfileResponse
)
from ..auth.jwt_auth import get_current_user_id, optional_auth
from ..database.connection import get_db
from ..database.models import UserProfileDB, UserDB, ProfileVisibilityEnum
from datetime import datetime
import uuid

router = APIRouter(prefix="/profiles", tags=["User Profiles"])

# PUBLIC_INTERFACE
@router.post("/", response_model=UserProfileResponse, summary="Create user profile")
async def create_user_profile(
    profile_data: UserProfileCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user profile
    
    Creates a comprehensive user profile with sports preferences, 
    notification settings, and privacy controls.
    """
    # Check if profile already exists
    existing_profile = await db.execute(
        select(UserProfileDB).where(UserProfileDB.user_id == current_user_id)
    )
    if existing_profile.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile already exists"
        )
    
    # Create new profile
    profile = UserProfileDB(
        profile_id=str(uuid.uuid4()),
        user_id=current_user_id,
        display_name=profile_data.display_name,
        bio=profile_data.bio,
        location=profile_data.location,
        website=str(profile_data.website) if profile_data.website else None,
        favorite_teams=profile_data.favorite_teams,
        favorite_sports=profile_data.favorite_sports,
        profile_visibility=ProfileVisibilityEnum.PUBLIC,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    
    return _convert_profile_to_response(profile)

# PUBLIC_INTERFACE
@router.get("/me", response_model=UserProfileResponse, summary="Get current user's profile")
async def get_my_profile(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's own profile
    
    Returns complete profile information for the current user,
    including private settings and preferences.
    """
    result = await db.execute(
        select(UserProfileDB)
        .options(selectinload(UserProfileDB.user))
        .where(UserProfileDB.user_id == current_user_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return _convert_profile_to_response(profile)

# PUBLIC_INTERFACE
@router.put("/me", response_model=UserProfileResponse, summary="Update current user's profile")
async def update_my_profile(
    profile_update: UserProfileUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the authenticated user's profile
    
    Updates profile information, preferences, and privacy settings
    for the current user.
    """
    result = await db.execute(
        select(UserProfileDB).where(UserProfileDB.user_id == current_user_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Update fields
    if profile_update.display_name is not None:
        profile.display_name = profile_update.display_name
    if profile_update.bio is not None:
        profile.bio = profile_update.bio
    if profile_update.location is not None:
        profile.location = profile_update.location
    if profile_update.website is not None:
        profile.website = str(profile_update.website) if profile_update.website else None
    if profile_update.avatar_url is not None:
        profile.avatar_url = str(profile_update.avatar_url) if profile_update.avatar_url else None
    if profile_update.cover_image_url is not None:
        profile.cover_image_url = str(profile_update.cover_image_url) if profile_update.cover_image_url else None
    if profile_update.favorite_teams is not None:
        profile.favorite_teams = profile_update.favorite_teams
    if profile_update.favorite_sports is not None:
        profile.favorite_sports = profile_update.favorite_sports
    if profile_update.favorite_players is not None:
        profile.favorite_players = profile_update.favorite_players
    if profile_update.favorite_leagues is not None:
        profile.favorite_leagues = profile_update.favorite_leagues
    if profile_update.notification_preferences is not None:
        profile.notification_preferences = [pref.dict() for pref in profile_update.notification_preferences]
    if profile_update.profile_visibility is not None:
        profile.profile_visibility = ProfileVisibilityEnum(profile_update.profile_visibility.value)
    if profile_update.show_favorite_teams is not None:
        profile.show_favorite_teams = profile_update.show_favorite_teams
    if profile_update.show_activity is not None:
        profile.show_activity = profile_update.show_activity
    if profile_update.preferred_language is not None:
        profile.preferred_language = profile_update.preferred_language
    if profile_update.timezone is not None:
        profile.timezone = profile_update.timezone
        
    profile.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(profile)
    
    return _convert_profile_to_response(profile)

# PUBLIC_INTERFACE
@router.get("/{profile_id}", response_model=UserProfileResponse, summary="Get user profile by ID")
async def get_profile_by_id(
    profile_id: str,
    current_user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a user profile by profile ID
    
    Returns public profile information. Private profiles are only
    accessible to the profile owner.
    """
    result = await db.execute(
        select(UserProfileDB)
        .options(selectinload(UserProfileDB.user))
        .where(UserProfileDB.profile_id == profile_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Check privacy settings
    if profile.profile_visibility == ProfileVisibilityEnum.PRIVATE:
        if not current_user_id or current_user_id != profile.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Profile is private"
            )
    
    return _convert_profile_to_response(profile, is_own_profile=(current_user_id == profile.user_id))

# PUBLIC_INTERFACE
@router.get("/", response_model=List[UserProfileResponse], summary="Search user profiles")
async def search_profiles(
    q: Optional[str] = Query(None, description="Search query for display name or username"),
    favorite_sport: Optional[str] = Query(None, description="Filter by favorite sport"),
    location: Optional[str] = Query(None, description="Filter by location"),
    verified_only: bool = Query(False, description="Show only verified profiles"),
    limit: int = Query(20, ge=1, le=100, description="Number of profiles to return"),
    offset: int = Query(0, ge=0, description="Number of profiles to skip"),
    current_user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Search and filter user profiles
    
    Search for public user profiles with various filtering options
    including sport preferences, location, and verification status.
    """
    query = select(UserProfileDB).options(selectinload(UserProfileDB.user))
    
    # Only show public profiles to non-authenticated users
    if not current_user_id:
        query = query.where(UserProfileDB.profile_visibility == ProfileVisibilityEnum.PUBLIC)
    else:
        # Authenticated users can see public and friends profiles (simplified to public for now)
        query = query.where(
            UserProfileDB.profile_visibility.in_([ProfileVisibilityEnum.PUBLIC, ProfileVisibilityEnum.FRIENDS])
        )
    
    # Apply filters
    if q:
        query = query.join(UserDB).where(
            UserDB.username.ilike(f"%{q}%") | 
            UserProfileDB.display_name.ilike(f"%{q}%")
        )
    
    if favorite_sport:
        query = query.where(UserProfileDB.favorite_sports.contains([favorite_sport]))
    
    if location:
        query = query.where(UserProfileDB.location.ilike(f"%{location}%"))
    
    if verified_only:
        query = query.where(UserProfileDB.is_verified == True)
    
    # Apply pagination and ordering
    query = query.offset(offset).limit(limit).order_by(UserProfileDB.created_at.desc())
    
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    return [
        _convert_profile_to_response(profile, is_own_profile=(current_user_id == profile.user_id))
        for profile in profiles
    ]

# PUBLIC_INTERFACE
@router.delete("/me", summary="Delete current user's profile")
async def delete_my_profile(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete the authenticated user's profile
    
    Permanently deletes the user's profile data while keeping
    the user account intact.
    """
    result = await db.execute(
        select(UserProfileDB).where(UserProfileDB.user_id == current_user_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    await db.delete(profile)
    await db.commit()
    
    return {"message": "Profile deleted successfully"}

def _convert_profile_to_response(profile: UserProfileDB, is_own_profile: bool = False) -> UserProfileResponse:
    """Convert UserProfileDB to UserProfileResponse"""
    # Build notification preferences
    notification_prefs = []
    if profile.notification_preferences:
        from ..models.profile import NotificationPreference
        for pref_dict in profile.notification_preferences:
            notification_prefs.append(NotificationPreference(**pref_dict))
    
    return UserProfileResponse(
        profile_id=str(profile.profile_id),
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        bio=profile.bio,
        location=profile.location,
        website=profile.website,
        avatar_url=profile.avatar_url,
        cover_image_url=profile.cover_image_url,
        favorite_teams=profile.favorite_teams or [],
        favorite_sports=profile.favorite_sports or [],
        favorite_players=profile.favorite_players or [],
        favorite_leagues=profile.favorite_leagues or [],
        profile_visibility=profile.profile_visibility,
        total_reactions=profile.total_reactions,
        matches_watched=profile.matches_watched,
        highlights_watched=profile.highlights_watched,
        is_verified=profile.is_verified,
        preferred_language=profile.preferred_language,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )
