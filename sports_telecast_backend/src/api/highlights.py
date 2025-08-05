from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session

from ..models.match import Highlight, HighlightListResponse
from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user_optional
from ..database.session import get_db
from ..database.service import DatabaseService

router = APIRouter(prefix="/highlights", tags=["Highlights"])

# PUBLIC_INTERFACE
@router.get("/", response_model=HighlightListResponse, summary="Get highlights list")
def get_highlights(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    match_id: Optional[str] = Query(None, description="Filter by match ID"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of match highlights

    Returns video highlights from matches with optional filtering by match.
    Authentication is optional - may provide personalized results for authenticated users.
    """
    try:
        db_service = DatabaseService(db)
        offset = (page - 1) * page_size
        highlights, total = db_service.get_highlights(
            limit=page_size,
            offset=offset,
            match_id=match_id
        )
        
        # Convert to Pydantic models
        highlight_list = []
        for highlight in highlights:
            highlight_data = Highlight(
                highlight_id=highlight.highlight_id,
                match_id=highlight.match_id,
                title=highlight.title,
                description=highlight.description,
                video_url=highlight.video_url,
                thumbnail_url=highlight.thumbnail_url,
                duration=highlight.duration,
                tags=highlight.tags or [],
                view_count=highlight.view_count,
                created_at=highlight.created_at
            )
            highlight_list.append(highlight_data)
        
        return HighlightListResponse(
            highlights=highlight_list,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving highlights: {str(e)}")

# PUBLIC_INTERFACE
@router.get("/{highlight_id}", response_model=Highlight, summary="Get highlight details")
def get_highlight_details(
    highlight_id: str,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific highlight

    Returns comprehensive highlight data including video URL, description, and metadata.
    """
    try:
        db_service = DatabaseService(db)
        highlight = db_service.get_highlight_by_id(highlight_id)
        if not highlight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Highlight not found"
            )
        
        highlight_data = Highlight(
            highlight_id=highlight.highlight_id,
            match_id=highlight.match_id,
            title=highlight.title,
            description=highlight.description,
            video_url=highlight.video_url,
            thumbnail_url=highlight.thumbnail_url,
            duration=highlight.duration,
            tags=highlight.tags or [],
            view_count=highlight.view_count,
            created_at=highlight.created_at
        )
        
        return highlight_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving highlight: {str(e)}")

# PUBLIC_INTERFACE
@router.get("/featured/latest", response_model=HighlightListResponse, summary="Get latest featured highlights")
def get_featured_highlights(
    limit: int = Query(10, ge=1, le=50, description="Number of highlights to return"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get latest featured highlights

    Returns the most recent and popular highlights across all matches.
    Perfect for homepage or featured content sections.
    """
    try:
        db_service = DatabaseService(db)
        highlights = db_service.get_featured_highlights(limit=limit)
        
        # Convert to Pydantic models
        highlight_list = []
        for highlight in highlights:
            highlight_data = Highlight(
                highlight_id=highlight.highlight_id,
                match_id=highlight.match_id,
                title=highlight.title,
                description=highlight.description,
                video_url=highlight.video_url,
                thumbnail_url=highlight.thumbnail_url,
                duration=highlight.duration,
                tags=highlight.tags or [],
                view_count=highlight.view_count,
                created_at=highlight.created_at
            )
            highlight_list.append(highlight_data)
        
        return HighlightListResponse(
            highlights=highlight_list,
            total=len(highlight_list),
            page=1,
            page_size=len(highlight_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving featured highlights: {str(e)}")
