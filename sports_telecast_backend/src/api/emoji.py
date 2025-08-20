from fastapi import APIRouter, HTTPException, status, Request, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import asyncio
from pydantic import BaseModel, Field
from typing import List

from ..models.emoji import (
    EmojiReactionSummary,
    UserEmojiReactionCaptureRequest,
    ReactionCapturedResponse,
)
from ..database.repositories import EmojiRepository, MatchRepository, EventRepository
from ..database.schemas import convert_emoji_db_to_pydantic
from ..database.connection import get_db
from ..websocket.manager import manager
from ..auth.jwt_auth import get_current_user_id
from .utils import get_trusted_user

router = APIRouter(prefix="/fan-engagement/emoji/v1", tags=["Fan Engagement - Emojis"])


def _parse_created_at(created_at_str: str) -> datetime:
    """
    Parse createdAt string into a timezone-aware datetime where possible.
    Accepts ISO 8601 formats; falls back to naive parsing as UTC if tz absent.
    """
    # Try ISO format with 'Z' or offset
    try:
        # Handle 'Z' suffix
        if created_at_str.endswith("Z"):
            created_at_str = created_at_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(created_at_str)
        return dt
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid createdAt format. Use ISO 8601 string (e.g., 2025-07-29T11:35:24Z).",
        )


# PUBLIC_INTERFACE
class EmojiListItem(BaseModel):
    """Response model item for listing emojis with frontend-required fields."""
    emojiId: str = Field(..., description="Emoji unique identifier (from emoji_id)")
    emojiType: str = Field(..., description="Emoji type/category (from emoji_type)")
    imageUrl: str = Field(..., description="Public image URL for the emoji (from image_url or derived)")

# PUBLIC_INTERFACE
@router.get(
    "/listEmojis",
    response_model=List[EmojiListItem],
    summary="List available emojis",
    description="Return all records from emoji_assets with fields: emojiId (emoji_id), emojiType (emoji_type), imageUrl (image_url or derived from file_location).",
    responses={
        200: {"description": "List of available emojis"},
        500: {"description": "Internal server error"}
    },
)
async def list_emojis(
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all available emojis for reactions.

    Returns a flat list of items with camelCase keys expected by the frontend:
    - emojiId: from emoji_assets.emoji_id
    - emojiType: from emoji_assets.emoji_type
    - imageUrl: from emoji_assets.image_url if available, otherwise derived from file_location

    Notes:
    - Connects to the actual database via AsyncSession using the repository layer.
    - No pagination; returns all active emojis, ordered by sort_order when available.
    """
    # No auth needed; allow trusted frontend access
    _ = get_trusted_user(request)

    emoji_repo = EmojiRepository(db)
    # Fetch all active emojis (upper reasonable bound)
    emojis_db = await emoji_repo.get_emojis(limit=1000, offset=0)

    # Convert using shared converter (handles ORM and minimal dict rows) then remap keys to camelCase
    items: List[EmojiListItem] = []
    for e in emojis_db:
        converted = convert_emoji_db_to_pydantic(e)
        items.append(
            EmojiListItem(
                emojiId=str(converted.get("emoji_id")),
                emojiType=str(converted.get("emoji_type")),
                imageUrl=str(converted.get("image_url")),
            )
        )
    return items


# PUBLIC_INTERFACE
@router.post(
    "/userEmojiReaction",
    response_model=ReactionCapturedResponse,
    summary="Submit emoji reaction",
    description="Requires Authorization: Bearer <user-token>. Accepts body: {userId, eventId, emojiId, createdAt}.",
)
async def create_emoji_reaction(
    reaction_request: UserEmojiReactionCaptureRequest = Body(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Submit an emoji reaction for a live event.

    Authorization:
      - Requires 'Authorization: Bearer <user-token>' header.

    Request body (JSON):
      - userId (str): ID of the user submitting the reaction
      - eventId (str): ID of event or match
      - emojiId (str): ID of the emoji
      - createdAt (str): ISO 8601 timestamp for when the reaction occurred

    Returns:
      - {
          "status": "SUCCESS",
          "message": "Reaction captured successfully",
          "data": { "reactionId": "<uuid>" }
        }
    """
    # Validate presence of fields via Pydantic and parse createdAt
    user_id: str = reaction_request.userId
    event_id: str = reaction_request.eventId
    emoji_id: str = reaction_request.emojiId
    created_at_str: str = reaction_request.createdAt

    if not all([user_id, event_id, emoji_id, created_at_str]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: userId, eventId, emojiId, createdAt",
        )

    created_at: datetime = _parse_created_at(created_at_str)

    # Repositories
    emoji_repo = EmojiRepository(db)
    match_repo = MatchRepository(db)
    event_repo = EventRepository(db)

    # Validate emoji exists
    emoji_db = await emoji_repo.get_emoji_by_id(emoji_id)
    if not emoji_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    # Validate event/match exists (support either)
    match_db = await match_repo.get_match_by_id(event_id)
    event_db = await event_repo.get_event_by_id(event_id)
    if not match_db and not event_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Persist reaction with provided createdAt
    reaction_id = await emoji_repo.add_reaction(
        user_id=user_id,
        event_id=event_id,
        emoji_id=emoji_id,
        created_at=created_at,
    )

    # Asynchronously broadcast updated counts (best-effort, non-blocking)
    try:
        summary = await emoji_repo.get_reaction_summary(event_id)
        emoji_update_data = {
            "event_id": event_id,
            "emoji_id": emoji_id,
            "emoji_type": emoji_db.emoji_type.value,
            "new_count": summary.get("emoji_counts", {}).get(emoji_id, 1),
            "user_id": user_id,
            "reaction_summary": {
                "total_reactions": summary.get("total_reactions", 0),
                "top_emojis": summary.get("top_emojis", []),
            },
        }
        asyncio.create_task(manager.broadcast_emoji_reaction(event_id, emoji_update_data))
    except Exception:
        # Do not fail the API if websocket broadcast fails
        pass

    return ReactionCapturedResponse(
        status="SUCCESS",
        message="Reaction captured successfully",
        data={"reactionId": reaction_id},
    )


# PUBLIC_INTERFACE
@router.get("/reactions/{event_id}", response_model=EmojiReactionSummary, summary="Get event reaction summary")
async def get_event_reactions(
    event_id: str,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get emoji reaction summary for a specific event.
    Accepts userId/userData (optional) from trusted frontend, no auth required.
    """
    get_trusted_user(request)
    match_repo = MatchRepository(db)
    emoji_repo = EmojiRepository(db)
    match_db = await match_repo.get_match_by_id(event_id)
    if not match_db:
        # Allow summaries for events even if match isn't found (some event_ids refer to EventDB)
        event_repo = EventRepository(db)
        event_db = await event_repo.get_event_by_id(event_id)
        if not event_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    summary = await emoji_repo.get_reaction_summary(event_id)
    return summary
