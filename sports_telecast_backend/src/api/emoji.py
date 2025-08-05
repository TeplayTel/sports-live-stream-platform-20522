from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..models.emoji import (
    EmojiListResponse, EmojiReactionRequest, EmojiReactionResponse,
    EmojiReactionSummary
)
from ..auth.jwt_auth import get_current_user_id, optional_auth
from ..database.connection import get_db
from ..database.repositories import EmojiRepository, MatchRepository, EventRepository
from ..database.schemas import convert_emoji_db_to_pydantic
from ..websocket.manager import manager

router = APIRouter(prefix="/fan-engagement/emoji/v1", tags=["Fan Engagement - Emojis"])

# PUBLIC_INTERFACE
@router.get("/listEmojis", response_model=EmojiListResponse, summary="List available emojis")
async def list_emojis(
    pageNo: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(10, ge=1, le=100, description="Page size"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of available emojis for reactions
    
    Returns all active emoji assets that users can use for reactions during live events.
    Requires JWT authentication.
    """
    emoji_repo = EmojiRepository(db)
    offset = (pageNo - 1) * pageSize
    
    emojis_db = await emoji_repo.get_emojis(limit=pageSize, offset=offset)
    
    # Convert to Pydantic models
    emojis = [convert_emoji_db_to_pydantic(emoji_db) for emoji_db in emojis_db]
    
    # Get total count (simplified approach)
    total_count = len(emojis) if len(emojis) < pageSize else pageSize * pageNo + 1
    
    return EmojiListResponse(
        status="SUCCESS",
        emojis=emojis,
        total=total_count,
        page=pageNo,
        page_size=pageSize
    )

# PUBLIC_INTERFACE
@router.post("/userEmojiReaction", response_model=EmojiReactionResponse, summary="Submit emoji reaction")
async def create_emoji_reaction(
    reaction_request: EmojiReactionRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit an emoji reaction for a live event
    
    Records a user's emoji reaction for a specific event and broadcasts the update
    to all connected WebSocket clients in real-time.
    """
    emoji_repo = EmojiRepository(db)
    
    # Validate emoji exists
    emoji_db = await emoji_repo.get_emoji_by_id(reaction_request.emoji_id)
    if not emoji_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emoji not found"
        )
    
    # Validate event exists - try both match and event lookups
    match_repo = MatchRepository(db)
    event_repo = EventRepository(db)
    
    event_exists = (
        await match_repo.get_match_by_id(reaction_request.event_id) or 
        await event_repo.get_event_by_id(reaction_request.event_id)
    )
    
    if not event_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Create reaction record
    reaction_id = await emoji_repo.add_reaction(
        current_user_id,  # Use authenticated user ID
        reaction_request.event_id,
        reaction_request.emoji_id
    )
    
    # Get updated reaction summary
    summary = await emoji_repo.get_reaction_summary(reaction_request.event_id)
    
    # Prepare WebSocket broadcast data
    emoji_update_data = {
        "event_id": reaction_request.event_id,
        "emoji_id": reaction_request.emoji_id,
        "emoji_type": emoji_db.emoji_type.value,
        "new_count": summary.get("emoji_counts", {}).get(reaction_request.emoji_id, 1),
        "user_id": current_user_id,
        "reaction_summary": {
            "total_reactions": summary.get("total_reactions", 0),
            "top_emojis": summary.get("top_emojis", [])
        }
    }
    
    # Schedule WebSocket broadcast (non-blocking)
    import asyncio
    asyncio.create_task(manager.broadcast_emoji_reaction(
        reaction_request.event_id, 
        emoji_update_data
    ))
    
    return EmojiReactionResponse(
        status="SUCCESS",
        reaction_id=reaction_id,
        message="Reaction recorded successfully"
    )

# PUBLIC_INTERFACE
@router.get("/reactions/{event_id}", response_model=EmojiReactionSummary, summary="Get event reaction summary")
async def get_event_reactions(
    event_id: str,
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get emoji reaction summary for a specific event
    
    Returns aggregated reaction counts and top emojis for the specified event.
    Authentication is optional.
    """
    # Validate event exists
    match_repo = MatchRepository(db)
    event_repo = EventRepository(db)
    
    event_exists = (
        await match_repo.get_match_by_id(event_id) or 
        await event_repo.get_event_by_id(event_id)
    )
    
    if not event_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    emoji_repo = EmojiRepository(db)
    summary = await emoji_repo.get_reaction_summary(event_id)
    
    return EmojiReactionSummary(
        event_id=summary["event_id"],
        emoji_counts=summary["emoji_counts"],
        total_reactions=summary["total_reactions"],
        top_emojis=summary["top_emojis"],
        last_updated=summary["last_updated"]
    )
