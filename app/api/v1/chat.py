"""Chat endpoints for messaging functionality."""

from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json
import asyncio

from app.database import get_db
from app.models.user import User
from app.services.chat_service import ChatService
from app.services.analytics_service import AnalyticsService
from app.schemas.chat import ChatRequest, ChatResponse, StreamingChatResponse
from app.dependencies import get_current_active_user, get_chat_service, get_analytics_service
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat")


@router.post("/message", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Send a message and get AI response."""
    try:
        # Validate request
        if not chat_request.message.strip():
            raise ValidationError("Message cannot be empty")
        
        # Process chat request
        response = await chat_service.send_message(chat_request, current_user)
        
        # Track analytics
        await analytics_service.track_message_sent(
            message_id=response.message_id,
            conversation_id=response.conversation_id,
            user_id=current_user.id,
            token_count=response.token_count,
            processing_time=response.processing_time,
            model_used=response.model_used,
            metadata={
                "request_metadata": chat_request.metadata,
                "sources_count": len(response.sources) if response.sources else 0
            }
        )
        
        logger.info(
            "Message sent",
            user_id=current_user.id,
            conversation_id=response.conversation_id,
            message_id=response.message_id,
            token_count=response.token_count
        )
        
        return response
        
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Message sending failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.post("/stream")
async def stream_message(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Send a message and stream AI response."""
    try:
        # Validate request
        if not chat_request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Set streaming flag
        chat_request.stream = True
        
        async def generate_stream():
            """Generate streaming response."""
            try:
                async for chunk in chat_service.stream_message(chat_request, current_user):
                    # Convert to JSON and add newline for SSE format
                    chunk_data = chunk.model_dump()
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                
                # Send final completion marker
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                # Send error in stream
                error_chunk = StreamingChatResponse(
                    delta="",
                    finished=True,
                    metadata={"error": str(e)}
                )
                yield f"data: {json.dumps(error_chunk.model_dump())}\n\n"
                logger.error("Streaming failed", error=str(e), user_id=current_user.id)
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        logger.error("Stream setup failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup message stream"
        )


@router.get("/models")
async def get_available_models():
    """Get list of available LLM models."""
    # This would typically come from a configuration or model registry
    models = [
        {
            "id": "gpt-4",
            "name": "GPT-4",
            "description": "Most capable GPT-4 model",
            "max_tokens": 8192,
            "cost_per_token": 0.00003
        },
        {
            "id": "gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "description": "Faster GPT-4 variant",
            "max_tokens": 4096,
            "cost_per_token": 0.00001
        },
        {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "description": "Fast and efficient model",
            "max_tokens": 4096,
            "cost_per_token": 0.000002
        }
    ]
    
    return {"models": models}


@router.get("/usage")
async def get_chat_usage(
    current_user: User = Depends(get_current_active_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get user's chat usage statistics."""
    try:
        from datetime import date, timedelta
        
        # Get usage for last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        summary = await analytics_service.get_analytics_summary(
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id
        )
        
        return {
            "period": "30_days",
            "total_conversations": summary.total_conversations,
            "total_messages": summary.total_messages,
            "total_tokens": summary.total_tokens,
            "estimated_cost": summary.total_cost,
            "average_response_time": summary.average_processing_time
        }
        
    except Exception as e:
        logger.error("Usage retrieval failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )