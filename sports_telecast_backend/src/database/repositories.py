"""
Database repository layer for Sports Telecast Backend

This module provides repository classes that encapsulate database operations
and provide a clean interface for business logic layers.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import uuid

from .models import (
    UserDB, EventDB, MatchDB, 
    HighlightDB, UserProfileDB
)
from ..models.user import UserCreate, UserUpdate
from ..models.profile import UserProfileCreate, UserProfileUpdate
from ..models.match import MatchStatus

class BaseRepository:
    """Base repository with common database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session

class UserRepository(BaseRepository):
    """Repository for user operations"""
    
    # PUBLIC_INTERFACE
    async def create_user(self, user_data: UserCreate, password_hash: str) -> UserDB:
        """
        Create a new user in the database using minimal schema (id, email, username, password_hash).

        Args:
            user_data: User creation data (email, username, password required)
            password_hash: Hashed password

        Returns:
            UserDB: Created user record
        """
        user = UserDB(
            id=str(uuid.uuid4()),
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    # PUBLIC_INTERFACE
    async def get_user_by_id(self, user_id: str) -> Optional[UserDB]:
        """Get user by ID"""
        result = await self.session.execute(
            select(UserDB).where(UserDB.id == user_id)
        )
        return result.scalar_one_or_none()
    
    # PUBLIC_INTERFACE
    async def get_user_by_email(self, email: str) -> Optional[UserDB]:
        """Get user by email"""
        result = await self.session.execute(
            select(UserDB).where(UserDB.email == email)
        )
        return result.scalar_one_or_none()
    
    # PUBLIC_INTERFACE
    async def get_user_by_username(self, username: str) -> Optional[UserDB]:
        """Get user by username"""
        result = await self.session.execute(
            select(UserDB).where(UserDB.username == username)
        )
        return result.scalar_one_or_none()
    
    # PUBLIC_INTERFACE
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[UserDB]:
        """Update user information"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
            
        if user_data.username is not None:
            user.username = user_data.username
            
        await self.session.commit()
        await self.session.refresh(user)
        return user

class UserProfileRepository(BaseRepository):
    """Repository for user profile operations"""
    
    # PUBLIC_INTERFACE
    async def create_profile(self, profile_data: UserProfileCreate) -> UserProfileDB:
        """
        Create a new user profile
        
        Args:
            profile_data: Profile creation data
            
        Returns:
            UserProfileDB: Created profile record
        """
        profile = UserProfileDB(
            profile_id=str(uuid.uuid4()),
            user_id=profile_data.user_id,
            display_name=profile_data.display_name,
            avatar_url=profile_data.avatar_url
        )
        
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile
    
    # PUBLIC_INTERFACE
    async def get_profile_by_user_id(self, user_id: str) -> Optional[UserProfileDB]:
        """Get profile by user ID"""
        result = await self.session.execute(
            select(UserProfileDB).where(UserProfileDB.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    # PUBLIC_INTERFACE
    async def get_profile_by_id(self, profile_id: str) -> Optional[UserProfileDB]:
        """Get profile by profile ID"""
        result = await self.session.execute(
            select(UserProfileDB).where(UserProfileDB.profile_id == profile_id)
        )
        return result.scalar_one_or_none()
    
    # PUBLIC_INTERFACE
    async def update_profile(self, profile_id: str, profile_data: UserProfileUpdate) -> Optional[UserProfileDB]:
        """Update profile information"""
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            return None
            
        if profile_data.display_name is not None:
            profile.display_name = profile_data.display_name
        if profile_data.avatar_url is not None:
            profile.avatar_url = profile_data.avatar_url
            
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

class MatchRepository(BaseRepository):
    """Repository for match operations"""
    
    # PUBLIC_INTERFACE
    async def get_matches(self, 
                         limit: int = 20, 
                         offset: int = 0,
                         status: Optional[MatchStatus] = None) -> List[MatchDB]:
        """Get paginated list of matches with optional filtering"""
        query = select(MatchDB).options(
            selectinload(MatchDB.home_team),
            selectinload(MatchDB.away_team),
            selectinload(MatchDB.event)
        )
        
        if status:
            query = query.where(MatchDB.status == status.value)
            
        query = query.order_by(desc(MatchDB.start_time)).offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # PUBLIC_INTERFACE
    async def get_match_by_id(self, match_id: str) -> Optional[MatchDB]:
        """Get match by ID with related data"""
        result = await self.session.execute(
            select(MatchDB)
            .options(
                selectinload(MatchDB.home_team),
                selectinload(MatchDB.away_team),
                selectinload(MatchDB.event)
            )
            .where(MatchDB.match_id == match_id)
        )
        return result.scalar_one_or_none()
    
    # PUBLIC_INTERFACE
    async def get_live_matches(self) -> List[MatchDB]:
        """Get all currently live matches"""
        result = await self.session.execute(
            select(MatchDB)
            .options(
                selectinload(MatchDB.home_team),
                selectinload(MatchDB.away_team),
                selectinload(MatchDB.event)
            )
            .where(MatchDB.status == "live")
        )
        return result.scalars().all()
    
    # PUBLIC_INTERFACE
    async def get_upcoming_matches(self, days: int = 7, limit: int = 20, offset: int = 0) -> List[MatchDB]:
        """Get upcoming matches within specified days"""
        end_date = datetime.utcnow() + timedelta(days=days)
        
        result = await self.session.execute(
            select(MatchDB)
            .options(
                selectinload(MatchDB.home_team),
                selectinload(MatchDB.away_team),
                selectinload(MatchDB.event)
            )
            .where(
                and_(
                    MatchDB.status == "scheduled",
                    MatchDB.start_time >= datetime.utcnow(),
                    MatchDB.start_time <= end_date
                )
            )
            .order_by(MatchDB.start_time)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    # PUBLIC_INTERFACE
    async def get_matches_by_event_id(self, event_id: str, limit: int = 20, offset: int = 0) -> List[MatchDB]:
        """Get matches for a specific event"""
        query = select(MatchDB).options(
            selectinload(MatchDB.home_team),
            selectinload(MatchDB.away_team),
            selectinload(MatchDB.event)
        ).where(MatchDB.event_id == event_id)
            
        query = query.order_by(desc(MatchDB.start_time)).offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # PUBLIC_INTERFACE
    async def get_total_matches_count(self, status: Optional[MatchStatus] = None) -> int:
        """Get total count of matches with optional filtering"""
        query = select(func.count(MatchDB.match_id))
        
        if status:
            query = query.where(MatchDB.status == status.value)
        
        result = await self.session.execute(query)
        return result.scalar() or 0

class EventRepository(BaseRepository):
    """Repository for event operations"""
    
    # PUBLIC_INTERFACE
    async def get_events(self, 
                        limit: int = 20, 
                        offset: int = 0,
                        sport_type: Optional[str] = None) -> List[EventDB]:
        """Get paginated list of events with optional filtering"""
        query = select(EventDB)
        
        if sport_type:
            query = query.where(EventDB.sport_type == sport_type)
            
        query = query.order_by(desc(EventDB.start_date)).offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # PUBLIC_INTERFACE
    async def get_event_by_id(self, event_id: str) -> Optional[EventDB]:
        """Get event by ID with matches"""
        result = await self.session.execute(
            select(EventDB)
            .options(selectinload(EventDB.matches))
            .where(EventDB.event_id == event_id)
        )
        return result.scalar_one_or_none()

class HighlightRepository(BaseRepository):
    """Repository for highlight operations"""
    
    # PUBLIC_INTERFACE
    async def get_highlights(self, 
                           limit: int = 20, 
                           offset: int = 0,
                           match_id: Optional[str] = None) -> List[HighlightDB]:
        """Get paginated list of highlights"""
        query = select(HighlightDB).options(selectinload(HighlightDB.match))
        
        if match_id:
            query = query.where(HighlightDB.match_id == match_id)
            
        query = query.order_by(desc(HighlightDB.created_at)).offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # PUBLIC_INTERFACE
    async def get_highlight_by_id(self, highlight_id: str) -> Optional[HighlightDB]:
        """Get highlight by ID"""
        result = await self.session.execute(
            select(HighlightDB)
            .options(selectinload(HighlightDB.match))
            .where(HighlightDB.highlight_id == highlight_id)
        )
        return result.scalar_one_or_none()
