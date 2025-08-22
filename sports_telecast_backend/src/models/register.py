from pydantic import BaseModel, EmailStr, Field

# PUBLIC_INTERFACE
class RegisterRequest(BaseModel):
    """Request payload for user registration: minimal required fields."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Desired username")
    password: str = Field(..., min_length=8, description="User password (plain text; will be hashed)")

# PUBLIC_INTERFACE
class MinimalUserResponse(BaseModel):
    """Minimal user response following the minimal users table schema."""
    id: str = Field(..., description="User ID (UUIDv4 as text)")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Username")
    created_at: str = Field(..., description="Account creation timestamp (ISO)")
