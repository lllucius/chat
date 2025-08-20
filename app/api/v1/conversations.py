"""Conversation management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.chat_service import ChatService
from app.schemas.conversation import (
    Conversation, ConversationCreate, ConversationUpdate, 
    ConversationWithMessages, ConversationSummary
)
from app.dependencies import get_current_active_user, get_chat_service
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations")


@router.post("/", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Create a new conversation."""
    try:
        conversation = await chat_service.create_conversation(
            user=current_user,
            title=conversation_data.title,
            context_settings=conversation_data.context_settings
        )
        return conversation
    except Exception as e:
        logger.error("Conversation creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )


@router.get("/", response_model=List[ConversationSummary])
async def get_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get user conversations."""
    try:
        conversations = await chat_service.get_user_conversations(
            user=current_user,
            limit=limit,
            offset=offset,
            include_inactive=include_inactive
        )
        
        # Convert to summary format
        summaries = []
        for conv in conversations:
            summaries.append(ConversationSummary(
                id=conv.id,
                title=conv.title,
                message_count=conv.message_count,
                total_tokens=conv.total_tokens,
                last_message_at=conv.last_message_at,
                created_at=conv.created_at,
                is_active=conv.is_active
            ))
        
        return summaries
    except Exception as e:
        logger.error("Conversation retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get conversation with messages."""
    try:
        conversation = await chat_service.get_conversation(
            conversation_id=conversation_id,
            user=current_user,
            include_messages=True
        )
        return conversation
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )


@router.put("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update conversation."""
    # Implementation would update conversation metadata
    pass


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete conversation (soft delete)."""
    # Implementation would soft delete conversation
    pass