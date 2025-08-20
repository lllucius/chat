"""Document models and schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Integer, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from chat.core.database import Base


class DocumentStatus(str, Enum):
    """Document processing status enumeration."""
    
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Document type enumeration."""
    
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    DOCX = "docx"
    HTML = "html"


# Database Models
class Document(Base):
    """Document database model."""
    
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(20), nullable=False)
    content_type = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    status = Column(String(20), default=DocumentStatus.UPLOADED, nullable=False)
    metadata = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    indexed_at = Column(DateTime, nullable=True)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Document chunk database model."""
    
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    metadata = Column(JSON, default=dict)
    embedding = Column(LargeBinary, nullable=True)  # Store embedding as binary
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")


# Pydantic Schemas
class DocumentBase(BaseModel):
    """Base document schema."""
    
    filename: str = Field(..., description="Document filename")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Document metadata")


class DocumentUpload(BaseModel):
    """Document upload schema."""
    
    filename: str = Field(..., description="Original filename")


class DocumentResponse(DocumentBase):
    """Document response schema."""
    
    id: str
    user_id: str
    original_filename: str
    file_size: int
    file_type: DocumentType
    content_type: str
    status: DocumentStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
    chunk_count: int = 0
    
    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    """Document update schema."""
    
    filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[DocumentStatus] = None


class DocumentChunkResponse(BaseModel):
    """Document chunk response schema."""
    
    id: str
    document_id: str
    content: str
    chunk_index: int
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentSearchRequest(BaseModel):
    """Document search request schema."""
    
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Number of results")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    document_ids: Optional[List[str]] = Field(None, description="Filter by document IDs")


class DocumentSearchResult(BaseModel):
    """Document search result schema."""
    
    chunk: DocumentChunkResponse
    document: DocumentResponse
    similarity_score: float
    rank: int


class DocumentSearchResponse(BaseModel):
    """Document search response schema."""
    
    query: str
    results: List[DocumentSearchResult]
    total_results: int
    search_time_ms: float


class DocumentProcessingStatus(BaseModel):
    """Document processing status schema."""
    
    document_id: str
    status: DocumentStatus
    progress: float = Field(ge=0.0, le=1.0, description="Processing progress (0-1)")
    message: Optional[str] = None
    error: Optional[str] = None