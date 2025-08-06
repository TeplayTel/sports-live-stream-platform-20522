from fastapi import APIRouter, HTTPException, status, Depends
<<<<<<< HEAD
from sqlalchemy.orm import Session

from ..models.user import UserCreate, UserLogin, UserUpdate, UserResponse, TokenData
from ..auth.jwt_auth import create_access_token, get_password_hash, verify_password, get_current_user
from ..database.session import get_db
from ..database.service import DatabaseService
=======
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from passlib.context import CryptContext

from ..models.user import UserCreate, UserLogin, UserResponse, TokenData, UserUpdate
from ..auth.jwt_auth import JWTAuth, get_current_user_id, get_current_user
from ..database.connection import get_db
from ..database.repositories import UserRepository
from ..database.schemas import convert_user_db_to_response
<<<<<<< HEAD
import bcrypt
>>>>>>> cga-cg908b179b
=======
from sqlalchemy.ext.asyncio import AsyncSession
>>>>>>> cga-cg908b179b

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# PUBLIC_INTERFACE
@router.post("/register", response_model=TokenData, summary="Register new user")
<<<<<<< HEAD
<<<<<<< HEAD
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
=======
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
>>>>>>> cga-cg908b179b
=======
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
>>>>>>> cga-cg908b179b
    """
    Register a new user account

    Creates a new user account with the provided information and returns
    an access token for immediate authentication.
    """
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
    user_repo = UserRepository(db)
    
    # Check if user already exists
    existing_user = await user_repo.get_user_by_email(user_data.email)
=======
    repo = UserRepository(db)
    existing_user = await repo.get_user_by_email(user_data.email)
>>>>>>> cga-cg908b179b
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
<<<<<<< HEAD
    
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
    
=======

    password_hash = pwd_context.hash(user_data.password)
    user = await repo.create_user(user_data, password_hash=password_hash)

>>>>>>> cga-cg908b179b
    # Create access token
    access_token = JWTAuth.create_access_token(
        data={"sub": user_db.user_id, "email": user_db.email}
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
<<<<<<< HEAD
>>>>>>> cga-cg908b179b
=======
>>>>>>> cga-cg908b179b
    """
    Authenticate user and return access token

    Validates user credentials and returns a JWT token for API access.
    """
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
    user_repo = UserRepository(db)
    
    # Get user by email
    user_db = await user_repo.get_user_by_email(login_data.email)
    if not user_db:
=======
    repo = UserRepository(db)
    user = await repo.get_user_by_email(login_data.email)
    if not user:
>>>>>>> cga-cg908b179b
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
<<<<<<< HEAD
    
    # Verify password
    if not bcrypt.checkpw(login_data.password.encode('utf-8'), user_db.password_hash.encode('utf-8')):
=======

    # Password validation
    if not pwd_context.verify(login_data.password, user.password_hash):
>>>>>>> cga-cg908b179b
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
<<<<<<< HEAD
    
    # Convert to response model
    user_response = convert_user_db_to_response(user_db)
    
    # Create access token
=======

>>>>>>> cga-cg908b179b
    access_token = JWTAuth.create_access_token(
        data={"sub": user_db.user_id, "email": user_db.email}
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
<<<<<<< HEAD
>>>>>>> cga-cg908b179b
=======
>>>>>>> cga-cg908b179b
):
    """
    Get current authenticated user's profile

    Returns the profile information for the currently authenticated user.
    """
<<<<<<< HEAD
<<<<<<< HEAD
    return current_user

# PUBLIC_INTERFACE
@router.put("/me", response_model=UserResponse, summary="Update current user")
def update_current_user_profile(
    user_data: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
=======
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
=======
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
>>>>>>> cga-cg908b179b
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
<<<<<<< HEAD
>>>>>>> cga-cg908b179b
=======
>>>>>>> cga-cg908b179b
):
    """
    Update current authenticated user's profile

    Updates the profile information for the currently authenticated user.
    """
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
    user_repo = UserRepository(db)
    
    # Update user 
    updated_user = await user_repo.update_user(current_user_id, user_update)
    if not updated_user:
=======
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
>>>>>>> cga-cg908b179b
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
<<<<<<< HEAD
    
    return convert_user_db_to_response(updated_user)

# PUBLIC_INTERFACE
@router.post("/refresh", response_model=TokenData, summary="Refresh access token")
async def refresh_access_token(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
>>>>>>> cga-cg908b179b
):
    """
    Refresh the access token

    Issues a new access token for the authenticated user.
    """
<<<<<<< HEAD
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
=======
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
=======

>>>>>>> cga-cg908b179b
    access_token = JWTAuth.create_access_token(
        data={"sub": user_db.user_id, "email": user_db.email}
    )
    user_response = convert_user_db_to_response(user)

    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=1440 * 60,  # 24 hours in seconds
        user=user_response
    )
>>>>>>> cga-cg908b179b
