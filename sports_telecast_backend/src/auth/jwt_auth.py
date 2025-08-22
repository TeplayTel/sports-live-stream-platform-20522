from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

# Use the available connection dependency instead of the missing session module
from ..database.connection import get_db
from ..database.repositories import UserRepository
from ..models.user import UserResponse

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

security = HTTPBearer()

# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

# PUBLIC_INTERFACE
def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

# PUBLIC_INTERFACE
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# PUBLIC_INTERFACE
async def verify_token(token: str, db: AsyncSession) -> Optional[UserResponse]:
    """
    Verify a JWT token and return the corresponding user as UserResponse.

    Args:
        token: The bearer token string.
        db: Async SQLAlchemy session provided by get_db.

    Returns:
        UserResponse if token is valid and user exists, otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            return None

        # Fetch user via repository (async)
        repo = UserRepository(db)
        db_user = await repo.get_user_by_id(user_id)
        if not db_user:
            return None

        # Map minimal fields present in current schema to UserResponse
        user_response = UserResponse(
            id=str(db_user.id),
            email=db_user.email,
            username=db_user.username,
            created_at=db_user.created_at,
        )
        return user_response

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        # Any other JWT error -> treat as invalid
        return None

# PUBLIC_INTERFACE
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    FastAPI dependency that returns the current authenticated user.

    Parameters:
        credentials: Extracted bearer token via HTTPBearer.
        db: Async DB session.

    Returns:
        UserResponse for the current user.

    Raises:
        HTTPException(401): If credentials cannot be validated.
    """
    token = credentials.credentials
    user = await verify_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# PUBLIC_INTERFACE
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserResponse]:
    """
    Optional authentication dependency.
    Returns UserResponse if authenticated, None otherwise.
    """
    if credentials is None:
        return None
    user = await verify_token(credentials.credentials, db)
    return user

# Legacy functions for backward compatibility

# PUBLIC_INTERFACE
def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Get current user ID from JWT token (legacy helper).

    Returns:
        str: user_id (sub) from the token.

    Raises:
        HTTPException(401) on invalid/expired tokens.
    """
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# PUBLIC_INTERFACE
def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[str]:
    """
    Optional authentication - returns user_id if authenticated, None otherwise (legacy helper).
    """
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None
