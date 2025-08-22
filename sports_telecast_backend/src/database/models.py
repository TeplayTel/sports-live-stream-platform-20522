from typing import Optional, List
from sqlalchemy import String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid as uuid_pkg

from .connection import Base

# Database Models
class UserDB(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    emoji_reactions: Mapped[List["UserEmojiReactionDB"]] = relationship("UserEmojiReactionDB", back_populates="user")
    profile: Mapped[Optional["UserProfileDB"]] = relationship("UserProfileDB", back_populates="user", uselist=False)

class UserProfileDB(Base):
    __tablename__ = "user_profiles"
    
    profile_id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id"), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="profile")

class EventDB(Base):
    __tablename__ = "events"
    
    event_id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sport_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    matches: Mapped[List["MatchDB"]] = relationship("MatchDB", back_populates="event")

class TeamDB(Base):
    __tablename__ = "teams"
    
    team_id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Relationships
    home_matches: Mapped[List["MatchDB"]] = relationship("MatchDB", foreign_keys="MatchDB.home_team_id", back_populates="home_team")
    away_matches: Mapped[List["MatchDB"]] = relationship("MatchDB", foreign_keys="MatchDB.away_team_id", back_populates="away_team")

class MatchDB(Base):
    __tablename__ = "matches"
    
    match_id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    event_id: Mapped[str] = mapped_column(Text, ForeignKey("events.event_id"), nullable=False)
    home_team_id: Mapped[str] = mapped_column(Text, ForeignKey("teams.team_id"), nullable=False)
    away_team_id: Mapped[str] = mapped_column(Text, ForeignKey("teams.team_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="scheduled")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stream_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    event: Mapped["EventDB"] = relationship("EventDB", back_populates="matches")
    home_team: Mapped["TeamDB"] = relationship("TeamDB", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped["TeamDB"] = relationship("TeamDB", foreign_keys=[away_team_id], back_populates="away_matches")
    highlights: Mapped[List["HighlightDB"]] = relationship("HighlightDB", back_populates="match")
    schedules: Mapped[List["ScheduleDB"]] = relationship("ScheduleDB", secondary="schedule_matches", back_populates="matches")

class HighlightDB(Base):
    __tablename__ = "highlights"
    
    highlight_id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    match_id: Mapped[str] = mapped_column(Text, ForeignKey("matches.match_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    match: Mapped["MatchDB"] = relationship("MatchDB", back_populates="highlights")

class EmojiAssetDB(Base):
    __tablename__ = "emoji_assets"
    
    emoji_id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    emoji_type: Mapped[str] = mapped_column(String(50), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    reactions: Mapped[List["UserEmojiReactionDB"]] = relationship("UserEmojiReactionDB", back_populates="emoji")

class UserEmojiReactionDB(Base):
    __tablename__ = "user_emoji_reactions"
    
    reaction_id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(Text, nullable=False)
    emoji_id: Mapped[str] = mapped_column(Text, ForeignKey("emoji_assets.emoji_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="emoji_reactions")
    emoji: Mapped["EmojiAssetDB"] = relationship("EmojiAssetDB", back_populates="reactions")

class ScheduleDB(Base):
    __tablename__ = "schedules"
    
    schedule_id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    total_matches: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    matches: Mapped[List["MatchDB"]] = relationship("MatchDB", secondary="schedule_matches", back_populates="schedules")

class ScheduleMatchDB(Base):
    __tablename__ = "schedule_matches"
    
    schedule_id: Mapped[str] = mapped_column(Text, ForeignKey("schedules.schedule_id"), primary_key=True)
    match_id: Mapped[str] = mapped_column(Text, ForeignKey("matches.match_id"), primary_key=True)
