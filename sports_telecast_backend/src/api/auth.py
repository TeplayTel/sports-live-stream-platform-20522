from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from passlib.context import CryptContext

from ..models.user import UserCreate, UserLogin, UserResponse, TokenData, UserUpdate
from ..auth.jwt_auth import JWTAuth, get_current_user_id, get_current_user
from ..database.connection import get_db
from ..database.repositories import UserRepository
from ..database.schemas import convert_user_db_to_response
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# PUBLIC_INTERFACE
@router.post("/register", response_model=TokenData, summary="Register new user")
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account

    Creates a new user account with the provided information and returns
    an access token for immediate authentication.
    """
    repo = UserRepository(db)
    existing_user = await repo.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    password_hash = pwd_context.hash(user_data.password)
    user = await repo.create_user(user_data, password_hash=password_hash)

    # Create access token
    access_token = JWTAuth.create_access_token(
        data={"sub": user.user_id, "email": user.email}
    )
    user_response = convert_user_db_to_response(user)

    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=1440 * 60,  # 24 hours in seconds
        user=user_response
    )

# PUBLIC_INTERFACE
@router.post("/login", response_model=TokenData, summary="User login")
async def login_user(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return access token

    Validates user credentials and returns a JWT token for API access.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Password validation
    if not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = JWTAuth.create_access_token(
        data={"sub": user.user_id, "email": user.email}
    )
    user_response = convert_user_db_to_response(user)

    return TokenData(
        access_token=access_token,
        token_type="bearer", 
        expires_in=1440 * 60,  # 24 hours in seconds
        user=user_response
    )

# PUBLIC_INTERFACE
@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_current_user_profile(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user's profile

    Returns the profile information for the currently authenticated user.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_response = convert_user_db_to_response(user)
    return user_response

# PUBLIC_INTERFACE
@router.put("/me", response_model=UserResponse, summary="Update current user")
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current authenticated user's profile

    Updates the profile information for the currently authenticated user.
    """
    repo = UserRepository(db)
    user = await repo.update_user(current_user_id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_response = convert_user_db_to_response(user)
    return user_response

# PUBLIC_INTERFACE
@router.post("/refresh", response_model=TokenData, summary="Refresh access token")
async def refresh_access_token(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh the access token

    Issues a new access token for the authenticated user.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_id(current_user["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    access_token = JWTAuth.create_access_token(
        data={"sub": user.user_id, "email": user.email}
    )
    user_response = convert_user_db_to_response(user)

    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=1440 * 60,  # 24 hours in seconds
        user=user_response
    )
