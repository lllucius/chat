"""Chat models and schemas."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from chat.core.database import Base


class MessageRole(str, Enum):
    """Message role enumeration."""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class ConversationStatus(str, Enum):
    """Conversation status enumeration."""
    
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


# Database Models
class Conversation(Base):
    """Conversation database model."""
    
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    status = Column(String(20), default=ConversationStatus.ACTIVE, nullable=False)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Message database model."""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


# Pydantic Schemas
class MessageBase(BaseModel):
    """Base message schema."""
    
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., min_length=1, description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Message metadata")


class MessageCreate(MessageBase):
    """Message creation schema."""
    pass


class MessageResponse(MessageBase):
    """Message response schema."""
    
    id: str
    conversation_id: str
    token_count: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base conversation schema."""
    
    title: Optional[str] = Field(None, max_length=255, description="Conversation title")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Conversation metadata")


class ConversationCreate(ConversationBase):
    """Conversation creation schema."""
    pass


class ConversationUpdate(BaseModel):
    """Conversation update schema."""
    
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[ConversationStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(ConversationBase):
    """Conversation response schema."""
    
    id: str
    user_id: str
    status: ConversationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[MessageResponse] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Chat request schema."""
    
    message: str = Field(..., min_length=1, description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens")
    stream: Optional[bool] = Field(None, description="Enable streaming")


class ChatResponse(BaseModel):
    """Chat response schema."""
    
    message: MessageResponse
    conversation_id: str
    usage: Optional[Dict[str, Any]] = None


class StreamingChatResponse(BaseModel):
    """Streaming chat response schema."""
    
    content: str
    conversation_id: str
    message_id: str
    done: bool = False