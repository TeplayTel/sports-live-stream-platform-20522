from fastapi import APIRouter, HTTPException, status, Query, Request
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.match import Highlight, HighlightListResponse
from ..database import get_db
from ..database.repositories import HighlightRepository
from ..database.schemas import convert_highlight_db_to_response
from .main import get_trusted_user

router = APIRouter(prefix="/highlights", tags=["Highlights"])

# PUBLIC_INTERFACE
@router.get("/", response_model=HighlightListResponse, summary="Get highlights list")
async def get_highlights(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    match_id: Optional[str] = Query(None, description="Filter by match ID"),
    request: Request = None,
    db_session: AsyncSession = None
):
    """
    Get paginated list of match highlights
    Accepts userId/userData from headers/params as trusted (no auth).
    """
    db_session = db_session or await get_db().__anext__()
    get_trusted_user(request)
    offset = (page - 1) * page_size
    highlight_repo = HighlightRepository(db_session)
    highlights_db = await highlight_repo.get_highlights(
        limit=page_size, 
        offset=offset, 
        match_id=match_id
    )
    highlights = [convert_highlight_db_to_response(highlight) for highlight in highlights_db]
    all_highlights_db = await highlight_repo.get_highlights(limit=1000, offset=0, match_id=match_id)
    total = len(all_highlights_db)
    return HighlightListResponse(
        highlights=highlights,
        total=total,
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@router.get("/{highlight_id}", response_model=Highlight, summary="Get highlight details")
async def get_highlight_details(
    highlight_id: str,
    request: Request = None,
    db_session: AsyncSession = None
):
    """
    Get detailed information about a specific highlight.
    Accepts userId/userData (if needed) from trusted frontend.
    """
    db_session = db_session or await get_db().__anext__()
    get_trusted_user(request)
    highlight_repo = HighlightRepository(db_session)
    highlight_db = await highlight_repo.get_highlight_by_id(highlight_id)
    if not highlight_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Highlight not found")
    highlight = convert_highlight_db_to_response(highlight_db)
    return highlight

# PUBLIC_INTERFACE
@router.get("/featured/latest", response_model=HighlightListResponse, summary="Get latest featured highlights")
async def get_featured_highlights(
    limit: int = Query(10, ge=1, le=50, description="Number of highlights to return"),
    request: Request = None,
    db_session: AsyncSession = None
):
    """
    Get latest featured highlights.
    Accepts userId/userData (if needed) from trusted frontend.
    """
    db_session = db_session or await get_db().__anext__()
    get_trusted_user(request)
    highlight_repo = HighlightRepository(db_session)
    featured_highlights_db = await highlight_repo.get_featured_highlights(limit=limit)
    featured_highlights = [convert_highlight_db_to_response(highlight) for highlight in featured_highlights_db]
    return HighlightListResponse(
        highlights=featured_highlights,
        total=len(featured_highlights),
        page=1,
        page_size=limit
    )
