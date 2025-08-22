from fastapi import APIRouter, HTTPException, status, Query, Request, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
# Use response models from database.schemas, as all conversions/proxying use these
from ..database import get_db
from ..database.repositories import HighlightRepository
from ..database.schemas import convert_highlight_db_to_response
from .utils import get_trusted_user

router = APIRouter(prefix="/highlights", tags=["Highlights"])

# PUBLIC_INTERFACE
@router.get("/", summary="Get highlights list")
async def get_highlights(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    match_id: Optional[str] = Query(None, description="Filter by match ID"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get paginated list of match highlights
    Accepts userId/userData from headers/params as trusted (no auth).

    Ensures only serializable structures are returned; ORM/session objects never returned.
    """
    get_trusted_user(request)
    offset = (page - 1) * page_size
    highlight_repo = HighlightRepository(db)
    highlights_db = await highlight_repo.get_highlights(
        limit=page_size,
        offset=offset,
        match_id=match_id
    )
    highlights = [convert_highlight_db_to_response(highlight) for highlight in highlights_db]

    # For total, use a separate query or reuse repository; here we use a large limit as before
    all_highlights_db = await highlight_repo.get_highlights(limit=1000, offset=0, match_id=match_id)
    total = len(all_highlights_db)

    # Convert highlights to minimal schema
    highlight_data = []
    for h in highlights:
        highlight_dict = {
            "highlight_id": str(h.highlight_id),
            "match_id": str(h.match_id),
            "title": h.title,
            "video_url": h.video_url,
            "created_at": h.created_at
        }
        highlight_data.append(highlight_dict)

    return {
        "highlights": highlight_data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

# PUBLIC_INTERFACE
@router.get("/{highlight_id}", summary="Get highlight details")
async def get_highlight_details(
    highlight_id: str,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get detailed information about a specific highlight.
    Accepts userId/userData (if needed) from trusted frontend.

    Always returns a serializable dict.
    """
    get_trusted_user(request)
    highlight_repo = HighlightRepository(db)
    highlight_db = await highlight_repo.get_highlight_by_id(highlight_id)
    if not highlight_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Highlight not found")
    highlight = convert_highlight_db_to_response(highlight_db)
    return highlight.dict() if hasattr(highlight, "dict") else highlight

# PUBLIC_INTERFACE
@router.get("/featured/latest", summary="Get latest featured highlights")
async def get_featured_highlights(
    limit: int = Query(10, ge=1, le=50, description="Number of highlights to return"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get latest featured highlights.
    Accepts userId/userData (if needed) from trusted frontend.

    Always returns a serializable dict.
    """
    get_trusted_user(request)
    highlight_repo = HighlightRepository(db)
    featured_highlights_db = await highlight_repo.get_featured_highlights(limit=limit)
    featured_highlights = [convert_highlight_db_to_response(highlight) for highlight in featured_highlights_db]
    return {
        "highlights": [h.dict() if hasattr(h, "dict") else h for h in featured_highlights],
        "total": len(featured_highlights),
        "page": 1,
        "page_size": limit,
    }
