from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EmojiType(str, Enum):
    """Emoji type enumeration"""
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

class EmojiAsset(BaseModel):
    """Emoji asset model"""
    emoji_id: str = Field(..., description="Unique emoji identifier", example="EMJ103")
    emoji_type: EmojiType = Field(..., description="Type of emoji", example="clap")
    image_url: HttpUrl = Field(..., description="URL to emoji image", example="https://cdn.mydomain.com/emojis/clap.png")
    name: str = Field(..., description="Display name of emoji", example="Clap")
    description: Optional[str] = Field(None, description="Emoji description")
    is_active: bool = Field(default=True, description="Whether emoji is active")
    sort_order: int = Field(default=0, description="Sort order for display")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserEmojiReaction(BaseModel):
    """User emoji reaction model"""
    user_id: str = Field(..., description="User identifier", example="USR456")
    event_id: str = Field(..., description="Event identifier", example="EVT123")
    emoji_id: str = Field(..., description="Emoji identifier", example="EMJ001")
    created_at: datetime = Field(..., description="Reaction timestamp", example="2025-07-29T11:35:24Z")

class EmojiReactionSummary(BaseModel):
    """Emoji reaction summary for an event"""
    event_id: str = Field(..., description="Event identifier")
    emoji_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of reactions per emoji ID"
    )
    total_reactions: int = Field(default=0, description="Total number of reactions")
    top_emojis: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top emojis with counts"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class EmojiListRequest(BaseModel):
    """Request model for emoji list"""
    page_no: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Page size")

class EmojiListResponse(BaseModel):
    """Response model for emoji list"""
    status: str = Field(default="SUCCESS", description="Response status")
    emojis: List[EmojiAsset] = Field(..., description="List of emojis")
    total: int = Field(..., description="Total number of emojis")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")

class EmojiReactionRequest(BaseModel):
    """Request model for emoji reaction"""
    event_id: str = Field(..., description="Event identifier", example="EVT123")
    emoji_id: str = Field(..., description="Emoji identifier", example="EMJ001")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Reaction timestamp")

class EmojiReactionResponse(BaseModel):
    """Response model for emoji reaction"""
    status: str = Field(default="SUCCESS", description="Response status")
    reaction_id: str = Field(..., description="Unique reaction identifier")
    message: str = Field(default="Reaction recorded successfully", description="Response message")

class WebSocketMessage(BaseModel):
    """WebSocket message model for real-time updates"""
    type: str = Field(..., description="Message type")
    event_id: str = Field(..., description="Event identifier")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EmojiReactionUpdate(BaseModel):
    """Real-time emoji reaction update"""
    event_id: str = Field(..., description="Event identifier")
    emoji_id: str = Field(..., description="Emoji identifier")
    emoji_type: EmojiType = Field(..., description="Emoji type")
    new_count: int = Field(..., description="New reaction count for this emoji")
    user_id: str = Field(..., description="User who reacted")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
