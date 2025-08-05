from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session

from ..models.emoji import (
    EmojiListResponse, EmojiReactionRequest, EmojiReactionResponse,
    EmojiReactionSummary, EmojiAsset
)
from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user, get_current_user_optional
from ..database.session import get_db
from ..database.service import DatabaseService
from ..websocket.manager import manager
import asyncio

router = APIRouter(prefix="/fan-engagement/emoji/v1", tags=["Fan Engagement - Emojis"])

# PUBLIC_INTERFACE
@router.get("/listEmojis", response_model=EmojiListResponse, summary="List available emojis")
def list_emojis(
    pageNo: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of available emojis for reactions
    
    Returns all active emoji assets that users can use for reactions during live events.
    Requires JWT authentication.
    """
    try:
        db_service = DatabaseService(db)
        offset = (pageNo - 1) * pageSize
        emojis, total = db_service.get_emojis(limit=pageSize, offset=offset)
        
        # Convert database models to Pydantic models
        emoji_list = []
        for emoji in emojis:
            emoji_data = EmojiAsset(
                emoji_id=emoji.emoji_id,
                emoji_type=emoji.emoji_type,
                image_url=emoji.image_url,
                name=emoji.name,
                description=emoji.description,
                is_active=emoji.is_active,
                sort_order=emoji.sort_order,
                created_at=emoji.created_at
            )
            emoji_list.append(emoji_data)
        
        return EmojiListResponse(
            status="SUCCESS",
            emojis=emoji_list,
            total=total,
            page=pageNo,
            page_size=pageSize
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving emojis: {str(e)}")

# PUBLIC_INTERFACE
@router.post("/userEmojiReaction", response_model=EmojiReactionResponse, summary="Submit emoji reaction")
def create_emoji_reaction(
    reaction_request: EmojiReactionRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit an emoji reaction for a live event
    
    Records a user's emoji reaction for a specific event and broadcasts the update
    to all connected WebSocket clients in real-time.
    """
    try:
        db_service = DatabaseService(db)
        
        # Validate emoji exists
        emoji = db_service.get_emoji_by_id(reaction_request.emoji_id)
        if not emoji:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emoji not found"
            )
        
        # Validate event exists - try both match and event lookups
        match = db_service.get_match_by_id(reaction_request.event_id)
        event = db_service.get_event_by_id(reaction_request.event_id)
        if not match and not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Create reaction
        reaction_id = db_service.add_reaction(
            user_id=current_user.user_id,  # Use authenticated user ID
            event_id=reaction_request.event_id,
            emoji_id=reaction_request.emoji_id
        )
        
        # Get updated reaction summary
        summary_data = db_service.get_reaction_summary(reaction_request.event_id)
        
        # Prepare WebSocket broadcast data
        emoji_update_data = {
            "event_id": reaction_request.event_id,
            "emoji_id": reaction_request.emoji_id,
            "emoji_type": emoji.emoji_type,
            "new_count": summary_data["emoji_counts"].get(reaction_request.emoji_id, 1),
            "user_id": current_user.user_id,
            "reaction_summary": {
                "total_reactions": summary_data["total_reactions"],
                "top_emojis": summary_data["top_emojis"]
            }
        }
        
        # Schedule WebSocket broadcast (non-blocking)
        asyncio.create_task(manager.broadcast_emoji_reaction(
            reaction_request.event_id, 
            emoji_update_data
        ))
        
        return EmojiReactionResponse(
            status="SUCCESS",
            reaction_id=reaction_id,
            message="Reaction recorded successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating reaction: {str(e)}")

# PUBLIC_INTERFACE
@router.get("/reactions/{event_id}", response_model=EmojiReactionSummary, summary="Get event reaction summary")
def get_event_reactions(
    event_id: str,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get emoji reaction summary for a specific event
    
    Returns aggregated reaction counts and top emojis for the specified event.
    Authentication is optional.
    """
    try:
        db_service = DatabaseService(db)
        
        # Validate event exists
        match = db_service.get_match_by_id(event_id)
        event = db_service.get_event_by_id(event_id)
        if not match and not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        summary_data = db_service.get_reaction_summary(event_id)
        
        summary = EmojiReactionSummary(
            event_id=summary_data["event_id"],
            emoji_counts=summary_data["emoji_counts"],
            total_reactions=summary_data["total_reactions"],
            top_emojis=summary_data["top_emojis"],
            last_updated=summary_data["last_updated"]
        )
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving reactions: {str(e)}")
