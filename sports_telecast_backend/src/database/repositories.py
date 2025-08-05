"""
Database repository layer for Sports Telecast Backend

This module provides repository classes that encapsulate database operations
and provide a clean interface for business logic layers.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import uuid

from .models import (
    UserDB, EventDB, MatchDB, 
    EmojiAssetDB, UserEmojiReactionDB, HighlightDB,
    SportTypeEnum, MatchStatusEnum, UserRoleEnum
)
from models.user import UserCreate, UserUpdate
from models.match import SportType, MatchStatus

class BaseRepository:
    """Base repository with common database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session

class UserRepository(BaseRepository):
    """Repository for user operations"""
    
    # PUBLIC_INTERFACE
    async def create_user(self, user_data: UserCreate, password_hash: str) -> UserDB:
        """
        Create a new user in the database
        
        Args:
            user_data: User creation data
            password_hash: Hashed password
            
        Returns:
            UserDB: Created user record
        """
        user = UserDB(
            user_id=str(uuid.uuid4()),
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
            full_name=user_data.full_name,
            role=UserRoleEnum.USER,
            is_active=True,
            preferences={}
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    # PUBLIC_INTERFACE
    async def get_user_by_id(self, user_id: str) -> Optional[UserDB]:
        """Get user by ID"""
        result = await self.session.execute(
            select(UserDB).where(UserDB.user_id == user_id)
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
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.avatar_url is not None:
            user.avatar_url = user_data.avatar_url
        if user_data.preferences is not None:
            user.preferences = user_data.preferences.dict() if user_data.preferences else {}
            
        user.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(user)
        return user

class MatchRepository(BaseRepository):
    """Repository for match operations"""
    
    # PUBLIC_INTERFACE
    async def get_matches(self, 
                         limit: int = 20, 
                         offset: int = 0,
                         status: Optional[MatchStatus] = None,
                         sport: Optional[SportType] = None) -> List[MatchDB]:
        """Get paginated list of matches with optional filtering"""
        query = select(MatchDB).options(
            selectinload(MatchDB.home_team),
            selectinload(MatchDB.away_team),
            selectinload(MatchDB.event)
        )
        
        if status:
            query = query.where(MatchDB.status == MatchStatusEnum(status.value))
        if sport:
            query = query.where(MatchDB.sport_type == SportTypeEnum(sport.value))
            
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
                selectinload(MatchDB.event),
                selectinload(MatchDB.match_events)
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
            .where(MatchDB.status == MatchStatusEnum.LIVE)
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
                    MatchDB.status == MatchStatusEnum.SCHEDULED,
                    MatchDB.start_time >= datetime.utcnow(),
                    MatchDB.start_time <= end_date
                )
            )
            .order_by(MatchDB.start_time)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

class EventRepository(BaseRepository):
    """Repository for event operations"""
    
    # PUBLIC_INTERFACE
    async def get_events(self, 
                        limit: int = 20, 
                        offset: int = 0,
                        sport: Optional[SportType] = None,
                        featured: Optional[bool] = None) -> List[EventDB]:
        """Get paginated list of events with optional filtering"""
        query = select(EventDB)
        
        if sport:
            query = query.where(EventDB.sport_type == SportTypeEnum(sport.value))
        if featured is not None:
            query = query.where(EventDB.is_featured == featured)
            
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

class EmojiRepository(BaseRepository):
    """Repository for emoji operations"""
    
    # PUBLIC_INTERFACE
    async def get_emojis(self, limit: int = 10, offset: int = 0) -> List[EmojiAssetDB]:
        """Get paginated list of active emojis"""
        result = await self.session.execute(
            select(EmojiAssetDB)
            .where(EmojiAssetDB.is_active == True)
            .order_by(EmojiAssetDB.sort_order)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()
    
    # PUBLIC_INTERFACE
    async def get_emoji_by_id(self, emoji_id: str) -> Optional[EmojiAssetDB]:
        """Get emoji by ID"""
        result = await self.session.execute(
            select(EmojiAssetDB).where(EmojiAssetDB.emoji_id == emoji_id)
        )
        return result.scalar_one_or_none()
    
    # PUBLIC_INTERFACE
    async def add_reaction(self, user_id: str, event_id: str, emoji_id: str) -> str:
        """Add emoji reaction"""
        reaction_id = str(uuid.uuid4())
        reaction = UserEmojiReactionDB(
            reaction_id=reaction_id,
            user_id=user_id,
            event_id=event_id,
            emoji_id=emoji_id
        )
        
        self.session.add(reaction)
        await self.session.commit()
        return reaction_id
    
    # PUBLIC_INTERFACE
    async def get_reaction_summary(self, event_id: str) -> Dict[str, Any]:
        """Get emoji reaction summary for an event"""
        # Get reaction counts
        result = await self.session.execute(
            select(
                UserEmojiReactionDB.emoji_id,
                func.count(UserEmojiReactionDB.reaction_id).label('count')
            )
            .where(UserEmojiReactionDB.event_id == event_id)
            .group_by(UserEmojiReactionDB.emoji_id)
        )
        
        emoji_counts = {}
        total_reactions = 0
        
        for row in result:
            emoji_counts[row.emoji_id] = row.count
            total_reactions += row.count
        
        # Get top emojis with details
        top_emojis = []
        if emoji_counts:
            emoji_ids = list(emoji_counts.keys())
            emoji_result = await self.session.execute(
                select(EmojiAssetDB)
                .where(EmojiAssetDB.emoji_id.in_(emoji_ids))
            )
            
            emojis = {emoji.emoji_id: emoji for emoji in emoji_result.scalars().all()}
            
            # Sort by count and get top 5
            sorted_counts = sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for emoji_id, count in sorted_counts:
                if emoji_id in emojis:
                    emoji = emojis[emoji_id]
                    top_emojis.append({
                        "emoji_id": emoji_id,
                        "emoji_type": emoji.emoji_type.value,
                        "count": count,
                        "image_url": emoji.image_url
                    })
        
        return {
            "event_id": event_id,
            "emoji_counts": emoji_counts,
            "total_reactions": total_reactions,
            "top_emojis": top_emojis,
            "last_updated": datetime.utcnow()
        }

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
    
    # PUBLIC_INTERFACE
    async def get_featured_highlights(self, limit: int = 10) -> List[HighlightDB]:
        """Get featured highlights (most recent and popular)"""
        result = await self.session.execute(
            select(HighlightDB)
            .options(selectinload(HighlightDB.match))
            .order_by(desc(HighlightDB.view_count), desc(HighlightDB.created_at))
            .limit(limit)
        )
        return result.scalars().all()
