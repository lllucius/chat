"""Analytics schemas for API request/response models."""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class AnalyticsBase(BaseModel):
    """Base analytics schema with common fields."""
    entity_type: str = Field(..., description="Entity type being tracked")
    entity_id: Optional[int] = Field(None, description="Entity ID")
    event_type: str = Field(..., description="Event type")
    event_count: int = Field(default=1, description="Number of events")


class AnalyticsCreate(AnalyticsBase):
    """Schema for creating analytics record."""
    user_id: Optional[int] = Field(None, description="User ID")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    token_count: Optional[int] = Field(None, description="Token count")
    tokens_per_second: Optional[float] = Field(None, description="Tokens per second")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost in USD")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error_type: Optional[str] = Field(None, description="Error type if applicable")
    error_message: Optional[str] = Field(None, description="Error message if applicable")


class Analytics(AnalyticsBase):
    """Schema for analytics in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    date: date
    hour: int
    user_id: Optional[int] = None
    processing_time: Optional[float] = None
    token_count: Optional[int] = None
    tokens_per_second: Optional[float] = None
    estimated_cost: Optional[float] = None
    metadata: Optional[str] = None  # JSON string in DB
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class AnalyticsSummary(BaseModel):
    """Schema for analytics summary."""
    date: date
    total_events: int
    unique_users: int
    total_conversations: int
    total_messages: int
    total_tokens: int
    total_cost: float
    average_processing_time: float
    error_count: int
    top_entities: List[Dict[str, Any]]


class AnalyticsQuery(BaseModel):
    """Schema for analytics query parameters."""
    start_date: date = Field(..., description="Start date for analytics")
    end_date: date = Field(..., description="End date for analytics")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    group_by: str = Field(default="date", description="Group results by: date, hour, entity_type, event_type")
    include_errors: bool = Field(default=False, description="Include error events")


class UsageMetrics(BaseModel):
    """Schema for usage metrics."""
    period: str  # 'hour', 'day', 'week', 'month'
    timestamp: datetime
    active_users: int
    total_conversations: int
    total_messages: int
    total_tokens: int
    average_response_time: float
    error_rate: float
    cost: float


class PerformanceMetrics(BaseModel):
    """Schema for performance metrics."""
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    tokens_per_second: float
    requests_per_minute: float
    error_rate: float
    availability: float


class EntityStats(BaseModel):
    """Schema for entity-specific statistics."""
    entity_type: str
    entity_id: int
    total_usage: int
    last_used: Optional[datetime] = None
    average_performance: float
    user_count: int
    metadata: Optional[Dict[str, Any]] = None