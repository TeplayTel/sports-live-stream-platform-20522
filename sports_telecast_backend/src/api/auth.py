from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..models.user import UserCreate, UserLogin, UserResponse, TokenData, UserUpdate
from ..auth.jwt_auth import JWTAuth, get_current_user_id, get_current_user
from ..database.connection import get_db
from ..database.repositories import UserRepository
from ..database.schemas import convert_user_db_to_response
import bcrypt

router = APIRouter(prefix="/auth", tags=["Authentication"])

# PUBLIC_INTERFACE
@router.post("/register", response_model=TokenData, summary="Register new user")
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account
    
    Creates a new user account with the provided information and returns
    an access token for immediate authentication.
    """
    user_repo = UserRepository(db)
    
    # Check if user already exists
    existing_user = await user_repo.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = await user_repo.get_user_by_username(user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Hash password
    password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create new user
    user_db = await user_repo.create_user(user_data, password_hash)
    
    # Convert to response model
    user_response = convert_user_db_to_response(user_db)
    
    # Create access token
    access_token = JWTAuth.create_access_token(
        data={"sub": user_db.user_id, "email": user_db.email}
    )
    
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
    user_repo = UserRepository(db)
    
    # Get user by email
    user_db = await user_repo.get_user_by_email(login_data.email)
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not bcrypt.checkpw(login_data.password.encode('utf-8'), user_db.password_hash.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Convert to response model
    user_response = convert_user_db_to_response(user_db)
    
    # Create access token
    access_token = JWTAuth.create_access_token(
        data={"sub": user_db.user_id, "email": user_db.email}
    )
    
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
    user_repo = UserRepository(db)
    user_db = await user_repo.get_user_by_id(current_user_id)
    
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return convert_user_db_to_response(user_db)

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
    user_repo = UserRepository(db)
    
    # Update user 
    updated_user = await user_repo.update_user(current_user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return convert_user_db_to_response(updated_user)

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
    user_repo = UserRepository(db)
    user_db = await user_repo.get_user_by_id(current_user["sub"])
    
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Convert to response model
    user_response = convert_user_db_to_response(user_db)
    
    # Create new access token
    access_token = JWTAuth.create_access_token(
        data={"sub": user_db.user_id, "email": user_db.email}
    )
    
    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=1440 * 60,  # 24 hours in seconds
        user=user_response
    )
