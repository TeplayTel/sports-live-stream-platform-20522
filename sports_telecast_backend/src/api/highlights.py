from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
<<<<<<< HEAD
from sqlalchemy.orm import Session

from ..models.match import Highlight, HighlightListResponse
<<<<<<< HEAD
from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user_optional
from ..database.session import get_db
from ..database.service import DatabaseService
=======
from ..auth.jwt_auth import optional_auth
from ..database.connection import get_db
from ..database.repositories import HighlightRepository
from ..database.schemas import convert_highlight_db_to_pydantic
>>>>>>> cga-cg908b179b
=======
from sqlalchemy.ext.asyncio import AsyncSession

from models.match import Highlight, HighlightListResponse
from auth.jwt_auth import optional_auth
from database import get_db
from database.repositories import HighlightRepository
from database.schemas import convert_highlight_db_to_pydantic
>>>>>>> cga-cg908b179b

router = APIRouter(prefix="/highlights", tags=["Highlights"])

# PUBLIC_INTERFACE
@router.get("/", response_model=HighlightListResponse, summary="Get highlights list")
async def get_highlights(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    match_id: Optional[str] = Query(None, description="Filter by match ID"),
<<<<<<< HEAD
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
=======
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get paginated list of match highlights

    Returns video highlights from matches with optional filtering by match.
    Authentication is optional - may provide personalized results for authenticated users.
    """
<<<<<<< HEAD
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
=======
    highlight_repo = HighlightRepository(db)
    offset = (page - 1) * page_size
    highlight_repo = HighlightRepository(db_session)
    
<<<<<<< HEAD
    highlights_db = await highlight_repo.get_highlights(
        limit=page_size,
        offset=offset,
=======
    # Get highlights with pagination
    highlights_db = await highlight_repo.get_highlights(
        limit=page_size, 
        offset=offset, 
>>>>>>> cga-cg908b179b
        match_id=match_id
    )
    
    # Convert to Pydantic models
<<<<<<< HEAD
    highlights = [convert_highlight_db_to_pydantic(highlight_db) for highlight_db in highlights_db]
    
    # For total count, this is a simplified approach
    total = len(highlights) if len(highlights) < page_size else page_size * page + 1
=======
    highlights = [convert_highlight_db_to_pydantic(highlight) for highlight in highlights_db]
    
    # Get total count for pagination
    all_highlights_db = await highlight_repo.get_highlights(limit=1000, offset=0, match_id=match_id)
    total = len(all_highlights_db)
>>>>>>> cga-cg908b179b
    
    return HighlightListResponse(
        highlights=highlights,
        total=total,
        page=page,
        page_size=page_size
    )
>>>>>>> cga-cg908b179b

# PUBLIC_INTERFACE
@router.get("/{highlight_id}", response_model=Highlight, summary="Get highlight details")
async def get_highlight_details(
    highlight_id: str,
<<<<<<< HEAD
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
=======
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get detailed information about a specific highlight

    Returns comprehensive highlight data including video URL, description, and metadata.
    """
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
    highlight_repo = HighlightRepository(db)
    highlight_db = await highlight_repo.get_highlight_by_id(highlight_id)
    
=======
    highlight_repo = HighlightRepository(db_session)
    highlight_db = await highlight_repo.get_highlight_by_id(highlight_id)
>>>>>>> cga-cg908b179b
    if not highlight_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Highlight not found"
        )
    
<<<<<<< HEAD
    # Increment view count (in a real app, you might want to track unique views)
    highlight_db.view_count += 1
    await db.commit()
    
    return convert_highlight_db_to_pydantic(highlight_db)
>>>>>>> cga-cg908b179b
=======
    # Convert to Pydantic model
    highlight = convert_highlight_db_to_pydantic(highlight_db)
    return highlight
>>>>>>> cga-cg908b179b

# PUBLIC_INTERFACE
@router.get("/featured/latest", response_model=HighlightListResponse, summary="Get latest featured highlights")
async def get_featured_highlights(
    limit: int = Query(10, ge=1, le=50, description="Number of highlights to return"),
<<<<<<< HEAD
<<<<<<< HEAD
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
=======
    user_id: Optional[str] = Depends(optional_auth),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
=======
    user_id: Optional[str] = Depends(optional_auth),
    db_session: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Get latest featured highlights

    Returns the most recent and popular highlights across all matches.
    Perfect for homepage or featured content sections.
    """
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
    highlight_repo = HighlightRepository(db)
    featured_highlights_db = await highlight_repo.get_featured_highlights(limit=limit)
    
    # Convert to Pydantic models
    featured_highlights = [convert_highlight_db_to_pydantic(highlight_db) for highlight_db in featured_highlights_db]
=======
    highlight_repo = HighlightRepository(db_session)
    
    # Get featured highlights using repository method
    featured_highlights_db = await highlight_repo.get_featured_highlights(limit=limit)
    
    # Convert to Pydantic models
    featured_highlights = [convert_highlight_db_to_pydantic(highlight) for highlight in featured_highlights_db]
>>>>>>> cga-cg908b179b
    
    return HighlightListResponse(
        highlights=featured_highlights,
        total=len(featured_highlights),
        page=1,
        page_size=limit
    )
>>>>>>> cga-cg908b179b
