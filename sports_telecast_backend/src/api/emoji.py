from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional

from models.emoji import (
    EmojiListResponse, EmojiReactionRequest, EmojiReactionResponse,
    EmojiReactionSummary
)
from auth.jwt_auth import get_current_user_id, optional_auth
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from database.repositories import EmojiRepository, MatchRepository, EventRepository
from database.schemas import convert_emoji_db_to_pydantic
from websocket.manager import manager

router = APIRouter(prefix="/fan-engagement/emoji/v1", tags=["Fan Engagement - Emojis"])

# PUBLIC_INTERFACE
@router.get("/listEmojis", response_model=EmojiListResponse, summary="List available emojis")
async def list_emojis(
    pageNo: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(10, ge=1, le=100, description="Page size"),
    current_user_id: str = Depends(get_current_user_id),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of available emojis for reactions
    
    Returns all active emoji assets that users can use for reactions during live events.
    Requires JWT authentication.
    """
    offset = (pageNo - 1) * pageSize
    emoji_repo = EmojiRepository(db_session)
    emojis_db = await emoji_repo.get_emojis(limit=pageSize, offset=offset)
    
    # Convert to Pydantic models
    emojis = [convert_emoji_db_to_pydantic(emoji) for emoji in emojis_db]
    
    # Get total count of active emojis
    all_emojis_db = await emoji_repo.get_emojis(limit=1000, offset=0)
    total_count = len(all_emojis_db)
    
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
    db_session: AsyncSession = Depends(get_db)
):
    """
    Submit an emoji reaction for a live event
    
    Records a user's emoji reaction for a specific event and broadcasts the update
    to all connected WebSocket clients in real-time.
    """
    emoji_repo = EmojiRepository(db_session)
    match_repo = MatchRepository(db_session)
    event_repo = EventRepository(db_session)
    
    # Validate emoji exists
    emoji_db = await emoji_repo.get_emoji_by_id(reaction_request.emoji_id)
    if not emoji_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emoji not found"
        )
    
    # Validate event exists - try both match and event lookups
    match_db = await match_repo.get_match_by_id(reaction_request.event_id)
    event_db = await event_repo.get_event_by_id(reaction_request.event_id)
    if not match_db and not event_db:
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
    
    # Broadcast update to WebSocket connections
    import asyncio
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
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get emoji reaction summary for a specific event
    
    Returns aggregated reaction counts and top emojis for the specified event.
    Authentication is optional.
    """
    match_repo = MatchRepository(db_session)
    emoji_repo = EmojiRepository(db_session)
    
    # Validate event exists
    match_db = await match_repo.get_match_by_id(event_id)
    if not match_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    summary = await emoji_repo.get_reaction_summary(event_id)
    return summary
