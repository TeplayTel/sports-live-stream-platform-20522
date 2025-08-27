from fastapi import APIRouter, Depends, Query, Body, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..database.connection import get_db
from ..database.models import EmojiAssetDB, UserEmojiReactionDB
from ..database.repositories import MatchRepository, EventRepository
from ..database.schemas import convert_emoji_db_to_pydantic
from ..models.emoji import (
    EmojiListResponse,
    EmojiReactionRequest,
    EmojiReactionResponse,
    EmojiReactionSummary,
)
from ..api.utils import get_trusted_user
from ..websocket.manager import manager

router = APIRouter(tags=["Emoji"])

# PUBLIC_INTERFACE
@router.get(
    "/getEmoji",
    response_model=EmojiListResponse,
    summary="Get available emojis",
    description="Returns all available emojis (active) with pagination.",
)
async def get_emoji(
    pageNo: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(50, ge=1, le=100, description="Page size"),
    request: Request = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Get the list of available emojis. No authentication required.
    """
    # Optional user extraction (no auth required)
    get_trusted_user(request)

    offset = (pageNo - 1) * pageSize
    result = await session.execute(
        select(EmojiAssetDB).where(EmojiAssetDB.is_active == True).offset(offset).limit(pageSize)
    )
    emojis_db = result.scalars().all()
    emojis = [convert_emoji_db_to_pydantic(emoji) for emoji in emojis_db]

    total_result = await session.execute(
        select(func.count()).select_from(EmojiAssetDB).where(EmojiAssetDB.is_active == True)
    )
    total = int(total_result.scalar() or 0)

    return EmojiListResponse(
        status="SUCCESS",
        emojis=emojis,
        total=total,
        page=pageNo,
        page_size=pageSize,
    )

# PUBLIC_INTERFACE
@router.post(
    "/userEmojiReaction",
    response_model=EmojiReactionResponse,
    summary="Record a user emoji reaction",
    description="Records a reaction to an emoji for an event and increases its count.",
)
async def user_emoji_reaction(
    payload: EmojiReactionRequest = Body(...),
    request: Request = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Record a user's emoji reaction for an event (match or generic event).
    No auth required; userId can be provided via header X-User-Id, query user_id,
    or omitted (will error).
    """
    user_id, _ = get_trusted_user(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing userId. Provide X-User-Id header or user_id query parameter.",
        )

    # Validate emoji exists and active
    emoji_q = await session.execute(
        select(EmojiAssetDB).where(EmojiAssetDB.emoji_id == payload.emoji_id, EmojiAssetDB.is_active == True)
    )
    emoji_db = emoji_q.scalar_one_or_none()
    if not emoji_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    # Validate event_id exists as a match or an event
    match_repo = MatchRepository(session)
    event_repo = EventRepository(session)
    match_db = await match_repo.get_match_by_id(payload.event_id)
    event_db = await event_repo.get_event_by_id(payload.event_id)
    if not match_db and not event_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Insert reaction row
    reaction = UserEmojiReactionDB(
        user_id=user_id,
        event_id=payload.event_id,
        emoji_id=payload.emoji_id,
    )
    session.add(reaction)
    await session.commit()
    await session.refresh(reaction)

    # Summarize counts for broadcast
    counts_result = await session.execute(
        select(UserEmojiReactionDB.emoji_id, func.count())
        .where(UserEmojiReactionDB.event_id == payload.event_id)
        .group_by(UserEmojiReactionDB.emoji_id)
    )
    rows = counts_result.all()
    emoji_counts = {row[0]: int(row[1]) for row in rows}
    total_reactions = sum(emoji_counts.values())

    # Fire-and-forget broadcast to websocket listeners
    import asyncio

    asyncio.create_task(
        manager.broadcast_emoji_reaction(
            payload.event_id,
            {
                "event_id": payload.event_id,
                "emoji_id": payload.emoji_id,
                "emoji_type": getattr(emoji_db, "emoji_type", None),
                "image_url": getattr(emoji_db, "image_url", None),
                "name": getattr(emoji_db, "name", None),
                "user_id": user_id,
                "total_reactions": total_reactions,
            },
        )
    )

    return EmojiReactionResponse(
        status="SUCCESS",
        reaction_id=reaction.reaction_id,
        message="Reaction recorded successfully",
    )

# PUBLIC_INTERFACE
@router.get(
    "/emoji/reactions/{event_id}",
    response_model=EmojiReactionSummary,
    summary="Reaction summary for an event",
    description="Returns aggregate emoji counts for a given event_id.",
)
async def get_reaction_summary(
    event_id: str,
    request: Request = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Fetch the summary of emoji reactions for an event.
    """
    # Optional user extraction (no auth required)
    get_trusted_user(request)

    # Ensure the event/match exists
    match_repo = MatchRepository(session)
    match_db = await match_repo.get_match_by_id(event_id)
    if not match_db:
        event_repo = EventRepository(session)
        event_db = await event_repo.get_event_by_id(event_id)
        if not event_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

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
        top_emojis=[{"emoji_id": k, "count": v} for k, v in sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True)[:5]],
    )
