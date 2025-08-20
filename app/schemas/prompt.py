"""Prompt schemas for API request/response models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class PromptBase(BaseModel):
    """Base prompt schema with common fields."""
    name: str = Field(..., description="Prompt name")
    description: Optional[str] = Field(None, description="Prompt description")
    category: str = Field(default="general", description="Prompt category")
    template: str = Field(..., description="Prompt template")
    variables: Optional[List[str]] = Field(None, description="Template variable names")
    example_values: Optional[Dict[str, Any]] = Field(None, description="Example variable values")


class PromptCreate(PromptBase):
    """Schema for creating a new prompt."""
    input_schema: Optional[Dict[str, Any]] = Field(None, description="Input validation schema")
    output_format: Optional[str] = Field(None, description="Expected output format")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_public: bool = Field(default=True, description="Public visibility")


class PromptUpdate(BaseModel):
    """Schema for updating a prompt."""
    name: Optional[str] = Field(None, description="Updated name")
    description: Optional[str] = Field(None, description="Updated description")
    category: Optional[str] = Field(None, description="Updated category")
    template: Optional[str] = Field(None, description="Updated template")
    variables: Optional[List[str]] = Field(None, description="Updated variables")
    example_values: Optional[Dict[str, Any]] = Field(None, description="Updated example values")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="Updated input schema")
    output_format: Optional[str] = Field(None, description="Updated output format")
    tags: Optional[str] = Field(None, description="Updated tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    is_active: Optional[bool] = Field(None, description="Updated active status")
    is_public: Optional[bool] = Field(None, description="Updated visibility")
    version: Optional[str] = Field(None, description="Updated version")
    changelog: Optional[str] = Field(None, description="Version changelog")


class Prompt(PromptBase):
    """Schema for prompt in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    input_schema: Optional[str] = None  # JSON string in DB
    output_format: Optional[str] = None
    usage_count: int
    last_used: Optional[datetime] = None
    average_rating: Optional[float] = None
    is_active: bool
    is_public: bool
    is_system: bool
    version: str
    changelog: Optional[str] = None
    tags: Optional[str] = None
    metadata: Optional[str] = None  # JSON string in DB
    created_at: datetime
    updated_at: datetime


class PromptExecution(BaseModel):
    """Schema for prompt execution request."""
    prompt_id: int = Field(..., description="Prompt ID")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variable values")
    profile_id: Optional[int] = Field(None, description="Profile ID for execution")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Execution metadata")


class PromptExecutionResult(BaseModel):
    """Schema for prompt execution result."""
    prompt_id: int
    rendered_prompt: str
    response: str
    token_count: int
    processing_time: float
    model_used: str
    metadata: Optional[Dict[str, Any]] = None


class PromptSearch(BaseModel):
    """Schema for prompt search request."""
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    is_public: Optional[bool] = Field(None, description="Filter by visibility")
    limit: int = Field(default=10, description="Maximum number of results")


class PromptSearchResult(BaseModel):
    """Schema for prompt search result."""
    prompt: Prompt
    relevance_score: float = Field(..., description="Search relevance score")
    matched_fields: List[str] = Field(..., description="Fields that matched the search")