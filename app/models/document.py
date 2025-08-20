"""Document model for knowledge base documents."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Boolean, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Document(Base):
    """Document model for knowledge base documents."""
    
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Document metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Document content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 hash
    
    # Processing status
    processing_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # 'pending', 'processing', 'completed', 'failed'
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Vector embedding for semantic search
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1536), nullable=True)
    
    # Document chunks for RAG
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Statistics
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"), nullable=True)
    
    # Metadata
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Comma-separated tags
    
    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
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
    user: Mapped["User"] = relationship("User", back_populates="documents")
    
    # Self-referential relationship for document versions
    child_documents: Mapped[list["Document"]] = relationship(
        "Document",
        remote_side=[parent_document_id],
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of the document."""
        return f"<Document(id={self.id}, filename='{self.filename}', user_id={self.user_id})>"