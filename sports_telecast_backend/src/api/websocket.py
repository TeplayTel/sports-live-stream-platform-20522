from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import logging

from ..websocket.manager import manager
from ..auth.jwt_auth import JWTAuth
from ..database.connection import db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

# PUBLIC_INTERFACE
@router.websocket("/ws/{event_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    event_id: str,
    token: Optional[str] = Query(None, description="JWT token for authentication")
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
    
    # Validate event exists
    event = db.get_match_by_id(event_id)
    if not event:
        await websocket.close(code=4004, reason="Event not found")
        return
    
    try:
        # Accept connection and add to manager
        await manager.connect(websocket, event_id, user_id)
        
        # Send initial data
        reaction_summary = db.get_reaction_summary(event_id)
        await manager.send_personal_message({
            "type": "initial_data",
            "event_id": event_id,
            "data": {
                "match": event.dict(),
                "reaction_summary": reaction_summary.dict()
            }
        }, websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }, websocket)
                
                elif message.get("type") == "get_reaction_summary":
                    summary = db.get_reaction_summary(event_id)
                    await manager.send_personal_message({
                        "type": "reaction_summary",
                        "event_id": event_id,
                        "data": summary.dict()
                    }, websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
            except Exception as e:
                logger.error(f"WebSocket message handling error: {e}")
                await manager.send_personal_message({
                    "type": "error", 
                    "message": "Message processing error"
                }, websocket)
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        manager.disconnect(websocket)

# PUBLIC_INTERFACE
@router.get("/ws/stats", summary="Get WebSocket connection statistics")
def get_websocket_stats():
    """
    Get WebSocket connection statistics
    
    Returns information about active WebSocket connections and events.
    Useful for monitoring and debugging.
    """
    return {
        "total_connections": manager.get_total_connections(),
        "active_events": manager.get_active_events(),
        "connection_counts": {
            event_id: manager.get_connection_count(event_id)
            for event_id in manager.get_active_events()
        }
    }
