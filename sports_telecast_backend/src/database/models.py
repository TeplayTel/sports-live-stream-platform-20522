from typing import Optional, List
from sqlalchemy import String, DateTime, Boolean, Integer, Text, JSON, ForeignKey, Enum as SQLEnum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid as uuid_pkg
import enum

from .connection import Base

# Enum definitions
class SportTypeEnum(enum.Enum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    CRICKET = "cricket"
    RUGBY = "rugby"
    HOCKEY = "hockey"
    BASEBALL = "baseball"

class MatchStatusEnum(enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"

class UserRoleEnum(enum.Enum):
    """User role enumeration stored as lowercase strings to match DB enum userroleenum.
    IMPORTANT: Values must remain lowercase to maintain compatibility with API and seeds."""
    USER = "user"      # lowercase values to match DB
    ADMIN = "admin" 
    MODERATOR = "moderator"

class EmojiTypeEnum(enum.Enum):
    CLAP = "clap"
    FIRE = "fire"
    HEART = "heart"
    THUMBS_UP = "thumbs_up"
    CELEBRATION = "celebration"
    SHOCKED = "shocked"
    ANGRY = "angry"
    SAD = "sad"
    LAUGH = "laugh"
    GOAL = "goal"

# Database Models
class UserDB(Base):
    __tablename__ = "users"

    # NOTE FOR MAINTAINERS:
    # We intentionally store 'role' as a String(32) with a SQL CHECK constraint rather than a native DB Enum.
    # Rationale:
    #   - Avoids coupling to PostgreSQL enum type management across environments/migrations.
    #   - Keeps values human-readable and compatible with OpenAPI ('user' | 'admin' | 'moderator').
    # Validation:
    #   - A database-level CHECK constraint enforces allowed values.
    #   - Application code should continue to normalize role to lowercase strings.
    # Migration:
    #   - Ensure Alembic migration updates existing column/type and adds the CHECK constraint if needed.

    user_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Store as string with check constraint, default 'user'
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="user"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Table-level constraints
    __table_args__ = (
        # Only allow these three lowercase values
        CheckConstraint(
            "role IN ('user','admin','moderator')",
            name="ck_users_role_valid_values"
        ),
    )

    # Relationships
    emoji_reactions: Mapped[List["UserEmojiReactionDB"]] = relationship("UserEmojiReactionDB", back_populates="user")
    profile: Mapped[Optional["UserProfileDB"]] = relationship("UserProfileDB", back_populates="user", uselist=False)

class TeamDB(Base):
    __tablename__ = "teams"
    
    team_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(10), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    colors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    home_matches: Mapped[List["MatchDB"]] = relationship("MatchDB", foreign_keys="MatchDB.home_team_id", back_populates="home_team")
    away_matches: Mapped[List["MatchDB"]] = relationship("MatchDB", foreign_keys="MatchDB.away_team_id", back_populates="away_team")

class EventDB(Base):
    __tablename__ = "events"
    
    event_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sport_type: Mapped[SportTypeEnum] = mapped_column(
        SQLEnum(SportTypeEnum, name="sporttypeenum", native_enum=True, create_type=False),
        nullable=False
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    organizer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    matches: Mapped[List["MatchDB"]] = relationship("MatchDB", back_populates="event")

class MatchDB(Base):
    __tablename__ = "matches"
    
    match_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    event_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.event_id"), nullable=False)
    home_team_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False)
    away_team_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False)
    sport_type: Mapped[SportTypeEnum] = mapped_column(
        SQLEnum(SportTypeEnum, name="sporttypeenum", native_enum=True, create_type=False),
        nullable=False
    )
    status: Mapped[MatchStatusEnum] = mapped_column(
        SQLEnum(MatchStatusEnum, name="matchstatusenum", native_enum=True, create_type=False),
        default=MatchStatusEnum.SCHEDULED
    )
    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)
    period_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    competition: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    round: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stream_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    event: Mapped["EventDB"] = relationship("EventDB", back_populates="matches")
    home_team: Mapped["TeamDB"] = relationship("TeamDB", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped["TeamDB"] = relationship("TeamDB", foreign_keys=[away_team_id], back_populates="away_matches")
    match_events: Mapped[List["MatchEventDB"]] = relationship("MatchEventDB", back_populates="match")
    highlights: Mapped[List["HighlightDB"]] = relationship("HighlightDB", back_populates="match")
    schedules: Mapped[List["ScheduleDB"]] = relationship("ScheduleDB", secondary="schedule_matches", back_populates="matches")

class MatchEventDB(Base):
    __tablename__ = "match_events"
    
    event_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    match_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.match_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    team_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    match: Mapped["MatchDB"] = relationship("MatchDB", back_populates="match_events")

class EmojiAssetDB(Base):
    __tablename__ = "emoji_assets"
    
    emoji_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    emoji_type: Mapped[EmojiTypeEnum] = mapped_column(
        SQLEnum(EmojiTypeEnum, name="emojitypeenum", native_enum=True, create_type=False),
        nullable=False
    )
    # Note: image_url is introduced by Alembic revision 005 as a nullable column with best-effort backfill.
    # Keep this column nullable at the ORM level to avoid transaction commit failures when legacy rows exist
    # without a resolvable file_location. A later migration can enforce NOT NULL after data cleanup.
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    reactions: Mapped[List["UserEmojiReactionDB"]] = relationship("UserEmojiReactionDB", back_populates="emoji")

class UserEmojiReactionDB(Base):
    __tablename__ = "user_emoji_reactions"
    
    reaction_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    user_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    event_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    emoji_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("emoji_assets.emoji_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="emoji_reactions")
    emoji: Mapped["EmojiAssetDB"] = relationship("EmojiAssetDB", back_populates="reactions")

class HighlightDB(Base):
    __tablename__ = "highlights"
    
    highlight_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    match_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.match_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    match: Mapped["MatchDB"] = relationship("MatchDB", back_populates="highlights")

class ProfileVisibilityEnum(enum.Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class UserProfileDB(Base):
    __tablename__ = "user_profiles"
    
    profile_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    user_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Sports preferences (stored as JSON arrays)
    favorite_teams: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    favorite_sports: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    favorite_players: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    favorite_leagues: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Notification preferences (stored as JSON)
    notification_preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Privacy settings
    profile_visibility: Mapped[ProfileVisibilityEnum] = mapped_column(
        SQLEnum(ProfileVisibilityEnum, name="profilevisibilityenum", native_enum=True, create_type=False),
        default=ProfileVisibilityEnum.PUBLIC
    )
    show_favorite_teams: Mapped[bool] = mapped_column(Boolean, default=True)
    show_activity: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_friend_requests: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Activity tracking
    total_reactions: Mapped[int] = mapped_column(Integer, default=0)
    matches_watched: Mapped[int] = mapped_column(Integer, default=0)
    highlights_watched: Mapped[int] = mapped_column(Integer, default=0)
    
    # Localization
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    date_format: Mapped[str] = mapped_column(String(20), default="MM/DD/YYYY")
    time_format: Mapped[str] = mapped_column(String(10), default="12h")
    
    # Metadata
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="profile")

class ScheduleDB(Base):
    __tablename__ = "schedules"
    
    schedule_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    total_matches: Mapped[int] = mapped_column(Integer, default=0)
    schedule_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    matches: Mapped[List["MatchDB"]] = relationship("MatchDB", secondary="schedule_matches", back_populates="schedules")

class ScheduleMatchDB(Base):
    __tablename__ = "schedule_matches"
    
    schedule_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schedules.schedule_id"), primary_key=True)
    match_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.match_id"), primary_key=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
