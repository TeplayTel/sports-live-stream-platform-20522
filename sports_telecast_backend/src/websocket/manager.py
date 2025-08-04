from typing import Dict, List, Set, Any
from fastapi import WebSocket
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket connection manager for real-time updates"""
    
    def __init__(self):
        # Store active connections by event_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store user connections for authentication
        self.user_connections: Dict[str, WebSocket] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, event_id: str, user_id: str = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Add to event-specific connections
        if event_id not in self.active_connections:
            self.active_connections[event_id] = set()
        self.active_connections[event_id].add(websocket)
        
        # Store user connection if authenticated
        if user_id:
            self.user_connections[user_id] = websocket
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "event_id": event_id,
            "user_id": user_id,
            "connected_at": datetime.utcnow()
        }
        
        logger.info(f"WebSocket connected for event {event_id}, user: {user_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "event_id": event_id,
            "message": "Connected to live updates",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        metadata = self.connection_metadata.get(websocket, {})
        event_id = metadata.get("event_id")
        user_id = metadata.get("user_id")
        
        # Remove from event connections
        if event_id and event_id in self.active_connections:
            self.active_connections[event_id].discard(websocket)
            if not self.active_connections[event_id]:
                del self.active_connections[event_id]
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
        
        # Remove metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        
        logger.info(f"WebSocket disconnected for event {event_id}, user: {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_event(self, message: Dict[str, Any], event_id: str):
        """Broadcast a message to all connections for a specific event"""
        if event_id not in self.active_connections:
            return
        
        # Create a copy of connections to avoid modification during iteration
        connections = self.active_connections[event_id].copy()
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                self.disconnect(connection)
    
    async def broadcast_emoji_reaction(self, event_id: str, emoji_data: Dict[str, Any]):
        """Broadcast emoji reaction update to all event connections"""
        message = {
            "type": "emoji_reaction_update",
            "event_id": event_id,
            "data": emoji_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_event(message, event_id)
        logger.info(f"Broadcasted emoji reaction for event {event_id}")
    
    async def broadcast_match_update(self, event_id: str, match_data: Dict[str, Any]):
        """Broadcast match data update to all event connections"""
        message = {
            "type": "match_update", 
            "event_id": event_id,
            "data": match_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_event(message, event_id)
        logger.info(f"Broadcasted match update for event {event_id}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send a message to a specific user"""
        if user_id in self.user_connections:
            await self.send_personal_message(message, self.user_connections[user_id])
    
    def get_connection_count(self, event_id: str) -> int:
        """Get number of active connections for an event"""
        return len(self.active_connections.get(event_id, set()))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_active_events(self) -> List[str]:
        """Get list of events with active connections"""
        return list(self.active_connections.keys())

# Global connection manager instance
manager = ConnectionManager()
