# Ensure environment variables from a .env file are available before any other imports.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # In production, .env auto-loading is optional
    pass

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from contextlib import asynccontextmanager

# Import routers
from .auth import router as auth_router
from .profiles import router as profiles_router
from .emoji import router as emoji_router
from api.emoji_upload import router as emoji_upload_router
from .highlights import router as highlights_router
from .websocket import router as websocket_router

# Import database components
from ..database import (
    init_database, 
    close_database_connections, 
    check_database_connection,
    get_database_health
)

# Import middleware
from ..middleware.api_logger import APILoggingMiddleware, set_api_logger

# (get_trusted_user import removed — now only used via dependent modules)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 Sports Telecast Backend starting up...")

    # Initialize database
    try:
        logger.info("🔗 Initializing database connection...")
        await init_database()

        # Check database connection
        if await check_database_connection():
            logger.info("✅ Database connection established successfully")
        else:
            logger.warning("⚠️ Database connection check failed")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # Graceful degradation

    yield

    # Cleanup on shutdown
    logger.info("🛑 Sports Telecast Backend shutting down...")
    try:
        await close_database_connections()
        logger.info("🔌 Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

# Create FastAPI app with cricket streaming-only metadata
app = FastAPI(
    title="Sports Telecast Backend API",
    description="""
    ## Sports Live Streaming Platform Backend

    **Cricket-only backend** for event streaming, emoji reactions, highlights, and user authentication/profile.

    ### 🎯 Features
    * **Live Stream & Match Data**: Real-time cricket match data and streaming event info
    * **Emoji Reactions**: Interactive emoji reactions during live cricket matches
    * **JWT Auth & Profiles**: User authentication and profile management
    * **Match Highlights**: Video highlights and cricket key moments
    * **WebSocket**: Real-time updates for cricket matches & engagement
    """,
    version="1.0.0",
    contact={
        "name": "Sports Telecast API Support",
        "email": "support@sportstelecast.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

api_logger_middleware = APILoggingMiddleware(app)
set_api_logger(api_logger_middleware)
app.add_middleware(APILoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, tighten this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )

# PUBLIC_INTERFACE
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Specialized validation handler to provide clearer guidance when file uploads are
    incorrectly sent as strings for the emoji upload endpoint.

    If the 'emojiImage' field is present as a string instead of a file in a multipart/form-data
    request, FastAPI would normally raise a 422 with a generic message. This handler detects
    that case and returns a more actionable error and examples.
    """
    try:
        errors = exc.errors()
        for err in errors:
            loc = err.get("loc", [])
            msg = err.get("msg", "")
            # Detect the common case: 'emojiImage' sent as text instead of file
            if any(str(x).lower() == "emojiimage" for x in loc) and "UploadFile" in msg:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "detail": "Invalid 'emojiImage' form field. Send a file via multipart/form-data with key 'emojiImage' (e.g., a PNG). Do not send a string.",
                        "resolution": "Use a FormData/file upload. If using axios or fetch, append the File object. In curl, use -F 'emojiImage=@/path/to/file.png'.",
                        "examples": {
                            "curl": "curl -X POST -H 'Authorization: Bearer <token>' -F 'emojiType=clap' -F 'emojiImage=@/path/to/emoji.png' http://localhost:3001/fan-engagement/emoji/v1/upload",
                            "axios": "const fd = new FormData(); fd.append('emojiType','clap'); fd.append('emojiImage', file); axios.post('/fan-engagement/emoji/v1/upload', fd, { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'multipart/form-data' } });",
                            "fetch": "const fd = new FormData(); fd.append('emojiType','clap'); fd.append('emojiImage', fileInput.files[0]); fetch('/fan-engagement/emoji/v1/upload', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd });"
                        },
                        "note": "As a compatibility fallback, a field named 'file' is also accepted when sent as a file. Prefer 'emojiImage'."
                    },
                )
    except Exception:
        # Fall through to default behavior if inspection fails
        pass

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors if (errors := exc.errors()) else "Validation error"},
    )

@app.get("/", tags=["Health"], summary="Health Check")
async def health_check():
    """
    Health check endpoint

    Returns the API status and basic information.
    Use this endpoint to verify the API is running correctly.
    """
    db_health = await get_database_health()

    return {
        "message": "Sports Telecast Backend API is running! 🏟️🏏",
        "status": "healthy",
        "version": "1.0.0",
        "database": db_health,
        "features": [
            "Live CRICKET match data and scores",
            "Emoji reactions with real-time updates", 
            "WebSocket support for live connections",
            "JWT-based authentication",
            "Match highlights and cricket video content",
        ],
        "endpoints": {
            "authentication": "/auth/*",
            "profiles": "/profiles/*",
            "emoji_reactions": "/fan-engagement/emoji/v1/*",
            "highlights": "/highlights/*",
            "websocket": "/ws/{event_id}",
            "api_docs": "/docs",
            "redoc_docs": "/redoc", 
            "openapi_spec": "/openapi.json"
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        }
    }

@app.get("/health/database", tags=["Health"], summary="Database Health Check")
async def database_health_check():
    """
    Database health check endpoint

    Returns detailed database connection and health information.
    """
    db_health = await get_database_health()
    return {
        "database": db_health
    }

app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(emoji_router)
app.include_router(emoji_upload_router)
app.include_router(highlights_router)
app.include_router(websocket_router)

tags_metadata = [
    {
        "name": "Health",
        "description": "Health check and API status endpoints"
    },
    {
        "name": "Authentication", 
        "description": "User authentication and JWT token management"
    },
    {
        "name": "User Profiles",
        "description": "User profiles with preferences and privacy settings"
    },
    {
        "name": "Fan Engagement - Emojis",
        "description": "Interactive emoji reactions for live cricket events"
    },
    {
        "name": "Highlights",
        "description": "Match highlights, cricket video content, and key moments"
    },
    {
        "name": "WebSocket",
        "description": "Real-time WebSocket connections for cricket live updates and emoji reactions"
    }
]
app.openapi_tags = tags_metadata

if __name__ == "__main__":
    """
    Entrypoint for running the app directly.

    Binds to host/port derived from environment variables:
    - HOST: defaults to '0.0.0.0' to allow external access (preview/proxy)
    - PORT: defaults to 3001 to match the preview system's expectations
    """
    import uvicorn
    import os

    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", "3001"))
    except ValueError:
        port = 3001

    # Using string import path keeps reload/import resolution consistent when used externally
    uvicorn.run("src.api.main:app", host=host, port=port, log_level="info")
