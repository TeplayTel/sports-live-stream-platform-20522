from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional

from ..models.match import Highlight, HighlightListResponse
from ..auth.jwt_auth import optional_auth
from ..database.connection import db

router = APIRouter(prefix="/highlights", tags=["Highlights"])

# PUBLIC_INTERFACE
@router.get("/", response_model=HighlightListResponse, summary="Get highlights list")
def get_highlights(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    match_id: Optional[str] = Query(None, description="Filter by match ID"),
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get paginated list of match highlights
    
    Returns video highlights from matches with optional filtering by match.
    Authentication is optional - may provide personalized results for authenticated users.
    """
    offset = (page - 1) * page_size
    
    if match_id:
        # Get highlights for specific match
        highlights = db.get_highlights_by_match(match_id)
        # Apply pagination
        paginated_highlights = highlights[offset:offset + page_size]
        total = len(highlights)
    else:
        # Get all highlights
        highlights = db.get_highlights(limit=page_size, offset=offset)
        paginated_highlights = highlights
        # For total count, get all highlights
        all_highlights = db.get_highlights(limit=1000, offset=0)
        total = len(all_highlights)
    
    return HighlightListResponse(
        highlights=paginated_highlights,
        total=total,
        page=page,
        page_size=page_size
    )

# PUBLIC_INTERFACE
@router.get("/{highlight_id}", response_model=Highlight, summary="Get highlight details")
def get_highlight_details(
    highlight_id: str,
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get detailed information about a specific highlight
    
    Returns comprehensive highlight data including video URL, description, and metadata.
    """
    highlight = db.get_highlight_by_id(highlight_id)
    if not highlight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Highlight not found"
        )
    
    # Increment view count (in a real app, you might want to track unique views)
    highlight.view_count += 1
    
    return highlight

# PUBLIC_INTERFACE
@router.get("/featured/latest", response_model=HighlightListResponse, summary="Get latest featured highlights")
def get_featured_highlights(
    limit: int = Query(10, ge=1, le=50, description="Number of highlights to return"),
    user_id: Optional[str] = Depends(optional_auth)
):
    """
    Get latest featured highlights
    
    Returns the most recent and popular highlights across all matches.
    Perfect for homepage or featured content sections.
    """
    # Get recent highlights and sort by view count and recency
    all_highlights = db.get_highlights(limit=100, offset=0)
    
    # Sort by view count and creation time (featured logic)
    featured_highlights = sorted(
        all_highlights,
        key=lambda x: (x.view_count, x.created_at),
        reverse=True
    )[:limit]
    
    return HighlightListResponse(
        highlights=featured_highlights,
        total=len(featured_highlights),
        page=1,
        page_size=limit
    )
