from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime

class UserProfileResponse(BaseModel):
    profile_id: str
    user_id: str
    display_name: str
    avatar_url: Optional[str] = None

class HighlightResponse(BaseModel):
    highlight_id: str
    match_id: str
    title: str
    video_url: str
    created_at: datetime

class EmojiResponse(BaseModel):
    emoji_id: str
    emoji_type: str
    image_url: str
    name: str
    is_active: bool = True

class EmojiReactionResponse(BaseModel):
    status: str
    reaction_id: str
    message: str

class MatchResponse(BaseModel):
    match_id: str
    event_id: str
    home_team_id: str
    away_team_id: str
    status: str
    start_time: datetime
    stream_url: Optional[str] = None
