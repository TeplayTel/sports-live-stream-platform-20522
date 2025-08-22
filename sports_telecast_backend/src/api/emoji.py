from fastapi import APIRouter, HTTPException, status, Query, Request, Body, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.emoji import (
    EmojiListResponse, EmojiReactionRequest, EmojiReactionResponse,
    EmojiReactionSummary
)
from ..database.repositories import MatchRepository, EventRepository
from ..database.schemas import convert_emoji_db_to_pydantic
from ..database.connection import get_db
from ..database.models import EmojiAssetDB, UserEmojiReactionDB
from ..websocket.manager import manager
from .utils import get_trusted_user

router = APIRouter(prefix="/fan-engagement/emoji/v1", tags=["Fan Engagement - Emojis"])

# PUBLIC_INTERFACE
@router.get("/listEmojis", response_model=EmojiListResponse, summary="List available emojis")
async def list_emojis(
    pageNo: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(10, ge=1, le=100, description="Page size"),
    request: Request = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of available emojis for reactions.
    Accepts userId/userData via headers or request for trusted/mocked login.
    """
    get_trusted_user(request)
    offset = (pageNo - 1) * pageSize

    # Query emojis directly using the session and ORM model
    result = await session.execute(
        select(EmojiAssetDB)
        .where(EmojiAssetDB.is_active == True)  # only active emojis
        .offset(offset)
        .limit(pageSize)
    )
    emojis_db = result.scalars().all()
    emojis = [convert_emoji_db_to_pydantic(emoji) for emoji in emojis_db]

    total_result = await session.execute(
        select(func.count()).select_from(EmojiAssetDB).where(EmojiAssetDB.is_active == True)
    )
    total_count = int(total_result.scalar() or 0)

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
    session: AsyncSession = Depends(get_db),
):
    """
    Submit an emoji reaction for a live event.
    Accepts userId from trusted frontend in headers/body/params.
    """
    user_id, _ = get_trusted_user(request)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing userId in headers or params.")

    # Verify emoji exists
    emoji_result = await session.execute(
        select(EmojiAssetDB).where(EmojiAssetDB.emoji_id == reaction_request.emoji_id, EmojiAssetDB.is_active == True)
    )
    emoji_db = emoji_result.scalar_one_or_none()
    if not emoji_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    # Verify event or match exists (support both IDs by checking repositories)
    match_repo = MatchRepository(session)
    event_repo = EventRepository(session)
    match_db = await match_repo.get_match_by_id(reaction_request.event_id)
    event_db = await event_repo.get_event_by_id(reaction_request.event_id)
    if not match_db and not event_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Insert reaction
    reaction = UserEmojiReactionDB(
        user_id=user_id,
        event_id=reaction_request.event_id,
        emoji_id=reaction_request.emoji_id,
    )
    session.add(reaction)
    await session.commit()
    await session.refresh(reaction)

    # Build summary: total reactions for this event and per-emoji counts
    counts_result = await session.execute(
        select(UserEmojiReactionDB.emoji_id, func.count())
        .where(UserEmojiReactionDB.event_id == reaction_request.event_id)
        .group_by(UserEmojiReactionDB.emoji_id)
    )
    rows = counts_result.all()
    emoji_counts = {row[0]: int(row[1]) for row in rows}
    total_reactions = sum(emoji_counts.values())

    import asyncio
    emoji_update_data = {
        "event_id": reaction_request.event_id,
        "emoji_id": reaction_request.emoji_id,
        "emoji_type": emoji_db.emoji_type,
        "image_url": emoji_db.image_url,
        "name": emoji_db.name,
        "user_id": user_id,
        "total_reactions": total_reactions
    }
    asyncio.create_task(manager.broadcast_emoji_reaction(
        reaction_request.event_id, emoji_update_data
    ))
    return EmojiReactionResponse(
        status="SUCCESS",
        reaction_id=reaction.reaction_id,
        message="Reaction recorded successfully"
    )

# PUBLIC_INTERFACE
@router.get("/reactions/{event_id}", response_model=EmojiReactionSummary, summary="Get event reaction summary")
async def get_event_reactions(
    event_id: str,
    request: Request = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Get emoji reaction summary for a specific event.
    Accepts userId/userData (optional) from trusted frontend, no auth required.
    """
    get_trusted_user(request)

    # Ensure the event/match exists using available repositories
    match_repo = MatchRepository(session)
    match_db = await match_repo.get_match_by_id(event_id)
    if not match_db:
        # If not a match, verify it as an event id
        event_repo = EventRepository(session)
        event_db = await event_repo.get_event_by_id(event_id)
        if not event_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Aggregate counts
    counts_result = await session.execute(
        select(UserEmojiReactionDB.emoji_id, func.count())
        .where(UserEmojiReactionDB.event_id == event_id)
        .group_by(UserEmojiReactionDB.emoji_id)
    )
    rows = counts_result.all()
    emoji_counts = {row[0]: int(row[1]) for row in rows}
    total_reactions = sum(emoji_counts.values())

    return EmojiReactionSummary(
        event_id=event_id,
        emoji_counts=emoji_counts,
        total_reactions=total_reactions,
        top_emojis=[{"emoji_id": k, "count": v} for k, v in sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    )
