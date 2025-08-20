"""Analytics model for tracking usage statistics and metrics."""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Date, Text, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Analytics(Base):
    """Analytics model for tracking usage statistics and metrics."""
    
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Time dimensions
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-23
    
    # Entity tracking
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # 'conversation', 'message', 'document', 'prompt', 'profile', 'user'
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Event tracking
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # 'created', 'viewed', 'used', 'updated', 'deleted', 'error'
    event_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Performance metrics
    processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # seconds
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_per_second: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Cost tracking
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # USD
    
    # Additional metadata
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    
    # Error tracking
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        """String representation of the analytics record."""
        return (
            f"<Analytics(id={self.id}, entity_type='{self.entity_type}', "
            f"event_type='{self.event_type}', date={self.date})>"
        )