from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from ..models.user import UserCreate, UserLogin, UserUpdate, UserResponse, TokenData
from ..auth.jwt_auth import create_access_token, get_password_hash, verify_password, get_current_user
from ..database.session import get_db
from ..database.service import DatabaseService

router = APIRouter(prefix="/auth", tags=["Authentication"])

# PUBLIC_INTERFACE
@router.post("/register", response_model=TokenData, summary="Register new user")
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account

    Creates a new user account with the provided information and returns
    an access token for immediate authentication.
    """
    try:
        db_service = DatabaseService(db)
        
        # Check if user already exists
        existing_user = db_service.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash the password
        password_hash = get_password_hash(user_data.password)
        
        # Create user
        db_user = db_service.create_user(user_data, password_hash)
        
        # Create access token
        access_token = create_access_token(data={"sub": db_user.user_id})
        
        # Convert to response model
        user_response = UserResponse(
            user_id=db_user.user_id,
            email=db_user.email,
            username=db_user.username,
            full_name=db_user.full_name,
            avatar_url=db_user.avatar_url,
            role=db_user.role,
            preferences=db_user.preferences or {},
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
        
        return TokenData(
            access_token=access_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user=user_response
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

# PUBLIC_INTERFACE
@router.post("/login", response_model=TokenData, summary="User login")
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access token

    Validates user credentials and returns a JWT token for API access.
    """
    try:
        db_service = DatabaseService(db)
        
        # Get user by email
        db_user = db_service.get_user_by_email(user_data.email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(user_data.password, db_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": db_user.user_id})
        
        # Convert to response model
        user_response = UserResponse(
            user_id=db_user.user_id,
            email=db_user.email,
            username=db_user.username,
            full_name=db_user.full_name,
            avatar_url=db_user.avatar_url,
            role=db_user.role,
            preferences=db_user.preferences or {},
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
        
        return TokenData(
            access_token=access_token,
            token_type="bearer", 
            expires_in=1800,  # 30 minutes
            user=user_response
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

# PUBLIC_INTERFACE
@router.get("/me", response_model=UserResponse, summary="Get current user")
def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get current authenticated user's profile

    Returns the profile information for the currently authenticated user.
    """
    return current_user

# PUBLIC_INTERFACE
@router.put("/me", response_model=UserResponse, summary="Update current user")
def update_current_user_profile(
    user_data: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current authenticated user's profile

    Updates the profile information for the currently authenticated user.
    """
    try:
        db_service = DatabaseService(db)
        
        # Update user
        updated_user = db_service.update_user(current_user.user_id, user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Convert to response model
        user_response = UserResponse(
            user_id=updated_user.user_id,
            email=updated_user.email,
            username=updated_user.username,
            full_name=updated_user.full_name,
            avatar_url=updated_user.avatar_url,
            role=updated_user.role,
            preferences=updated_user.preferences or {},
            is_active=updated_user.is_active,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at
        )
        
        return user_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

# PUBLIC_INTERFACE
@router.post("/refresh", response_model=TokenData, summary="Refresh access token")
def refresh_access_token(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Refresh the access token

    Issues a new access token for the authenticated user.
    """
    try:
        # Create new access token
        access_token = create_access_token(data={"sub": current_user.user_id})
        
        return TokenData(
            access_token=access_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user=current_user
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing token: {str(e)}")
