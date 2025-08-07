from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload
from datetime import datetime

from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user_id, optional_auth
from ..database.connection import get_db
from ..database.models import UserDB, UserProfileDB, UserRoleEnum
from ..database.schemas import convert_user_db_to_response
from ..database.repositories import UserRepository

router = APIRouter(prefix="/users", tags=["Users"])

# PUBLIC_INTERFACE
@router.get("/", response_model=List[UserResponse], summary="Get users")
async def get_users(
    q: Optional[str] = Query(None, description="Search query for username or full name"),
    role: Optional[str] = Query(None, description="Filter by user role"),
    active_only: bool = Query(True, description="Show only active users"),
    limit: int = Query(20, ge=1, le=100, description="Number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    current_user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of users
    
    Search and filter users by various criteria. Public endpoint
    with limited information for non-authenticated users.
    """
    query = select(UserDB).options(selectinload(UserDB.profile))
    
    # Apply filters
    conditions = []
    
    if active_only:
        conditions.append(UserDB.is_active == True)
    
    if role:
        try:
            role_enum = UserRoleEnum(role.lower())
            conditions.append(UserDB.role == role_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}"
            )
    
    if q:
        search_condition = or_(
            UserDB.username.ilike(f"%{q}%"),
            UserDB.full_name.ilike(f"%{q}%"),
            UserDB.email.ilike(f"%{q}%")
        )
        conditions.append(search_condition)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply pagination and ordering
    query = query.order_by(UserDB.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [convert_user_db_to_response(user) for user in users]

# PUBLIC_INTERFACE
@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user_by_id(
    user_id: str,
    current_user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific user by ID
    
    Returns public user information. Some details may be limited
    for non-authenticated users.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return convert_user_db_to_response(user)

# PUBLIC_INTERFACE
@router.get("/username/{username}", response_model=UserResponse, summary="Get user by username")
async def get_user_by_username(
    username: str,
    current_user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific user by username
    
    Returns public user information for the specified username.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_username(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return convert_user_db_to_response(user)

# PUBLIC_INTERFACE
@router.get("/search/suggestions", response_model=List[dict], summary="Get user search suggestions")
async def get_user_suggestions(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions to return"),
    current_user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user search suggestions
    
    Returns a list of user suggestions based on username and display name
    for autocomplete functionality.
    """
    query = select(UserDB, UserProfileDB).options(
        selectinload(UserDB.profile)
    ).outerjoin(UserProfileDB).where(
        and_(
            UserDB.is_active == True,
            or_(
                UserDB.username.ilike(f"%{q}%"),
                UserDB.full_name.ilike(f"%{q}%"),
                UserProfileDB.display_name.ilike(f"%{q}%")
            )
        )
    ).limit(limit)
    
    result = await db.execute(query)
    users = [row[0] for row in result]
    
    suggestions = []
    for user in users:
        profile = user.profile if hasattr(user, 'profile') and user.profile else None
        
        suggestion = {
            "user_id": str(user.user_id),
            "username": user.username,
            "full_name": user.full_name,
            "display_name": profile.display_name if profile else None,
            "avatar_url": user.avatar_url or (profile.avatar_url if profile else None),
            "is_verified": profile.is_verified if profile else False
        }
        suggestions.append(suggestion)
    
    return suggestions

# PUBLIC_INTERFACE
@router.get("/stats/overview", response_model=dict, summary="Get user statistics overview")
async def get_user_stats(
    current_user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user statistics overview
    
    Returns general statistics about the user base including
    total users, active users, and role distribution.
    """
    # Total users
    total_result = await db.execute(select(func.count()).select_from(UserDB))
    total_users = total_result.scalar()
    
    # Active users
    active_result = await db.execute(
        select(func.count()).select_from(UserDB).where(UserDB.is_active == True)
    )
    active_users = active_result.scalar()
    
    # New users this week
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_result = await db.execute(
        select(func.count()).select_from(UserDB).where(
            and_(
                UserDB.created_at >= week_ago,
                UserDB.is_active == True
            )
        )
    )
    new_users_this_week = new_result.scalar()
    
    # Users with profiles
    profiles_result = await db.execute(select(func.count()).select_from(UserProfileDB))
    users_with_profiles = profiles_result.scalar()
    
    # Role distribution
    roles_result = await db.execute(
        select(UserDB.role, func.count()).group_by(UserDB.role)
    )
    role_distribution = {}
    for role, count in roles_result:
        role_distribution[role.value] = count
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "new_users_this_week": new_users_this_week,
        "users_with_profiles": users_with_profiles,
        "role_distribution": role_distribution,
        "profile_completion_rate": round((users_with_profiles / max(total_users, 1)) * 100, 1)
    }

# PUBLIC_INTERFACE  
@router.put("/{user_id}/activate", response_model=UserResponse, summary="Activate user account")
async def activate_user(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate a user account
    
    Admin-only endpoint to activate a deactivated user account.
    """
    # Check if current user has admin permissions
    current_user = await db.execute(
        select(UserDB).where(UserDB.user_id == current_user_id)
    )
    current_user_obj = current_user.scalar_one_or_none()
    
    if not current_user_obj or current_user_obj.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Find and activate user
    result = await db.execute(
        select(UserDB).where(UserDB.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user)
    
    return convert_user_db_to_response(user)

# PUBLIC_INTERFACE
@router.put("/{user_id}/deactivate", response_model=UserResponse, summary="Deactivate user account")
async def deactivate_user(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a user account
    
    Admin-only endpoint to deactivate a user account. Users can also
    deactivate their own accounts.
    """
    # Check permissions (admin or self)
    current_user = await db.execute(
        select(UserDB).where(UserDB.user_id == current_user_id)
    )
    current_user_obj = current_user.scalar_one_or_none()
    
    if not current_user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current user not found"
        )
    
    # Allow if admin or user deactivating their own account
    if current_user_obj.role != UserRoleEnum.ADMIN and current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only deactivate your own account or need admin access"
        )
    
    # Find and deactivate user
    result = await db.execute(
        select(UserDB).where(UserDB.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user)
    
    return convert_user_db_to_response(user)
