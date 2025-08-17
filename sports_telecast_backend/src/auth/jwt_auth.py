from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

# Ensure environment variables from a .env file are available even if this module is imported standalone
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # Optional in production environments
    pass

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

# Default mock token string that should ALWAYS be accepted in development/test
DEFAULT_MOCK_JWT_TOKEN = "mock-superuser-jwt-token"

def _normalize_token(value: Optional[str]) -> str:
    """
    Normalize a token string by:
      - handling None safely
      - trimming whitespace
      - removing wrapping single/double quotes often present in envs
      - stripping accidental 'Bearer ' prefixes if provided incorrectly
    """
    if not value:
        return ""
    s = value.strip()
    if s.lower().startswith("bearer "):
        s = s[7:]
    # Strip wrapping quotes if any
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    return s.strip()

def _get_configured_mock_token() -> str:
    """
    Read MOCK_JWT_TOKEN from environment on-demand and normalize it.
    If empty or unset, falls back to DEFAULT_MOCK_JWT_TOKEN.
    """
    configured = _normalize_token(os.getenv("MOCK_JWT_TOKEN", ""))
    return configured or DEFAULT_MOCK_JWT_TOKEN

security = HTTPBearer()


class JWTAuth:
    """JWT Authentication handler with mock-token support for testing."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a signed JWT access token"""
        to_encode = data.copy()
        expire = (datetime.utcnow() + expires_delta) if expires_delta else (datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def _mock_payload() -> Dict[str, Any]:
        """Internal: produce a privileged payload for the mock token."""
        now = datetime.utcnow()
        return {
            "sub": "00000000-0000-0000-0000-000000000000",
            "email": "mockadmin@example.com",
            "username": "mockadmin",
            "role": "admin",                  # single role
            "roles": ["admin", "moderator"],  # multi-role for compatibility
            "scopes": ["*"],
            "permissions": ["*"],
            "is_admin": True,
            "iat": now,
            "exp": now + timedelta(days=3650),  # ~10 years
            "iss": "sports-telecast-backend",
            "aud": "public",
        }

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token; accept a special mock token as universally valid.

        Acceptance rules (in this order):
          1) Accept if token equals the configured MOCK_JWT_TOKEN (normalized)
          2) Accept if token equals the DEFAULT_MOCK_JWT_TOKEN ("mock-superuser-jwt-token")
          3) Otherwise, verify as a signed JWT with SECRET_KEY/ALGORITHM
        """
        incoming = _normalize_token(token)
        if not incoming:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        configured_mock = _get_configured_mock_token()
        # Accept either the configured value or the default constant to avoid .env mismatch surprises
        if incoming == configured_mock or incoming == _normalize_token(DEFAULT_MOCK_JWT_TOKEN):
            return JWTAuth._mock_payload()

        try:
            payload = jwt.decode(incoming, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.PyJWTError:
            # Covers DecodeError, InvalidTokenError, etc.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception:
            # Fallback for any other error conditions
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


def _extract_user_id_from_payload(payload: Dict[str, Any]) -> str:
    """Helper to normalize user id extraction from JWT payload."""
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        # Some tokens might use a different field name
        user_id = payload.get("user_id") or payload.get("uid")
    return user_id or ""


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Get current user ID from JWT token.
    This is a dependency that can be used in FastAPI endpoints.
    Accepts the special MOCK_JWT_TOKEN as an admin token.
    """
    try:
        payload = JWTAuth.verify_token(credentials.credentials)
        user_id = _extract_user_id_from_payload(payload)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Get current user information from JWT token.
    This is a dependency that can be used in FastAPI endpoints.
    Accepts the special MOCK_JWT_TOKEN as an admin token.
    """
    try:
        payload = JWTAuth.verify_token(credentials.credentials)
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[str]:
    """
    Optional authentication - returns user_id if authenticated, None otherwise.
    Accepts the special MOCK_JWT_TOKEN as an admin token.
    """
    if credentials is None:
        return None

    try:
        payload = JWTAuth.verify_token(credentials.credentials)
        return _extract_user_id_from_payload(payload)
    except Exception:
        return None


# PUBLIC_INTERFACE
def get_mock_bearer_token() -> str:
    """Return the mock Bearer JWT token that the backend accepts for all roles in testing."""
    return _get_configured_mock_token()
