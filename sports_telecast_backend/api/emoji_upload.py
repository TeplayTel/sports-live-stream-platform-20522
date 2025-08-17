import os
import uuid
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from typing import Optional, Union, List
from dotenv import load_dotenv
from src.auth.jwt_auth import JWTAuth

# Load environment variables from .env for storage path (if running locally)
load_dotenv()

# PUBLIC_INTERFACE
def get_storage_dir():
    """Returns the directory path for storing emoji assets, from .env or config."""
    return os.getenv("EMOJI_ASSETS_DIR", "emoji_assets")

# PUBLIC_INTERFACE
def get_cdn_base_url():
    """Returns the base CDN URL for constructing emoji image URLs."""
    return os.getenv("EMOJI_CDN_BASE_URL", "https://cdn.placeholderdomain.com/emojis/")

# Database setup (reuse FastAPI settings if available)
DATABASE_URL = os.getenv("POSTGRES_URL", "sqlite:///./test.db") # fallback for local setup/demo
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EmojiAsset(Base):
    __tablename__ = "emoji_assets"
    emoji_id = Column(String(36), primary_key=True, index=True)
    emoji_type = Column(String(32), nullable=False)
    file_location = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create the table if it does not exist
Base.metadata.create_all(bind=engine)

# Response schemas
class EmojiAssetResponseModel(BaseModel):
    emoji_id: str = Field(..., description="Unique emoji identifier")
    emoji_type: str = Field(..., description="Emoji type/category (e.g. clap)")
    image_url: str = Field(..., description="URL to the uploaded emoji image")

class UploadEmojiResponse(BaseModel):
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Operation outcome")
    emoji: EmojiAssetResponseModel

router = APIRouter()

# PUBLIC_INTERFACE
@router.post(
    "/fan-engagement/emoji/v1/upload",
    summary="Upload a new emoji asset for user reactions",
    description=(
        "Upload an emoji image (admin only for now), store file, register in DB, and return details.\n"
        "Auth: Requires Authorization: Bearer <ADMIN_UPLOAD_TOKEN>."
    ),
    response_model=UploadEmojiResponse,
    responses={
        401: {"description": "Missing or invalid authorization header"},
        403: {"description": "Insufficient privileges"},
        422: {"description": "Validation error (invalid emojiType or missing file)"}
    },
    tags=["Fan Engagement - Emojis"]
)
async def upload_emoji(
    emojiType: str = Form(..., description="Type/category of the emoji (e.g. clap, fire)"),
    emojiImage: UploadFile = File(None, description="Emoji image file (PNG preferred). Preferred key: emojiImage"),
    request: Request = None,
    authorization: Optional[str] = Header(None, alias="Authorization", description="Bearer admin token"),
):
    """
    Uploads a new emoji asset to the platform (admin only for MVP).

    - Validates and saves the emoji image.
    - Inserts a new record into emoji_assets.
    - Returns emoji asset details.

    Auth:
      - Requires 'Authorization: Bearer <ADMIN_UPLOAD_TOKEN>' header.
      - ADMIN_UPLOAD_TOKEN is read from environment (.env). Defaults to 'admin' for local dev.

    Request (multipart/form-data):
      - emojiType: string
      - emojiImage: file (binary). As a compatibility fallback, 'file' is also accepted.

    Headers:
      - Authorization: Bearer <admin-token>
    """
    # Placeholder admin check (replace with JWT roles in future)
    admin_token = os.getenv("ADMIN_UPLOAD_TOKEN", "admin")

    # Validate Authorization header robustly
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    token_value = authorization.split(" ", 1)[1]

    # Authorize if the token matches the configured ADMIN token
    authorized = token_value == admin_token

    # Or authorize if it's a (mock) JWT with admin privileges
    if not authorized:
        try:
            payload = JWTAuth.verify_token(token_value)
            role = payload.get("role")
            roles = payload.get("roles", [])
            is_admin = payload.get("is_admin", False)
            scopes = payload.get("scopes", [])
            permissions = payload.get("permissions", [])

            def _has_admin(r: Union[str, List[str]]) -> bool:
                if isinstance(r, str):
                    return r.lower() == "admin"
                if isinstance(r, list):
                    return any(isinstance(x, str) and x.lower() == "admin" for x in r)
                return False

            if is_admin or _has_admin(role) or _has_admin(roles) or ("*" in scopes) or ("*" in permissions):
                authorized = True
        except HTTPException:
            authorized = False
        except Exception:
            authorized = False

    if not authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")

    # Validate emojiType (optional: match to allowed values)
    if not emojiType or not emojiType.isidentifier() or len(emojiType) > 32:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid emojiType")

    # Choose the provided file (support both 'emojiImage' and 'file' keys for compatibility)
    # To avoid validation errors when 'file' is sent as a string by some clients,
    # we only declare 'emojiImage' in the function signature and parse 'file' manually from the form.
    image_file = emojiImage
    if image_file is None:
        try:
            form = await request.form()
            candidate = form.get("file")
            if isinstance(candidate, UploadFile):
                image_file = candidate
        except Exception:
            # If parsing fails or candidate is not an UploadFile, continue to 422 below
            image_file = None

    if image_file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing emoji image file. Please send multipart/form-data with 'emojiImage' (preferred) or 'file' as a file upload."
        )

    # Save image to storage directory (ensure directory exists)
    storage_dir = get_storage_dir()
    os.makedirs(storage_dir, exist_ok=True)
    ext = os.path.splitext(image_file.filename or "")[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
    emoji_id = str(uuid.uuid4())
    file_name = f"{emoji_id}{ext}"
    file_path = os.path.join(storage_dir, file_name)

    with open(file_path, "wb") as out_file:
        while content := await image_file.read(4096):
            out_file.write(content)

    # Insert into DB
    db = SessionLocal()
    try:
        asset = EmojiAsset(
            emoji_id=emoji_id,
            emoji_type=emojiType,
            file_location=file_path
        )
        db.add(asset)
        db.commit()
    except Exception as e:
        db.rollback()
        # Rollback file save if DB insert fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save emoji asset: {str(e)}")

    # Generate the public image URL (actual CDN should proxy or serve assets)
    cdn_base = get_cdn_base_url()
    image_url = f"{cdn_base.rstrip('/')}/{file_name}"

    # Best-effort: update image_url column on emoji_assets if it exists (keeps schema in sync for listing API)
    try:
        db.execute(text("UPDATE emoji_assets SET image_url = :url WHERE emoji_id = :id"), {"url": image_url, "id": emoji_id})
        db.commit()
    except Exception:
        # Ignore if column doesn't exist or update fails
        pass
    finally:
        db.close()

    return UploadEmojiResponse(
        status="SUCCESS",
        message="Emoji uploaded successfully",
        emoji=EmojiAssetResponseModel(
            emoji_id=emoji_id,
            emoji_type=emojiType,
            image_url=image_url
        )
    )

# Instructions for mounting this router
# in src/api/emoji.py or main.py:
#    from .emoji_upload import router as upload_router
#    app.include_router(upload_router)
