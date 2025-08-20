"""Chat schemas for API request/response models."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Schema for a single chat message."""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")


class ChatRequest(BaseModel):
    """Schema for chat request."""
    message: str = Field(..., description="User message content")
    conversation_id: Optional[int] = Field(None, description="Existing conversation ID")
    profile_id: Optional[int] = Field(None, description="Profile ID for LLM settings")
    stream: bool = Field(False, description="Enable streaming response")
    context: Optional[List[ChatMessage]] = Field(None, description="Additional context messages")
    use_retrieval: bool = Field(True, description="Enable document retrieval")
    max_tokens: Optional[int] = Field(None, description="Override max tokens for this request")
    temperature: Optional[float] = Field(None, description="Override temperature for this request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional request metadata")


class ChatResponse(BaseModel):
    """Schema for chat response."""
    message: str = Field(..., description="Assistant response")
    conversation_id: int = Field(..., description="Conversation ID")
    message_id: int = Field(..., description="Message ID")
    model_used: str = Field(..., description="LLM model used")
    token_count: int = Field(..., description="Total tokens used")
    processing_time: float = Field(..., description="Processing time in seconds")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Retrieved document sources")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class StreamingChatResponse(BaseModel):
    """Schema for streaming chat response chunk."""
    delta: str = Field(..., description="Text delta for this chunk")
    conversation_id: Optional[int] = Field(None, description="Conversation ID")
    message_id: Optional[int] = Field(None, description="Message ID")
    finished: bool = Field(False, description="Whether the response is complete")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional chunk metadata")


class ChatHistory(BaseModel):
    """Schema for chat history."""
    conversation_id: int
    messages: List[ChatMessage]
    total_messages: int
    total_tokens: int
    created_at: str
    updated_at: str


class ConversationSummary(BaseModel):
    """Schema for conversation summary."""
    id: int
    title: str
    message_count: int
    last_message_at: Optional[str] = None
    created_at: str