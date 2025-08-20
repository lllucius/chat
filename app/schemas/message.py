"""Message schemas for API request/response models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class MessageBase(BaseModel):
    """Base message schema with common fields."""
    content: str = Field(..., description="Message content")
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    message_type: str = Field(default="text", description="Message type: 'text', 'image', 'file'")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    conversation_id: int = Field(..., description="Conversation ID")


class MessageUpdate(BaseModel):
    """Schema for updating a message."""
    content: Optional[str] = Field(None, description="Updated message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    is_edited: bool = Field(True, description="Mark as edited")


class Message(MessageBase):
    """Schema for message in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    conversation_id: int
    is_edited: bool
    is_deleted: bool
    token_count: int
    processing_time: Optional[float] = None
    model_used: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MessageWithEmbedding(Message):
    """Schema for message with embedding vector."""
    embedding: Optional[List[float]] = Field(None, description="Message embedding vector")


class MessageSearch(BaseModel):
    """Schema for message search request."""
    query: str = Field(..., description="Search query")
    conversation_id: Optional[int] = Field(None, description="Limit search to specific conversation")
    limit: int = Field(default=10, description="Maximum number of results")
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity score")


class MessageSearchResult(BaseModel):
    """Schema for message search result."""
    message: Message
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    highlights: Optional[List[str]] = Field(None, description="Highlighted text snippets")