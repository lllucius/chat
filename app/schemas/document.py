"""Document schemas for API request/response models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class DocumentBase(BaseModel):
    """Base document schema with common fields."""
    filename: str = Field(..., description="Document filename")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_public: bool = Field(default=False, description="Public visibility")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""
    content: str = Field(..., description="Document content")
    file_type: str = Field(..., description="File type")
    mime_type: str = Field(..., description="MIME type")


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""
    filename: Optional[str] = Field(None, description="Updated filename")
    tags: Optional[str] = Field(None, description="Updated tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    is_public: Optional[bool] = Field(None, description="Updated visibility")
    is_active: Optional[bool] = Field(None, description="Active status")


class Document(DocumentBase):
    """Schema for document in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    original_filename: str
    file_type: str
    file_size: int
    mime_type: str
    content_hash: str
    processing_status: str
    processing_error: Optional[str] = None
    chunk_count: int
    access_count: int
    last_accessed: Optional[datetime] = None
    version: int
    parent_document_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DocumentUpload(BaseModel):
    """Schema for document upload request."""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="Content type")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    is_public: bool = Field(default=False, description="Public visibility")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DocumentSearch(BaseModel):
    """Schema for document search request."""
    query: str = Field(..., description="Search query")
    file_types: Optional[List[str]] = Field(None, description="Filter by file types")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    is_public: Optional[bool] = Field(None, description="Filter by visibility")
    limit: int = Field(default=10, description="Maximum number of results")
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity score")


class DocumentSearchResult(BaseModel):
    """Schema for document search result."""
    document: Document
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    relevant_chunks: Optional[List[str]] = Field(None, description="Relevant text chunks")


class DocumentChunk(BaseModel):
    """Schema for document chunk."""
    id: int
    document_id: int
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Optional[Dict[str, Any]] = None