# Ensure environment variables from a .env file are available before any other imports.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # In production, .env auto-loading is optional
    pass

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Routers
from .auth import router as auth_router
from .profiles import router as profiles_router
from .emoji import router as emoji_router
from api.emoji_upload import router as emoji_upload_router
from .highlights import router as highlights_router
from .websocket import router as websocket_router

# Database utilities
from ..database import (
    init_database,
    close_database_connections,
    check_database_connection,
    get_database_health,
)

# Middleware
from ..middleware.api_logger import APILoggingMiddleware, set_api_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events for startup and shutdown."""
    logger.info("🚀 Sports Telecast Backend starting up...")

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

    # Yield control to the application
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

    Cricket-only backend for event streaming, emoji reactions, highlights, and user authentication/profile.

    Features
    * Live Stream & Match Data: Real-time cricket match data and streaming event info
    * Emoji Reactions: Interactive emoji reactions during live cricket matches
    * JWT Auth & Profiles: User authentication and profile management
    * Match Highlights: Video highlights and cricket key moments
    * WebSocket: Real-time updates for cricket matches & engagement
    """,
    version="1.0.0",
    contact={"name": "Sports Telecast API Support", "email": "support@sportstelecast.com"},
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    lifespan=lifespan,
)

# Setup API logging middleware
api_logger_middleware = APILoggingMiddleware(app)
set_api_logger(api_logger_middleware)
app.add_middleware(APILoggingMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": "An unexpected error occurred"},
    )

@app.get("/", tags=["Health"], summary="Health Check")
async def health_check():
    """
    Health check endpoint.

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
            "teams": "/teams/*",
            "categories": "/categories/*",
            "chat": "/chat/*",
            "websocket": "/ws/{event_id}",
            "api_docs": "/docs",
            "redoc_docs": "/redoc",
            "openapi_spec": "/openapi.json",
        },
        "documentation": {"swagger_ui": "/docs", "redoc": "/redoc", "openapi_json": "/openapi.json"},
    }

@app.get("/health/database", tags=["Health"], summary="Database Health Check")
async def database_health_check():
    """
    Database health check endpoint.

    Returns detailed database connection and health information.
    """
    db_health = await get_database_health()
    return {"database": db_health}

# Include routers
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(emoji_router)
app.include_router(emoji_upload_router)
app.include_router(highlights_router)
app.include_router(websocket_router)

# OpenAPI tags
tags_metadata = [
    {"name": "Health", "description": "Health check and API status endpoints"},
    {"name": "Authentication", "description": "User authentication and JWT token management"},
    {"name": "User Profiles", "description": "User profiles with preferences and privacy settings"},
    {"name": "Fan Engagement - Emojis", "description": "Interactive emoji reactions for live cricket events"},
    {"name": "Highlights", "description": "Match highlights, cricket video content, and key moments"},
    {"name": "WebSocket", "description": "Real-time WebSocket connections for cricket live updates and emoji reactions"},
]
app.openapi_tags = tags_metadata

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
