from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.match import Highlight, HighlightListResponse
from ..auth.jwt_auth import optional_auth
from ..database import get_db
from ..database.repositories import HighlightRepository
from ..database.schemas import convert_highlight_db_to_pydantic

router = APIRouter(prefix="/highlights", tags=["Highlights"])

# PUBLIC_INTERFACE
@router.get("/", response_model=HighlightListResponse, summary="Get highlights list")
async def get_highlights(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    match_id: Optional[str] = Query(None, description="Filter by match ID"),
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of match highlights
    
    Returns video highlights from matches with optional filtering by match.
    Authentication is optional - may provide personalized results for authenticated users.
    """
    offset = (page - 1) * page_size
    highlight_repo = HighlightRepository(db_session)
    
    # Get highlights with pagination
    highlights_db = await highlight_repo.get_highlights(
        limit=page_size, 
        offset=offset, 
        match_id=match_id
    )
    
    # Convert to Pydantic models
    highlights = [convert_highlight_db_to_pydantic(highlight) for highlight in highlights_db]
    
    # Get total count for pagination
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
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific highlight
    
    Returns comprehensive highlight data including video URL, description, and metadata.
    """
    highlight_repo = HighlightRepository(db_session)
    highlight_db = await highlight_repo.get_highlight_by_id(highlight_id)
    if not highlight_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Highlight not found"
        )
    
    # Convert to Pydantic model
    highlight = convert_highlight_db_to_pydantic(highlight_db)
    return highlight

# PUBLIC_INTERFACE
@router.get("/featured/latest", response_model=HighlightListResponse, summary="Get latest featured highlights")
async def get_featured_highlights(
    limit: int = Query(10, ge=1, le=50, description="Number of highlights to return"),
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Get latest featured highlights
    
    Returns the most recent and popular highlights across all matches.
    Perfect for homepage or featured content sections.
    """
    highlight_repo = HighlightRepository(db_session)
    
    # Get featured highlights using repository method
    featured_highlights_db = await highlight_repo.get_featured_highlights(limit=limit)
    
    # Convert to Pydantic models
    featured_highlights = [convert_highlight_db_to_pydantic(highlight) for highlight in featured_highlights_db]
    
    return HighlightListResponse(
        highlights=featured_highlights,
        total=len(featured_highlights),
        page=1,
        page_size=limit
    )
