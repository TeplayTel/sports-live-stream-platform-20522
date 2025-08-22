from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user_optional
from ..database.connection import get_db

router = APIRouter(prefix="/categories", tags=["Categories"])

class SportCategory(BaseModel):
    """Sport category model"""
    category_id: str
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime

class SportCategoryListResponse(BaseModel):
    """Sport category list response model"""
    categories: List[SportCategory]
    total: int

# PUBLIC_INTERFACE
@router.get("/sports", response_model=SportCategoryListResponse, summary="Get sports categories")
def get_sport_categories(
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of sport categories

    Note:
    - This endpoint currently returns an empty list because category storage/service
      is not implemented in this codebase. The dependency injection is corrected
      to use an actual AsyncSession from get_db to avoid generator/session type errors.
    """
    try:
        return SportCategoryListResponse(
            categories=[],
            total=0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving categories: {str(e)}")
