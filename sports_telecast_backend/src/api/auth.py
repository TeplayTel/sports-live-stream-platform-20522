from fastapi import APIRouter, HTTPException, status, Body, Request, Depends, Header, Query
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import UserLogin, UserResponse, TokenData, UserUpdate
from ..models.register import RegisterRequest, MinimalUserResponse
from ..database.connection import get_db
from ..database.repositories import UserRepository
from ..database.schemas import convert_user_db_to_response
from .utils import get_trusted_user
import logging
import types

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=MinimalUserResponse,
    summary="Register a new user",
)
async def register_user(
    payload: RegisterRequest = Body(..., description="Registration payload"),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.

    Validates that email and username are unique, securely hashes the password,
    creates a new user (UUIDv4 as text), and returns minimal user info.

    Parameters:
    - payload.email: EmailStr - must be unique
    - payload.username: str - must be unique
    - payload.password: str - will be hashed and not returned

    Returns:
    - MinimalUserResponse: { id, email, username, created_at }
    """
    # Diagnostic checks to ensure FastAPI injected a real AsyncSession
    logger.debug(f"[register_user] Received db object type={type(db)!r}")
    print(f"[DEBUG] register_user: db type={type(db)} is_asyncsession={isinstance(db, AsyncSession)}")  # visible in logs/console
    if isinstance(db, (types.AsyncGeneratorType, types.GeneratorType)):
        # This indicates an incorrect use like passing get_db without Depends
        raise HTTPException(status_code=500, detail="Internal error: database dependency yielded a generator, expected AsyncSession")
    if not isinstance(db, AsyncSession):
        raise HTTPException(status_code=500, detail=f"Internal error: expected AsyncSession, got {type(db)}")

    repo = UserRepository(db)

    # Uniqueness checks
    existing_by_email = await repo.get_user_by_email(payload.email)
    if existing_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    existing_by_username = await repo.get_user_by_username(payload.username)
    if existing_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Securely hash the password
    password_hash = pwd_context.hash(payload.password)

    # Create user using minimal schema
    from ..models.user import UserCreate  # reuse existing DTO, only minimal fields used
    created = await repo.create_user(
        user_data=UserCreate(email=payload.email, username=payload.username, password=payload.password),
        password_hash=password_hash,
    )

    # Build minimal response
    return MinimalUserResponse(
        id=str(created.id),
        email=created.email,
        username=created.username,
        created_at=created.created_at.isoformat() if getattr(created, "created_at", None) else ""
    )

# PUBLIC_INTERFACE
@router.post("/login", response_model=TokenData, summary="User login")
async def login_user(
    login_data: UserLogin = Body(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    User login with trusted userId/userData (no auth).

    - login_data: UserLogin request with email and password.
    - returns: TokenData (JWT access token + user info)
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_email(login_data.email)
    if not user or not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Build a proper UserResponse Pydantic model (not a raw dict)
    user_dict = convert_user_db_to_response(user)  # returns a dict with keys matching UserResponse
    user_model = UserResponse(**user_dict)

    return TokenData(
        access_token="mock_token",
        token_type="bearer",
        expires_in=86400,
        user=user_model
    )

# PUBLIC_INTERFACE
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_current_user_profile(
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(
        default=None,
        alias="X-User-Id",
        description="Trusted user ID provided by a proxy/frontend. If provided, takes precedence."
    ),
    user_id_q: str | None = Query(
        default=None,
        alias="user_id",
        description="User ID as query parameter for testing via Swagger UI when header injection is not possible."
    )
):
    """
    Get the current trusted/mock user's profile.

    This endpoint allows specifying the user in multiple ways for development and testing:
    - X-User-Id header
    - user_id query parameter
    - If neither is provided, it will fallback to extracting from request using utility (headers/query/body).

    Parameters:
    - X-User-Id (header): Optional user identifier header.
    - user_id (query): Optional user identifier query parameter.

    Returns:
    - UserResponse: The resolved user's profile.

    Errors:
    - 400: Missing user identifier.
    - 404: User not found.
    """
    # Prefer explicit parameters for clearer Swagger experience
    user_id = x_user_id or user_id_q
    if not user_id:
        # Fallback to existing extraction logic
        user_id, _ = get_trusted_user(request)

    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user identifier. Provide X-User-Id header or user_id query param.")

    repo = UserRepository(db)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_response = convert_user_db_to_response(user)
    return user_response

# PUBLIC_INTERFACE
@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
)
async def update_current_user_profile(
    user_update: UserUpdate = Body(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(
        default=None,
        alias="X-User-Id",
        description="Trusted user ID provided by a proxy/frontend. If provided, takes precedence."
    ),
    user_id_q: str | None = Query(
        default=None,
        alias="user_id",
        description="User ID as query parameter for testing via Swagger UI when header injection is not possible."
    )
):
    """
    Update the trusted/mock user's profile.

    You can provide the user via:
    - X-User-Id (header)
    - user_id (query)
    If neither is provided, utility will attempt to read from request.

    Parameters:
    - user_update: UserUpdate payload with allowed fields.
    - X-User-Id (header): Optional user identifier header.
    - user_id (query): Optional user identifier query parameter.

    Returns:
    - UserResponse: Updated user profile.

    Errors:
    - 400: Missing user identifier.
    - 404: User not found.
    """
    user_id = x_user_id or user_id_q
    if not user_id:
        user_id, _ = get_trusted_user(request)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user identifier. Provide X-User-Id header or user_id query param.")

    repo = UserRepository(db)
    user = await repo.update_user(user_id, user_update)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_response = convert_user_db_to_response(user)
    return user_response

# PUBLIC_INTERFACE
@router.post(
    "/refresh",
    response_model=TokenData,
    summary="Refresh access token",
)
async def refresh_access_token(
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(
        default=None,
        alias="X-User-Id",
        description="Trusted user ID provided by a proxy/frontend. If provided, takes precedence."
    ),
    user_id_q: str | None = Query(
        default=None,
        alias="user_id",
        description="User ID as query parameter for testing via Swagger UI when header injection is not possible."
    )
):
    """
    Refresh the access token (dummy for mock mode).

    You can provide the user via:
    - X-User-Id (header)
    - user_id (query)

    Returns:
    - TokenData (JWT access token + user info)

    Errors:
    - 400: Missing user identifier.
    - 404: User not found.
    """
    user_id = x_user_id or user_id_q
    if not user_id:
        user_id, _ = get_trusted_user(request)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user identifier. Provide X-User-Id header or user_id query param.")

    repo = UserRepository(db)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_dict = convert_user_db_to_response(user)
    user_model = UserResponse(**user_dict)
    return TokenData(
        access_token="mock_token",
        token_type="bearer",
        expires_in=86400,
        user=user_model
    )
