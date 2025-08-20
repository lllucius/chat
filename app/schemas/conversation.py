"""Conversation schemas for API request/response models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.message import Message


class ConversationBase(BaseModel):
    """Base conversation schema with common fields."""
    title: str = Field(..., description="Conversation title")
    summary: Optional[str] = Field(None, description="Conversation summary")
    context_settings: Optional[Dict[str, Any]] = Field(None, description="LLM context settings")


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    pass


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    title: Optional[str] = Field(None, description="Updated title")
    summary: Optional[str] = Field(None, description="Updated summary")
    context_settings: Optional[Dict[str, Any]] = Field(None, description="Updated context settings")
    is_active: Optional[bool] = Field(None, description="Active status")


class Conversation(ConversationBase):
    """Schema for conversation in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    is_active: bool
    message_count: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None


class ConversationWithMessages(Conversation):
    """Schema for conversation with messages included."""
    messages: List[Message] = Field(default_factory=list, description="Conversation messages")


class ConversationSummary(BaseModel):
    """Schema for conversation summary in lists."""
    id: int
    title: str
    message_count: int
    total_tokens: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    is_active: bool