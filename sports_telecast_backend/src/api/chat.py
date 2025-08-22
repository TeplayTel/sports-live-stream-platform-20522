from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
import uuid

from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user
from ..database.connection import get_db
from ..websocket.manager import manager
import asyncio

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    """Chat message model"""
    message_id: str
    user_id: str
    username: str
    match_id: Optional[str] = None
    event_id: Optional[str] = None
    message: str
    message_type: str = "text"
    created_at: datetime

class ChatMessageRequest(BaseModel):
    """Chat message request model"""
    match_id: Optional[str] = None
    event_id: Optional[str] = None
    message: str
    message_type: str = "text"

class ChatMessageResponse(BaseModel):
    """Chat message response model"""
    status: str = "SUCCESS"
    message_id: str
    message: str = "Message sent successfully"

class ChatMessageListResponse(BaseModel):
    """Chat message list response model"""
    messages: List[ChatMessage]
    total: int
    page: int
    page_size: int

# PUBLIC_INTERFACE
@router.post("/send", response_model=ChatMessageResponse, summary="Send chat message")
def send_chat_message(
    message_request: ChatMessageRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a chat message for a live event or match

    Records a user's chat message and broadcasts it to all connected WebSocket clients.

    Note:
    - Persistence layer is not implemented in this codebase; this endpoint broadcasts
      the message to connected WebSocket clients and returns a generated message_id.
    - Dependency injection now correctly provides an AsyncSession via get_db.
    """
    try:
        # Validate that either match_id or event_id is provided
        if not message_request.match_id and not message_request.event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either match_id or event_id must be provided"
            )

        # Prepare WebSocket broadcast data
        message_id = str(uuid.uuid4())
        chat_data = {
            "type": "chat_message",
            "message_id": message_id,
            "user_id": current_user.user_id,
            "username": current_user.username,
            "match_id": message_request.match_id,
            "event_id": message_request.event_id,
            "message": message_request.message,
            "message_type": message_request.message_type,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Broadcast to WebSocket connections
        event_id = message_request.match_id or message_request.event_id
        asyncio.create_task(manager.broadcast_to_event(event_id, chat_data))

        return ChatMessageResponse(
            message_id=message_id,
            message="Message sent successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

# PUBLIC_INTERFACE
@router.get("/messages/{match_id}", response_model=ChatMessageListResponse, summary="Get chat messages")
def get_chat_messages(
    match_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: Optional[UserResponse] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat messages for a specific match

    Note:
    - Persistence layer is not implemented in this codebase; returns empty list.
    - Dependency injection now correctly provides an AsyncSession via get_db.
    """
    try:
        return ChatMessageListResponse(
            messages=[],
            total=0,
            page=page,
            page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")
