from fastapi import APIRouter, HTTPException, status, Body, Request
from passlib.context import CryptContext

from ..models.user import UserLogin, UserResponse, TokenData, UserUpdate
from ..database.connection import get_db
from ..database.repositories import UserRepository
from ..database.schemas import convert_user_db_to_response
from sqlalchemy.ext.asyncio import AsyncSession
from .utils import get_trusted_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



# PUBLIC_INTERFACE
@router.post("/login", response_model=TokenData, summary="User login")
async def login_user(login_data: UserLogin = Body(...), request: Request = None, db: AsyncSession = None):
    """
    User login with trusted userId/userData (no auth).
    """
    db = db or await get_db().__anext__()
    repo = UserRepository(db)
    user = await repo.get_user_by_email(login_data.email)
    if not user or not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    user_response = convert_user_db_to_response(user)
    return TokenData(
        access_token="mock_token",
        token_type="bearer",
        expires_in=86400,
        user=user_response
    )

# PUBLIC_INTERFACE
@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_current_user_profile(request: Request = None, db: AsyncSession = None):
    """
    Get the current trusted/mock user's profile (from headers/params/body).
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    repo = UserRepository(db)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_response = convert_user_db_to_response(user)
    return user_response

# PUBLIC_INTERFACE
@router.put("/me", response_model=UserResponse, summary="Update current user")
async def update_current_user_profile(
    user_update: UserUpdate = Body(...),
    request: Request = None,
    db: AsyncSession = None
):
    """
    Update the trusted/mock user's profile.
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    repo = UserRepository(db)
    user = await repo.update_user(user_id, user_update)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_response = convert_user_db_to_response(user)
    return user_response

# PUBLIC_INTERFACE
@router.post("/refresh", response_model=TokenData, summary="Refresh access token")
async def refresh_access_token(request: Request = None, db: AsyncSession = None):
    """
    Refresh the access token (dummy for mock mode).
    """
    db = db or await get_db().__anext__()
    user_id, _ = get_trusted_user(request)
    repo = UserRepository(db)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_response = convert_user_db_to_response(user)
    return TokenData(
        access_token="mock_token",
        token_type="bearer",
        expires_in=86400,
        user=user_response
    )
