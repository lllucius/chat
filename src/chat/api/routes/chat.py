"""Chat routes for conversation management."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import json
import asyncio

from chat.core import get_db_session, get_logger
from chat.models import (
    User,
    Conversation,
    Message,
    MessageRole,
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ChatRequest,
    ChatResponse,
    MessageResponse,
    StreamingChatResponse,
)
from chat.services import llm_service, vector_store_service
from chat.api.dependencies import get_current_user
from chat.config import settings

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """Send a chat message and get response.
    
    Args:
        request: Chat request
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Chat response
    """
    logger.info("Processing chat request", user_id=str(current_user.id))
    
    # Get or create conversation
    if request.conversation_id:
        # Get existing conversation
        result = await db_session.execute(
            select(Conversation).where(
                (Conversation.id == request.conversation_id) &
                (Conversation.user_id == current_user.id)
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create new conversation
        conversation = Conversation(
            user_id=current_user.id,
            title="New Conversation",
        )
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
    
    # Get conversation history
    history_result = await db_session.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .limit(settings.conversation_memory_size)
    )
    history_messages = [MessageResponse.from_orm(msg) for msg in history_result.scalars().all()]
    
    # Get relevant context from documents
    context = await vector_store_service.get_relevant_context(
        query=request.message,
        user_id=str(current_user.id),
    )
    
    # Prepare system prompt with context
    system_prompt = request.system_prompt or settings.default_system_prompt
    if context:
        system_prompt += f"\n\nRelevant context:\n{context}"
    
    # Add user message to conversation
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=request.message,
    )
    db_session.add(user_message)
    
    try:
        # Generate response
        response_text = await llm_service.generate_response(
            user_message=request.message,
            conversation_history=history_messages,
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        # Add assistant message to conversation
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
        )
        db_session.add(assistant_message)
        
        # Update conversation title if this is the first exchange
        if not conversation.title or conversation.title == "New Conversation":
            try:
                title = await llm_service.generate_title([
                    MessageResponse.from_orm(user_message),
                    MessageResponse.from_orm(assistant_message),
                ])
                conversation.title = title
            except Exception as e:
                logger.warning("Failed to generate title", error=str(e))
        
        await db_session.commit()
        await db_session.refresh(assistant_message)
        
        logger.info("Chat response generated", conversation_id=str(conversation.id))
        
        return ChatResponse(
            message=MessageResponse.from_orm(assistant_message),
            conversation_id=str(conversation.id),
        )
        
    except Exception as e:
        await db_session.rollback()
        logger.error("Failed to generate chat response", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response"
        )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Send a chat message and get streaming response.
    
    Args:
        request: Chat request
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Streaming response
    """
    logger.info("Processing streaming chat request", user_id=str(current_user.id))
    
    async def generate_stream():
        try:
            # Similar setup to regular chat
            if request.conversation_id:
                result = await db_session.execute(
                    select(Conversation).where(
                        (Conversation.id == request.conversation_id) &
                        (Conversation.user_id == current_user.id)
                    )
                )
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    yield f"data: {json.dumps({'error': 'Conversation not found'})}\n\n"
                    return
            else:
                conversation = Conversation(
                    user_id=current_user.id,
                    title="New Conversation",
                )
                db_session.add(conversation)
                await db_session.commit()
                await db_session.refresh(conversation)
            
            # Get conversation history
            history_result = await db_session.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
                .limit(settings.conversation_memory_size)
            )
            history_messages = [MessageResponse.from_orm(msg) for msg in history_result.scalars().all()]
            
            # Get relevant context
            context = await vector_store_service.get_relevant_context(
                query=request.message,
                user_id=str(current_user.id),
            )
            
            # Prepare system prompt
            system_prompt = request.system_prompt or settings.default_system_prompt
            if context:
                system_prompt += f"\n\nRelevant context:\n{context}"
            
            # Add user message
            user_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=request.message,
            )
            db_session.add(user_message)
            
            # Create assistant message placeholder
            assistant_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content="",
            )
            db_session.add(assistant_message)
            await db_session.commit()
            await db_session.refresh(assistant_message)
            
            # Stream response
            full_response = ""
            async for token in llm_service.stream_response(
                user_message=request.message,
                conversation_history=history_messages,
                system_prompt=system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                full_response += token
                
                chunk = StreamingChatResponse(
                    content=token,
                    conversation_id=str(conversation.id),
                    message_id=str(assistant_message.id),
                    done=False,
                )
                
                yield f"data: {chunk.model_dump_json()}\n\n"
            
            # Update assistant message with full response
            assistant_message.content = full_response
            await db_session.commit()
            
            # Send final chunk
            final_chunk = StreamingChatResponse(
                content="",
                conversation_id=str(conversation.id),
                message_id=str(assistant_message.id),
                done=True,
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            
        except Exception as e:
            logger.error("Streaming chat error", error=str(e))
            error_chunk = {"error": str(e)}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0,
) -> List[ConversationResponse]:
    """List user's conversations.
    
    Args:
        current_user: Current authenticated user
        db_session: Database session
        limit: Maximum number of conversations
        offset: Offset for pagination
        
    Returns:
        List of conversations
    """
    result = await db_session.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
        .offset(offset)
    )
    
    conversations = result.scalars().all()
    return [ConversationResponse.from_orm(conv) for conv in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Get a specific conversation with messages.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Conversation with messages
    """
    # Get conversation
    conv_result = await db_session.execute(
        select(Conversation).where(
            (Conversation.id == conversation_id) &
            (Conversation.user_id == current_user.id)
        )
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get messages
    msg_result = await db_session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = [MessageResponse.from_orm(msg) for msg in msg_result.scalars().all()]
    
    response = ConversationResponse.from_orm(conversation)
    response.messages = messages
    
    return response


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Update a conversation.
    
    Args:
        conversation_id: Conversation ID
        update_data: Update data
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Updated conversation
    """
    result = await db_session.execute(
        select(Conversation).where(
            (Conversation.id == conversation_id) &
            (Conversation.user_id == current_user.id)
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(conversation, field, value)
    
    await db_session.commit()
    await db_session.refresh(conversation)
    
    return ConversationResponse.from_orm(conversation)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a conversation.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Success message
    """
    result = await db_session.execute(
        select(Conversation).where(
            (Conversation.id == conversation_id) &
            (Conversation.user_id == current_user.id)
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    await db_session.delete(conversation)
    await db_session.commit()
    
    return {"message": "Conversation deleted successfully"}