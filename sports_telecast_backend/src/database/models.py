from typing import Optional, List
from sqlalchemy import String, DateTime, Boolean, Integer, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
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
    USER = "user"
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
    
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[UserRoleEnum] = mapped_column(SQLEnum(UserRoleEnum), default=UserRoleEnum.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    emoji_reactions: Mapped[List["UserEmojiReactionDB"]] = relationship("UserEmojiReactionDB", back_populates="user")

class TeamDB(Base):
    __tablename__ = "teams"
    
    team_id: Mapped[str] = mapped_column(String(36), primary_key=True)
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
    
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sport_type: Mapped[SportTypeEnum] = mapped_column(SQLEnum(SportTypeEnum), nullable=False)
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
    
    match_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.event_id"), nullable=False)
    home_team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.team_id"), nullable=False)
    away_team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.team_id"), nullable=False)
    sport_type: Mapped[SportTypeEnum] = mapped_column(SQLEnum(SportTypeEnum), nullable=False)
    status: Mapped[MatchStatusEnum] = mapped_column(SQLEnum(MatchStatusEnum), default=MatchStatusEnum.SCHEDULED)
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

class MatchEventDB(Base):
    __tablename__ = "match_events"
    
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    match_id: Mapped[str] = mapped_column(String(36), ForeignKey("matches.match_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    team_id: Mapped[str] = mapped_column(String(36), nullable=False)
    player_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    match: Mapped["MatchDB"] = relationship("MatchDB", back_populates="match_events")

class EmojiAssetDB(Base):
    __tablename__ = "emoji_assets"
    
    emoji_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    emoji_type: Mapped[EmojiTypeEnum] = mapped_column(SQLEnum(EmojiTypeEnum), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    reactions: Mapped[List["UserEmojiReactionDB"]] = relationship("UserEmojiReactionDB", back_populates="emoji")

class UserEmojiReactionDB(Base):
    __tablename__ = "user_emoji_reactions"
    
    reaction_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    emoji_id: Mapped[str] = mapped_column(String(36), ForeignKey("emoji_assets.emoji_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="emoji_reactions")
    emoji: Mapped["EmojiAssetDB"] = relationship("EmojiAssetDB", back_populates="reactions")

class HighlightDB(Base):
    __tablename__ = "highlights"
    
    highlight_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    match_id: Mapped[str] = mapped_column(String(36), ForeignKey("matches.match_id"), nullable=False)
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
