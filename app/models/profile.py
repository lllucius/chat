"""Profile model for LLM parameter management."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Profile(Base):
    """Profile model for managing LLM parameters and settings."""
    
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Profile metadata
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # LLM Configuration
    model_name: Mapped[str] = mapped_column(String(100), default="gpt-4", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048, nullable=False)
    top_p: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    top_k: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    frequency_penalty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    presence_penalty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Context and Memory Settings
    context_window: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50), default="conversation_buffer", nullable=False)
    memory_max_tokens: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    
    # System Prompt and Instructions
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Vector Search Settings
    retrieval_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retrieval_top_k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    retrieval_score_threshold: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    hybrid_search_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Tool and Function Calling
    tools_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    available_tools: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of tool names
    
    # Status and Usage
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Statistics
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_conversations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Additional configuration
    custom_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profiles")

    def __repr__(self) -> str:
        """String representation of the profile."""
        return f"<Profile(id={self.id}, name='{self.name}', user_id={self.user_id})>"