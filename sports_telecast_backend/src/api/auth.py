from fastapi import APIRouter, HTTPException, status, Body, Request, Depends
from passlib.context import CryptContext

from ..models.user import UserLogin, UserResponse, TokenData, UserUpdate, UserCreate
from ..database.connection import get_db
from ..database.repositories import UserRepository
from ..database.schemas import convert_user_db_to_response
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth.jwt_auth import JWTAuth, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user_id

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



# PUBLIC_INTERFACE
@router.post("/login", response_model=TokenData, summary="User login")
async def login_user(
    login_data: UserLogin = Body(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    User login with trusted userId/userData (no auth).

    - **login_data**: UserLogin request with email and password.
    - **returns**: TokenData (JWT access token + user info)
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_email(login_data.email)
    if not user or not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    user_response = convert_user_db_to_response(user)
    # Create a real JWT access token
    access_token = JWTAuth.create_access_token(
        data={
            "sub": str(user.user_id),
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
        }
    )
    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response,
    )

# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=TokenData,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Registers a new user with email, username, and password. Returns an access token and user info.",
    responses={
        201: {"description": "User created and token returned"},
        409: {"description": "Email or username already registered"},
        422: {"description": "Validation error"},
    },
)
async def register_user(
    user_data: UserCreate = Body(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.

    - user_data: UserCreate payload containing email, username, password, and optional full_name
    - returns: TokenData (mock JWT access token + created user info)

    Validation rules:
    - Email must be unique
    - Username must be unique
    - Password is hashed using bcrypt via passlib
    """
    # Local import to avoid circular import at module load and to keep dependency surface small
    from sqlalchemy.exc import IntegrityError  # noqa: WPS433

    repo = UserRepository(db)

    # Pre-check for duplicate email/username
    existing_by_email = await repo.get_user_by_email(user_data.email)
    if existing_by_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    existing_by_username = await repo.get_user_by_username(user_data.username)
    if existing_by_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Hash the password
    password_hash = pwd_context.hash(user_data.password)

    # Attempt to create user; handle race-condition via integrity error
    try:
        created_user = await repo.create_user(user_data, password_hash)
    except IntegrityError:
        # Rollback the transaction to clean the session state
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )

    # Build response token and user payload
    user_response = convert_user_db_to_response(created_user)
    # Create a real JWT access token for the newly registered user
    # role.value is guaranteed lowercase by repository normalization and DB enum
    access_token = JWTAuth.create_access_token(
        data={
            "sub": str(created_user.user_id),
            "email": created_user.email,
            "username": created_user.username,
            "role": created_user.role.value,
        }
    )
    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response,
    )

# PUBLIC_INTERFACE
@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get the current user's profile derived from the JWT token (Bearer authentication).

    - returns: UserResponse profile
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_response = convert_user_db_to_response(user)
    return user_response

# PUBLIC_INTERFACE
@router.put("/me", response_model=UserResponse, summary="Update current user")
async def update_current_user_profile(
    user_update: UserUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Update the current user's profile using identity from the JWT token.

    - user_update: UserUpdate payload
    - returns: UserResponse updated profile
    """
    repo = UserRepository(db)
    user = await repo.update_user(current_user_id, user_update)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_response = convert_user_db_to_response(user)
    return user_response

# PUBLIC_INTERFACE
@router.post("/refresh", response_model=TokenData, summary="Refresh access token")
async def refresh_access_token(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Refresh the access token using the current authenticated user.

    - returns: TokenData (new JWT access token + user info)
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_response = convert_user_db_to_response(user)
    access_token = JWTAuth.create_access_token(
        data={
            "sub": str(user.user_id),
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
        }
    )
    return TokenData(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )
