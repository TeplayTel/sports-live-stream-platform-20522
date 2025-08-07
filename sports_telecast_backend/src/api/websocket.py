<<<<<<< HEAD
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
=======
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
>>>>>>> cga-cg908b179b
from typing import Optional
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession

<<<<<<< HEAD
<<<<<<< HEAD
from ..websocket.manager import manager
from ..auth.jwt_auth import JWTAuth
from ..database.connection import get_db
from ..database.repositories import MatchRepository, EventRepository
=======
from websocket.manager import manager
from auth.jwt_auth import JWTAuth
from database import get_db
from database.repositories import MatchRepository, EmojiRepository
>>>>>>> cga-cg908b179b
=======
from ..websocket.manager import manager
from ..auth.jwt_auth import JWTAuth
from ..database import get_db
from ..database.repositories import MatchRepository, EmojiRepository
>>>>>>> cga-cg908b179b

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# PUBLIC_INTERFACE
<<<<<<< HEAD
@router.websocket("/{event_id}")
async def websocket_endpoint(websocket: WebSocket, event_id: str, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time event updates
    
    Handles WebSocket connections for live event updates including:
    - Emoji reactions
    - Match score updates
    - Event notifications
    
    Usage:
        const ws = new WebSocket('ws://localhost:8000/ws/EVT123?token=your_jwt_token');
    """
    # Initialize database session for this connection
    from ..database.connection import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Authenticate user if token provided
        user_id = None
        if token:
            try:
                payload = JWTAuth.decode_access_token(token)
                user_id = payload.get("sub")
            except Exception as e:
                logger.warning(f"WebSocket authentication failed: {e}")
                await websocket.close(code=1008, reason="Invalid token")
                return
        
        # Validate event exists
        match_repo = MatchRepository(db)
        event_repo = EventRepository(db)
        
        event_exists = (
            await match_repo.get_match_by_id(event_id) or 
            await event_repo.get_event_by_id(event_id)
        )
        
        if not event_exists:
            await websocket.close(code=1008, reason="Event not found")
            return
        
        # Accept WebSocket connection
        await websocket.accept()
        
        # Add connection to manager
        await manager.connect(websocket, event_id, user_id)
        
        try:
            # Send initial connection confirmation
            await websocket.send_text(json.dumps({
                "type": "connection_established",
                "event_id": event_id,
                "user_id": user_id,
                "message": "Connected to live updates"
            }))
            
            # Keep connection alive and handle incoming messages
            while True:
                try:
                    # Wait for messages from client
                    data = await websocket.receive_text()
                    
                    try:
                        message = json.loads(data)
                        message_type = message.get("type")
                        
                        # Handle different message types
                        if message_type == "ping":
                            # Respond to ping with pong
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "timestamp": message.get("timestamp")
                            }))
                        
                        elif message_type == "subscribe_to_reactions":
                            # Client wants to receive emoji reaction updates
                            await websocket.send_text(json.dumps({
                                "type": "subscribed",
                                "subscription": "emoji_reactions",
                                "event_id": event_id
                            }))
                        
                        else:
                            logger.warning(f"Unknown message type: {message_type}")
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON received from WebSocket: {data}")
                
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error in WebSocket message handling: {e}")
                    break
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for event {event_id}, user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Remove connection from manager
            await manager.disconnect(websocket, event_id)
=======
@router.websocket("/ws/{event_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    event_id: str,
    token: Optional[str] = Query(None, description="JWT token for authentication"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time event updates

    Establishes a WebSocket connection for receiving real-time updates about:
    - Emoji reactions from other users
    - Match score updates
    - Live match events
    - General event notifications

    Authentication via JWT token is optional but recommended for personalized updates.
    """
    user_id = None

    # Optional authentication
    if token:
        try:
            payload = JWTAuth.verify_token(token)
            user_id = payload.get("sub")
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            # Continue without authentication

    # Validate event exists (try match or event id)
    match_repo = MatchRepository(db)
    emoji_repo = EmojiRepository(db)
    event = await match_repo.get_match_by_id(event_id)
    if not event:
        await websocket.close(code=4004, reason="Event not found")
        return

    try:
        # Accept connection and add to manager
        await manager.connect(websocket, event_id, user_id)

        # Send initial data
        reaction_summary = await emoji_repo.get_reaction_summary(event_id)
        await manager.send_personal_message(
            {
                "type": "initial_data",
                "event_id": event_id,
                "data": {
                    "match": {
                        "match_id": event.match_id,
                        "status": event.status.value if hasattr(event.status, 'value') else str(event.status),
                        "home_score": event.home_score,
                        "away_score": event.away_score,
                        # Add other fields as needed for the frontend
                    },
                    "reaction_summary": reaction_summary,
                },
            },
            websocket,
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    await manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": message.get("timestamp"),
                        },
                        websocket,
                    )

                elif message.get("type") == "get_reaction_summary":
                    summary = await emoji_repo.get_reaction_summary(event_id)
                    await manager.send_personal_message(
                        {
                            "type": "reaction_summary",
                            "event_id": event_id,
                            "data": summary,
                        },
                        websocket,
                    )

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                    },
                    websocket,
                )
            except Exception as e:
                logger.error(f"WebSocket message handling error: {e}")
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Message processing error",
                    },
                    websocket,
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        manager.disconnect(websocket)
>>>>>>> cga-cg908b179b


# PUBLIC_INTERFACE
@router.get("/stats", summary="Get WebSocket connection statistics")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics

    Returns information about active WebSocket connections and events.
    Useful for monitoring and debugging.
    """
    stats = await manager.get_connection_stats()
    return {
<<<<<<< HEAD
        "status": "active",
        "total_connections": stats.get("total_connections", 0),
        "events_with_connections": stats.get("events_with_connections", 0),
        "connection_details": stats.get("connection_details", {}),
        "uptime": stats.get("uptime", 0)
=======
        "total_connections": manager.get_total_connections(),
        "active_events": manager.get_active_events(),
        "connection_counts": {
            event_id: manager.get_connection_count(event_id)
            for event_id in manager.get_active_events()
        },
>>>>>>> cga-cg908b179b
    }

