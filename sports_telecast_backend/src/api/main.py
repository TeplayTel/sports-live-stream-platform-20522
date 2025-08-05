from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

# Import routers
from api.auth import router as auth_router
from api.matches import router as matches_router
from api.emoji import router as emoji_router
from api.highlights import router as highlights_router
from api.websocket import router as websocket_router

# Import database components
from database import (
    init_database, 
    close_database_connections, 
    check_database_connection,
    get_database_health
)

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
        # Don't raise the exception to allow the app to start even if DB is not available
        # This allows for graceful degradation
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Sports Telecast Backend shutting down...")
    try:
        await close_database_connections()
        logger.info("🔌 Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

# Create FastAPI app with metadata for OpenAPI documentation
app = FastAPI(
    title="Sports Telecast Backend API",
    description="""
    ## Sports Live Streaming Platform Backend
    
    A comprehensive backend API for a sports telecast application that provides:
    
    ### 🏟️ Match & Event Management
    * **Live Match Data**: Real-time scores, events, and statistics
    * **Event Schedules**: Upcoming matches and tournament information  
    * **Match Highlights**: Video highlights and key moments
    
    ### 😊 Fan Engagement
    * **Emoji Reactions**: Interactive emoji reactions during live events
    * **Real-time Updates**: WebSocket connections for live reaction broadcasts
    * **User Preferences**: Personalized content and notifications
    
    ### 🔐 Authentication & Users
    * **JWT Authentication**: Secure token-based authentication
    * **User Profiles**: User management and preferences
    * **Role-based Access**: Different access levels for users and admins
    
    ### 🔄 Real-time Features
    * **WebSocket Support**: Live updates for emoji reactions and match events
    * **Live Streaming**: Integration with video streaming services
    * **Push Notifications**: Real-time alerts and updates
    
    ## Getting Started
    
    1. **Authentication**: Register or login to get a JWT token
    2. **Browse Events**: Get list of live and upcoming matches
    3. **React & Engage**: Use emoji reactions during live events
    4. **Real-time Updates**: Connect via WebSocket for live data
    
    ## WebSocket Connection
    
    Connect to `/ws/{event_id}` for real-time updates:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/EVT123?token=your_jwt_token');
    ```
    
    The WebSocket connection provides:
    - Live emoji reaction updates from all users
    - Real-time match score and event updates  
    - Connection status and statistics
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

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
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

# Health check endpoint
@app.get("/", tags=["Health"], summary="Health Check")
async def health_check():
    """
    Health check endpoint
    
    Returns the API status and basic information.
    Use this endpoint to verify the API is running correctly.
    """
    # Get database health
    db_health = await get_database_health()
    
    return {
        "message": "Sports Telecast Backend API is running! 🏟️⚽",
        "status": "healthy",
        "version": "1.0.0",
        "database": db_health,
        "features": [
            "Live match data and scores",
            "Emoji reactions with real-time updates", 
            "WebSocket support for live connections",
            "JWT-based authentication",
            "Match highlights and video content",
            "Event schedules and tournament info"
        ],
        "endpoints": {
            "authentication": "/auth/*",
            "matches": "/matches/*", 
            "events": "/events/*",
            "emoji_reactions": "/fan-engagement/emoji/v1/*",
            "highlights": "/highlights/*",
            "websocket": "/ws/{event_id}",
            "api_docs": "/docs",
            "openapi_spec": "/openapi.json"
        }
    }

# Database health check endpoint
@app.get("/health/database", tags=["Health"], summary="Database Health Check")
async def database_health_check():
    """
    Database health check endpoint
    
    Returns detailed database connection and health information.
    """
    db_health = await get_database_health()
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "database": db_health
    }

# Include API routers
app.include_router(auth_router)
app.include_router(matches_router)
app.include_router(emoji_router)
app.include_router(highlights_router)
app.include_router(websocket_router)

# API documentation tags
tags_metadata = [
    {
        "name": "Health",
        "description": "Health check and API status endpoints"
    },
    {
        "name": "Authentication", 
        "description": "User authentication, registration, and JWT token management"
    },
    {
        "name": "Matches",
        "description": "Live matches, scores, events, and schedules"
    },
    {
        "name": "Events", 
        "description": "Sports events, tournaments, and competitions"
    },
    {
        "name": "Fan Engagement - Emojis",
        "description": "Interactive emoji reactions for live events with real-time updates"
    },
    {
        "name": "Highlights",
        "description": "Match highlights, video content, and key moments"
    },
    {
        "name": "WebSocket",
        "description": "Real-time WebSocket connections for live updates and emoji reactions"
    }
]

app.openapi_tags = tags_metadata

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
