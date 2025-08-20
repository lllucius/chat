"""Profile schemas for API request/response models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class ProfileBase(BaseModel):
    """Base profile schema with common fields."""
    name: str = Field(..., description="Profile name")
    description: Optional[str] = Field(None, description="Profile description")
    model_name: str = Field(default="gpt-4", description="LLM model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int = Field(default=2048, gt=0, description="Maximum tokens")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p sampling")
    top_k: Optional[int] = Field(None, gt=0, description="Top-k sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")


class ProfileCreate(ProfileBase):
    """Schema for creating a new profile."""
    system_prompt: Optional[str] = Field(None, description="System prompt")
    instructions: Optional[str] = Field(None, description="Additional instructions")
    retrieval_enabled: bool = Field(default=True, description="Enable retrieval")
    retrieval_top_k: int = Field(default=5, gt=0, description="Retrieval top-k")
    retrieval_score_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Retrieval threshold")
    hybrid_search_enabled: bool = Field(default=True, description="Enable hybrid search")
    tools_enabled: bool = Field(default=True, description="Enable tools")
    available_tools: Optional[List[str]] = Field(None, description="Available tool names")
    custom_settings: Optional[Dict[str, Any]] = Field(None, description="Custom settings")


class ProfileUpdate(BaseModel):
    """Schema for updating a profile."""
    name: Optional[str] = Field(None, description="Updated name")
    description: Optional[str] = Field(None, description="Updated description")
    model_name: Optional[str] = Field(None, description="Updated model name")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Updated temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Updated max tokens")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated top-p")
    top_k: Optional[int] = Field(None, gt=0, description="Updated top-k")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Updated frequency penalty")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Updated presence penalty")
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")
    instructions: Optional[str] = Field(None, description="Updated instructions")
    retrieval_enabled: Optional[bool] = Field(None, description="Updated retrieval setting")
    retrieval_top_k: Optional[int] = Field(None, gt=0, description="Updated retrieval top-k")
    retrieval_score_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated threshold")
    hybrid_search_enabled: Optional[bool] = Field(None, description="Updated hybrid search setting")
    tools_enabled: Optional[bool] = Field(None, description="Updated tools setting")
    available_tools: Optional[List[str]] = Field(None, description="Updated available tools")
    custom_settings: Optional[Dict[str, Any]] = Field(None, description="Updated custom settings")
    is_active: Optional[bool] = Field(None, description="Updated active status")
    is_default: Optional[bool] = Field(None, description="Updated default status")


class Profile(ProfileBase):
    """Schema for profile in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    context_window: int
    memory_type: str
    memory_max_tokens: int
    system_prompt: Optional[str] = None
    instructions: Optional[str] = None
    retrieval_enabled: bool
    retrieval_top_k: int
    retrieval_score_threshold: float
    hybrid_search_enabled: bool
    tools_enabled: bool
    available_tools: Optional[str] = None  # JSON string in DB
    is_active: bool
    is_default: bool
    usage_count: int
    last_used: Optional[datetime] = None
    total_conversations: int
    total_tokens_used: int
    custom_settings: Optional[str] = None  # JSON string in DB
    created_at: datetime
    updated_at: datetime


class ProfileUsageStats(BaseModel):
    """Schema for profile usage statistics."""
    profile_id: int
    usage_count: int
    total_conversations: int
    total_tokens_used: int
    last_used: Optional[datetime] = None
    average_tokens_per_conversation: float