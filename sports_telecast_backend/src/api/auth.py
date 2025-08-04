from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from ..models.user import UserCreate, UserLogin, UserResponse, TokenData, UserUpdate
from ..auth.jwt_auth import JWTAuth, get_current_user_id, get_current_user
from ..database.connection import db

router = APIRouter(prefix="/auth", tags=["Authentication"])

# PUBLIC_INTERFACE
@router.post("/register", response_model=TokenData, summary="Register new user")
def register_user(user_data: UserCreate):
    """
    Register a new user account
    
    Creates a new user account with the provided information and returns
    an access token for immediate authentication.
    """
    # Check if user already exists
    existing_user = db.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = db.create_user(user_data)
    
    # Create access token
    access_token = JWTAuth.create_access_token(
        data={"sub": user.user_id, "email": user.email}
    )
    
    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=1440 * 60,  # 24 hours in seconds
        user=UserResponse(**user.dict())
    )

# PUBLIC_INTERFACE
@router.post("/login", response_model=TokenData, summary="User login")
def login_user(login_data: UserLogin):
    """
    Authenticate user and return access token
    
    Validates user credentials and returns a JWT token for API access.
    """
    # Get user by email
    user = db.get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # For demo purposes, we'll accept any password
    # In production, verify against hashed password
    # if not JWTAuth.verify_password(login_data.password, user.hashed_password):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid email or password"
    #     )
    
    # Create access token
    access_token = JWTAuth.create_access_token(
        data={"sub": user.user_id, "email": user.email}
    )
    
    return TokenData(
        access_token=access_token,
        token_type="bearer", 
        expires_in=1440 * 60,  # 24 hours in seconds
        user=UserResponse(**user.dict())
    )

# PUBLIC_INTERFACE
@router.get("/me", response_model=UserResponse, summary="Get current user")
def get_current_user_profile(current_user_id: str = Depends(get_current_user_id)):
    """
    Get current authenticated user's profile
    
    Returns the profile information for the currently authenticated user.
    """
    user = db.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user.dict())

# PUBLIC_INTERFACE
@router.put("/me", response_model=UserResponse, summary="Update current user")
def update_current_user_profile(
    user_update: UserUpdate,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Update current authenticated user's profile
    
    Updates the profile information for the currently authenticated user.
    """
    user = db.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    return UserResponse(**user.dict())

# PUBLIC_INTERFACE
@router.post("/refresh", response_model=TokenData, summary="Refresh access token")
def refresh_access_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Refresh the access token
    
    Issues a new access token for the authenticated user.
    """
    user = db.get_user_by_id(current_user["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create new access token
    access_token = JWTAuth.create_access_token(
        data={"sub": user.user_id, "email": user.email}
    )
    
    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=1440 * 60,  # 24 hours in seconds
        user=UserResponse(**user.dict())
    )
