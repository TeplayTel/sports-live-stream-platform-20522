from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user_optional
from ..database.session import get_db
from ..database.service import DatabaseService

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
    db: Session = Depends(get_db)
):
    """
    Get list of sport categories

    Returns all active sport categories for filtering and organization.
    """
    try:
        db_service = DatabaseService(db)
        categories = db_service.get_sport_categories()
        
        # Convert to Pydantic models
        category_list = []
        for category in categories:
            category_data = SportCategory(
                category_id=category.category_id,
                name=category.name,
                description=category.description,
                icon_url=category.icon_url,
                is_active=category.is_active,
                sort_order=category.sort_order,
                created_at=category.created_at
            )
            category_list.append(category_data)
        
        return SportCategoryListResponse(
            categories=category_list,
            total=len(category_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving categories: {str(e)}")
