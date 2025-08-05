from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, List
from sqlalchemy.orm import Session

from ..models.match import Team
from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user_optional
from ..database.session import get_db
from ..database.service import DatabaseService
from pydantic import BaseModel

router = APIRouter(prefix="/teams", tags=["Teams"])

class TeamListResponse(BaseModel):
    """Team list response model"""
    teams: List[Team]
    total: int
    page: int
    page_size: int

# PUBLIC_INTERFACE
@router.get("/", response_model=TeamListResponse, summary="Get teams list")
def get_teams(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of teams

    Returns a list of all active teams with their information and logos.
    """
    try:
        db_service = DatabaseService(db)
        offset = (page - 1) * page_size
        teams, total = db_service.get_teams(limit=page_size, offset=offset)
        
        # Convert to Pydantic models
        team_list = []
        for team in teams:
            team_data = Team(
                team_id=team.team_id,
                name=team.name,
                short_name=team.short_name,
                logo_url=team.logo_url,
                colors=team.colors or {}
            )
            team_list.append(team_data)
        
        return TeamListResponse(
            teams=team_list,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving teams: {str(e)}")

# PUBLIC_INTERFACE
@router.get("/{team_id}", response_model=Team, summary="Get team details")
def get_team_details(
    team_id: str,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific team

    Returns comprehensive team data including logo, colors, and metadata.
    """
    try:
        db_service = DatabaseService(db)
        team = db_service.get_team_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        team_data = Team(
            team_id=team.team_id,
            name=team.name,
            short_name=team.short_name,
            logo_url=team.logo_url,
            colors=team.colors or {}
        )
        
        return team_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving team: {str(e)}")
