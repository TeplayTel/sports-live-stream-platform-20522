from fastapi import APIRouter, HTTPException, status, Query, Body, Request
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.profile import (
    UserProfileCreate, UserProfileUpdate, UserProfileResponse
)
from ..database.connection import get_db
from ..database.models import UserProfileDB, UserDB, ProfileVisibilityEnum
from datetime import datetime
import uuid
from .utils import get_trusted_user

router = APIRouter(prefix="/profiles", tags=["User Profiles"])

# PUBLIC_INTERFACE
@router.post("/", response_model=UserProfileResponse, summary="Create user profile")
async def create_user_profile(
    profile_data: UserProfileCreate = Body(...),
    request: Request = None,
    db: AsyncSession = None
):
    """
    Create a new user profile.
    Accepts userId from headers, params, or body ("mock login").
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    # If not present in body, inject
    pdict = profile_data.dict()
    if not pdict.get("user_id"):
        pdict["user_id"] = user_id
    # Check if profile already exists
    existing_profile = await db.execute(
        select(UserProfileDB).where(UserProfileDB.user_id == pdict["user_id"])
    )
    if existing_profile.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User profile already exists")
    profile = UserProfileDB(
        profile_id=str(uuid.uuid4()),
        user_id=pdict["user_id"],
        display_name=pdict.get("display_name"),
        bio=pdict.get("bio"),
        location=pdict.get("location"),
        website=str(pdict["website"]) if pdict.get("website") else None,
        favorite_teams=pdict.get("favorite_teams"),
        favorite_sports=pdict.get("favorite_sports"),
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
async def get_my_profile(request: Request = None, db: AsyncSession = None):
    """
    Get the trusted/mock current user's own profile.
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    result = await db.execute(
        select(UserProfileDB)
        .options(selectinload(UserProfileDB.user))
        .where(UserProfileDB.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return _convert_profile_to_response(profile)

# PUBLIC_INTERFACE
@router.put("/me", response_model=UserProfileResponse, summary="Update current user's profile")
async def update_my_profile(
    profile_update: UserProfileUpdate = Body(...),
    request: Request = None,
    db: AsyncSession = None
):
    """
    Update the trusted/mock current user's profile.
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    result = await db.execute(
        select(UserProfileDB).where(UserProfileDB.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    # Update fields if provided
    for attr, value in profile_update.dict(exclude_unset=True).items():
        setattr(profile, attr, value)
    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(profile)
    return _convert_profile_to_response(profile)

# PUBLIC_INTERFACE
@router.get("/{profile_id}", response_model=UserProfileResponse, summary="Get user profile by ID")
async def get_profile_by_id(
    profile_id: str,
    request: Request = None,
    db: AsyncSession = None
):
    """
    Get a user profile by profile ID.
    Accepts current user from trusted frontend header if owner check is needed.
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    result = await db.execute(
        select(UserProfileDB)
        .options(selectinload(UserProfileDB.user))
        .where(UserProfileDB.profile_id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    # PRIVATE profiles only viewable by owner
    if profile.profile_visibility == ProfileVisibilityEnum.PRIVATE and user_id != profile.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile is private")
    return _convert_profile_to_response(profile, is_own_profile=(user_id == profile.user_id))

# PUBLIC_INTERFACE
@router.get("/", response_model=List[UserProfileResponse], summary="Search user profiles")
async def search_profiles(
    q: Optional[str] = Query(None, description="Search query for display name or username"),
    favorite_sport: Optional[str] = Query(None, description="Filter by favorite sport"),
    location: Optional[str] = Query(None, description="Filter by location"),
    verified_only: bool = Query(False, description="Show only verified profiles"),
    limit: int = Query(20, ge=1, le=100, description="Number of profiles to return"),
    offset: int = Query(0, ge=0, description="Number of profiles to skip"),
    request: Request = None,
    db: AsyncSession = None
):
    """
    Search user profiles. Accepts mock user via trusted input but not required.
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    query = select(UserProfileDB).options(selectinload(UserProfileDB.user))
    # Only show public profiles to non-authenticated users
    from ..database.models import ProfileVisibilityEnum
    if not user_id:
        query = query.where(UserProfileDB.profile_visibility == ProfileVisibilityEnum.PUBLIC)
    else:
        query = query.where(UserProfileDB.profile_visibility.in_([ProfileVisibilityEnum.PUBLIC, ProfileVisibilityEnum.FRIENDS]))
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
    query = query.offset(offset).limit(limit).order_by(UserProfileDB.created_at.desc())
    result = await db.execute(query)
    profiles = result.scalars().all()
    return [
        _convert_profile_to_response(profile, is_own_profile=(user_id == profile.user_id))
        for profile in profiles
    ]

# PUBLIC_INTERFACE
@router.delete("/me", summary="Delete current user's profile")
async def delete_my_profile(
    request: Request = None,
    db: AsyncSession = None
):
    """
    Delete the trusted/mock current user's profile.
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    result = await db.execute(
        select(UserProfileDB).where(UserProfileDB.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    await db.delete(profile)
    await db.commit()
    return {"message": "Profile deleted successfully"}

def _convert_profile_to_response(profile: UserProfileDB, is_own_profile: bool = False) -> UserProfileResponse:
    """Convert UserProfileDB to UserProfileResponse"""
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
