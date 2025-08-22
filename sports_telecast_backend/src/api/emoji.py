from fastapi import APIRouter, HTTPException, status, Query, Request, Body
from ..models.emoji import (
    EmojiListResponse, EmojiReactionRequest, EmojiReactionResponse,
    EmojiReactionSummary, EmojiAsset
)
from ..database.repositories import EmojiRepository, MatchRepository, EventRepository
from ..database.schemas import convert_emoji_db_to_pydantic
from ..websocket.manager import manager
from .utils import get_trusted_user

router = APIRouter(prefix="/fan-engagement/emoji/v1", tags=["Fan Engagement - Emojis"])

# PUBLIC_INTERFACE
@router.get("/listEmojis", response_model=EmojiListResponse, summary="List available emojis")
async def list_emojis(
    pageNo: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(10, ge=1, le=100, description="Page size"),
    request: Request = None,
):
    """
    Get paginated list of available emojis for reactions.
    Accepts userId/userData via headers or request for trusted/mocked login.
    """
    get_trusted_user(request)
    offset = (pageNo - 1) * pageSize
    emoji_repo = EmojiRepository()
    emojis_db = await emoji_repo.get_emojis(limit=pageSize, offset=offset)
    emojis = [convert_emoji_db_to_pydantic(emoji) for emoji in emojis_db]
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
    reaction_request: EmojiReactionRequest = Body(...),
    request: Request = None,
):
    """
    Submit an emoji reaction for a live event.
    Accepts userId from trusted frontend in headers/body/params.
    """
    user_id, _ = get_trusted_user(request)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing userId in headers or params.")
    emoji_repo = EmojiRepository()
    match_repo = MatchRepository()
    event_repo = EventRepository()
    emoji_db = await emoji_repo.get_emoji_by_id(reaction_request.emoji_id)
    if not emoji_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")
    match_db = await match_repo.get_match_by_id(reaction_request.event_id)
    event_db = await event_repo.get_event_by_id(reaction_request.event_id)
    if not match_db and not event_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    reaction_id = await emoji_repo.add_reaction(
        user_id,
        reaction_request.event_id,
        reaction_request.emoji_id
    )
    summary = await emoji_repo.get_reaction_summary(reaction_request.event_id)
    import asyncio
    emoji_update_data = {
        "event_id": reaction_request.event_id,
        "emoji_id": reaction_request.emoji_id,
        "emoji_type": emoji_db.emoji_type.value,
        "new_count": summary.get("emoji_counts", {}).get(reaction_request.emoji_id, 1),
        "user_id": user_id,
        "reaction_summary": {
            "total_reactions": summary.get("total_reactions", 0),
            "top_emojis": summary.get("top_emojis", [])
        }
    }
    asyncio.create_task(manager.broadcast_emoji_reaction(
        reaction_request.event_id, emoji_update_data
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
    request: Request = None,
):
    """
    Get emoji reaction summary for a specific event.
    Accepts userId/userData (optional) from trusted frontend, no auth required.
    """
    get_trusted_user(request)
    match_repo = MatchRepository()
    emoji_repo = EmojiRepository()
    match_db = await match_repo.get_match_by_id(event_id)
    if not match_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    summary = await emoji_repo.get_reaction_summary(event_id)
    return summary
