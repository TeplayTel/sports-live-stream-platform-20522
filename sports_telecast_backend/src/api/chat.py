from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, List
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..models.user import UserResponse
from ..auth.jwt_auth import get_current_user
from ..database.session import get_db
from ..database.service import DatabaseService
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
    db: Session = Depends(get_db)
):
    """
    Send a chat message for a live event or match

    Records a user's chat message and broadcasts it to all connected WebSocket clients.
    """
    try:
        db_service = DatabaseService(db)
        
        # Validate that either match_id or event_id is provided
        if not message_request.match_id and not message_request.event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either match_id or event_id must be provided"
            )
        
        # If match_id is provided, validate it exists
        if message_request.match_id:
            match = db_service.get_match_by_id(message_request.match_id)
            if not match:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Match not found"
                )
        
        # Add chat message
        message_id = db_service.add_chat_message(
            user_id=current_user.user_id,
            match_id=message_request.match_id,
            message=message_request.message,
            message_type=message_request.message_type
        )
        
        # Prepare WebSocket broadcast data
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
    db: Session = Depends(get_db)
):
    """
    Get chat messages for a specific match

    Returns paginated list of chat messages for the specified match.
    """
    try:
        db_service = DatabaseService(db)
        
        # Validate match exists
        match = db_service.get_match_by_id(match_id)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found"
            )
        
        offset = (page - 1) * page_size
        messages, total = db_service.get_chat_messages(
            match_id=match_id,
            limit=page_size,
            offset=offset
        )
        
        # Convert to Pydantic models
        message_list = []
        for message in messages:
            # Get username from user
            user = db_service.get_user_by_id(message.user_id)
            username = user.username if user else "Unknown User"
            
            message_data = ChatMessage(
                message_id=message.message_id,
                user_id=message.user_id,
                username=username,
                match_id=message.match_id,
                event_id=message.event_id,
                message=message.message,
                message_type=message.message_type,
                created_at=message.created_at
            )
            message_list.append(message_data)
        
        return ChatMessageListResponse(
            messages=message_list,
            total=total,
            page=page,
            page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")
