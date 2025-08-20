"""Prompt model for managing reusable prompts and templates."""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Prompt(Base):
    """Prompt model for managing reusable prompts and templates."""
    
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Prompt metadata
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False, index=True)
    
    # Prompt content
    template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of variable names
    example_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON object with example values
    
    # Prompt configuration
    input_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON schema for validation
    output_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'text', 'json', 'markdown'
    
    # Usage and performance
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    average_rating: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Status and visibility
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # System prompts
    
    # Version control
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Tags and metadata
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Comma-separated tags
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    
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

    def __repr__(self) -> str:
        """String representation of the prompt."""
        return f"<Prompt(id={self.id}, name='{self.name}', category='{self.category}')>"