"""
Database repository layer for Sports Telecast Backend

This module provides repository classes that encapsulate database operations
and provide a clean interface for business logic layers.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import uuid

from .models import (
    UserDB, EventDB, MatchDB, 
    EmojiAssetDB, UserEmojiReactionDB, HighlightDB, UserProfileDB,
    SportTypeEnum, MatchStatusEnum, UserRoleEnum, ProfileVisibilityEnum
)
from ..models.user import UserCreate, UserUpdate
from ..models.profile import UserProfileCreate, UserProfileUpdate
from ..models.match import SportType, MatchStatus

class BaseRepository:
    """Base repository with common database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session

class UserRepository(BaseRepository):
    """Repository for user operations

    Note:
        The backend expects the database 'users' table to include a JSON/JSONB column
        named 'preferences'. This is provisioned by the DB container migrations
        (e.g., 013_add_users_preferences_column.sql) and not by backend Alembic.
        Ensure DB migrations are applied before using registration APIs.

    Role normalization:
        All roles are stored as lowercase values in the DB enum ('user','admin','moderator').
        Any inbound value is coerced to a valid enum with lowercase value before persistence.
    """

    def _normalize_role(self, value: Optional[str]) -> UserRoleEnum:
        """
        Coerce arbitrary role input to the proper UserRoleEnum with lowercase value.
        Defaults to UserRoleEnum.USER if invalid or None.
        """
        if not value:
            return UserRoleEnum.USER
        try:
            lower = str(value).lower()
            for member in UserRoleEnum:
                if member.value == lower:
                    return member
        except Exception:
            pass
        return UserRoleEnum.USER
    
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
        # Normalize role to ensure lowercase-backed enum; default to USER for new registrations
        normalized_role = self._normalize_role(getattr(user_data, "role", None))

        # Log the exact data that will be used to create the UserDB record
        # Avoid logging sensitive raw password; log only the presence of a hash (length) for debugging.
        input_payload = {
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name,
            "incoming_role": getattr(user_data, "role", None),
            "normalized_role": normalized_role.value if hasattr(normalized_role, "value") else str(normalized_role),
            "is_active": True,
            "preferences": {},
            "password_hash_len": len(password_hash) if isinstance(password_hash, str) else None,
        }
        print("Creating UserDB with data:", input_payload)

        user = UserDB(
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
            full_name=user_data.full_name,
            role=normalized_role,
            is_active=True,
            preferences={},  # requires users.preferences column (JSON/JSONB)
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
            bio=profile_data.bio,
            location=profile_data.location,
            website=str(profile_data.website) if profile_data.website else None,
            favorite_teams=profile_data.favorite_teams,
            favorite_sports=profile_data.favorite_sports,
            profile_visibility=ProfileVisibilityEnum.PUBLIC,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
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
            
        # Update fields that are not None
        for field_name, value in profile_data.dict(exclude_unset=True).items():
            if value is not None:
                if field_name in ['website', 'avatar_url', 'cover_image_url'] and value:
                    setattr(profile, field_name, str(value))
                else:
                    setattr(profile, field_name, value)
                    
        profile.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

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
    
    # PUBLIC_INTERFACE
    async def get_more_matches(self, limit: int = 12, offset: int = 0, exclude_ids: List[str] = None) -> List[MatchDB]:
        """Get additional matches for 'more matches' section with variety"""
        if exclude_ids is None:
            exclude_ids = []
        
        # Build base query with exclusions
        base_query = select(MatchDB).options(
            selectinload(MatchDB.home_team),
            selectinload(MatchDB.away_team),
            selectinload(MatchDB.event)
        )
        
        if exclude_ids:
            base_query = base_query.where(~MatchDB.match_id.in_(exclude_ids))
        
        # Get a mix of different match types
        matches = []
        
        # 1. Live matches (highest priority)
        live_result = await self.session.execute(
            base_query.where(MatchDB.status == MatchStatusEnum.LIVE)
            .order_by(desc(MatchDB.start_time))
            .limit(3)
        )
        matches.extend(live_result.scalars().all())
        
        # 2. Recent finished matches (within last 7 days)
        recent_finished_result = await self.session.execute(
            base_query.where(
                and_(
                    MatchDB.status == MatchStatusEnum.FINISHED,
                    MatchDB.start_time >= datetime.utcnow() - timedelta(days=7)
                )
            )
            .order_by(desc(MatchDB.start_time))
            .limit(4)
        )
        matches.extend(recent_finished_result.scalars().all())
        
        # 3. Upcoming matches (next 7 days)
        upcoming_result = await self.session.execute(
            base_query.where(
                and_(
                    MatchDB.status == MatchStatusEnum.SCHEDULED,
                    MatchDB.start_time >= datetime.utcnow(),
                    MatchDB.start_time <= datetime.utcnow() + timedelta(days=7)
                )
            )
            .order_by(MatchDB.start_time)
            .limit(4)
        )
        matches.extend(upcoming_result.scalars().all())
        
        # 4. Fill remaining spots with any other matches
        if len(matches) < limit:
            existing_ids = [m.match_id for m in matches] + exclude_ids
            additional_result = await self.session.execute(
                base_query.where(~MatchDB.match_id.in_(existing_ids))
                .order_by(desc(MatchDB.start_time))
                .limit(limit - len(matches))
            )
            matches.extend(additional_result.scalars().all())
        
        # Remove duplicates and apply pagination
        unique_matches = {}
        for match in matches:
            if match.match_id not in unique_matches:
                unique_matches[match.match_id] = match
        
        final_matches = list(unique_matches.values())[offset:offset + limit]
        return final_matches

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
    async def get_emojis(self, limit: int = 10, offset: int = 0):
        """
        Get paginated list of active emojis.

        Returns:
            List[EmojiAssetDB] in normal schema, or a list[dict]-like fallback rows for minimal schema.
        """
        try:
            result = await self.session.execute(
                select(EmojiAssetDB)
                .where(EmojiAssetDB.is_active == True)  # noqa: E712
                .order_by(EmojiAssetDB.sort_order)
                .offset(offset)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception:
            # Fallback path for databases missing full emoji_assets columns (e.g., image_url, name, etc.)
            # Select minimal available fields to avoid referencing non-existent columns.
            fallback_sql = text(
                """
                SELECT
                    emoji_id::text AS emoji_id,
                    emoji_type::text AS emoji_type,
                    file_location,
                    created_at
                FROM emoji_assets
                ORDER BY created_at DESC
                OFFSET :offset LIMIT :limit
                """
            )
            result = await self.session.execute(fallback_sql, {"offset": offset, "limit": limit})
            # Return list of dict mappings to be handled by convert_emoji_db_to_pydantic
            return [dict(row) for row in result.mappings().all()]
    
    # PUBLIC_INTERFACE
    async def get_emoji_by_id(self, emoji_id: str) -> Optional[EmojiAssetDB]:
        """Get emoji by ID"""
        result = await self.session.execute(
            select(EmojiAssetDB).where(EmojiAssetDB.emoji_id == emoji_id)
        )
        return result.scalar_one_or_none()
    
    # PUBLIC_INTERFACE
    async def add_reaction(self, user_id: str, event_id: str, emoji_id: str, created_at: Optional[datetime] = None) -> str:
        """
        Add emoji reaction.
        
        Args:
            user_id: ID of the reacting user
            event_id: ID of the event/match
            emoji_id: ID of the emoji
            created_at: Explicit timestamp for the reaction (if provided by client)
        Returns:
            Newly created reaction_id
        """
        reaction_id = str(uuid.uuid4())
        reaction = UserEmojiReactionDB(
            reaction_id=reaction_id,
            user_id=user_id,
            event_id=event_id,
            emoji_id=emoji_id,
            created_at=created_at or datetime.utcnow(),
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
