"""Document service for managing document uploads and processing."""

import hashlib
import asyncio
from typing import List, Optional, Dict, Any, BinaryIO
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentUpload
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService
from app.utils.document_processor import DocumentProcessor
from app.core.exceptions import ValidationError, NotFoundError, ConflictError
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class DocumentService:
    """Service for managing document uploads and processing."""
    
    def __init__(self, db: AsyncSession, vector_service: VectorService) -> None:
        self.db = db
        self.vector_service = vector_service
        self.llm_service = LLMService()
        self.processor = DocumentProcessor()
    
    async def upload_document(
        self,
        user: User,
        file_content: bytes,
        upload_data: DocumentUpload
    ) -> Document:
        """
        Upload and process a document.
        
        Args:
            user: User uploading the document
            file_content: File content as bytes
            upload_data: Document upload metadata
            
        Returns:
            Created document
            
        Raises:
            ValidationError: If file validation fails
            ConflictError: If document already exists
        """
        # Validate file
        self._validate_file(file_content, upload_data)
        
        # Generate content hash
        content_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check for duplicate
        existing = await self._check_duplicate(user.id, content_hash)
        if existing:
            raise ConflictError(f"Document with same content already exists: {existing.filename}")
        
        # Process document content
        try:
            processed_content = await self.processor.extract_text(
                file_content,
                upload_data.content_type
            )
        except Exception as e:
            logger.error("Document processing failed", error=str(e))
            raise ValidationError(f"Failed to process document: {str(e)}")
        
        # Create document record
        document = Document(
            user_id=user.id,
            filename=upload_data.filename,
            original_filename=upload_data.filename,
            file_type=self._get_file_extension(upload_data.filename),
            file_size=len(file_content),
            mime_type=upload_data.content_type,
            content=processed_content,
            content_hash=content_hash,
            tags=upload_data.tags,
            is_public=upload_data.is_public,
            metadata=str(upload_data.metadata) if upload_data.metadata else None,
            processing_status="completed"
        )
        
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        
        # Generate embeddings in background
        asyncio.create_task(self._process_document_embeddings(document))
        
        logger.info(
            "Document uploaded",
            document_id=document.id,
            user_id=user.id,
            filename=document.filename,
            size=document.file_size
        )
        
        return document
    
    async def get_document(self, document_id: int, user: User) -> Document:
        """
        Get a document by ID.
        
        Args:
            document_id: Document ID
            user: User requesting the document
            
        Returns:
            Document
            
        Raises:
            NotFoundError: If document not found or access denied
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                (Document.user_id == user.id) | (Document.is_public == True)
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise NotFoundError(f"Document {document_id} not found")
        
        # Update access statistics
        document.access_count += 1
        document.last_accessed = datetime.utcnow()
        await self.db.commit()
        
        return document
    
    async def get_user_documents(
        self,
        user: User,
        limit: int = 50,
        offset: int = 0,
        file_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        include_public: bool = True
    ) -> List[Document]:
        """
        Get documents for a user.
        
        Args:
            user: User requesting documents
            limit: Maximum number of documents
            offset: Offset for pagination
            file_types: Filter by file types
            tags: Filter by tags
            include_public: Include public documents
            
        Returns:
            List of documents
        """
        query = select(Document).where(Document.is_active == True)
        
        # Filter by user or public documents
        if include_public:
            query = query.where(
                (Document.user_id == user.id) | (Document.is_public == True)
            )
        else:
            query = query.where(Document.user_id == user.id)
        
        # Apply filters
        if file_types:
            query = query.where(Document.file_type.in_(file_types))
        
        if tags:
            # Simple tag filtering (contains any of the specified tags)
            tag_conditions = [Document.tags.contains(tag) for tag in tags]
            query = query.where(func.or_(*tag_conditions))
        
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        documents = result.scalars().all()
        
        return list(documents)
    
    async def update_document(
        self,
        document_id: int,
        user: User,
        update_data: DocumentUpdate
    ) -> Document:
        """
        Update document metadata.
        
        Args:
            document_id: Document ID
            user: User updating the document
            update_data: Updated document data
            
        Returns:
            Updated document
            
        Raises:
            NotFoundError: If document not found
        """
        # Get document (user must own it)
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user.id
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise NotFoundError(f"Document {document_id} not found")
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if field == "metadata" and value:
                setattr(document, field, str(value))
            else:
                setattr(document, field, value)
        
        await self.db.commit()
        await self.db.refresh(document)
        
        logger.info("Document updated", document_id=document.id, user_id=user.id)
        return document
    
    async def delete_document(self, document_id: int, user: User) -> None:
        """
        Delete a document (soft delete).
        
        Args:
            document_id: Document ID
            user: User deleting the document
            
        Raises:
            NotFoundError: If document not found
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user.id
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise NotFoundError(f"Document {document_id} not found")
        
        # Soft delete
        document.is_active = False
        await self.db.commit()
        
        logger.info("Document deleted", document_id=document.id, user_id=user.id)
    
    async def search_documents(
        self,
        query: str,
        user: User,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        file_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search documents using vector similarity.
        
        Args:
            query: Search query
            user: User performing the search
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            file_types: Filter by file types
            tags: Filter by tags
            
        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            query_embedding = await self.llm_service.generate_embedding(query)
            
            # Perform vector search
            search_results = await self.vector_service.search_documents(
                query_embedding=query_embedding,
                user_id=user.id,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            # Apply additional filters if needed
            filtered_results = []
            for result in search_results:
                document = result.document
                
                # File type filter
                if file_types and document.file_type not in file_types:
                    continue
                
                # Tag filter
                if tags and document.tags:
                    doc_tags = [tag.strip() for tag in document.tags.split(",")]
                    if not any(tag in doc_tags for tag in tags):
                        continue
                
                filtered_results.append({
                    "document": document,
                    "similarity_score": result.similarity_score,
                    "relevant_chunks": result.relevant_chunks
                })
            
            logger.info(
                "Document search completed",
                query_length=len(query),
                results_count=len(filtered_results),
                user_id=user.id
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error("Document search failed", error=str(e))
            return []
    
    async def get_document_stats(self, user: User) -> Dict[str, Any]:
        """
        Get document statistics for a user.
        
        Args:
            user: User requesting statistics
            
        Returns:
            Dictionary with document statistics
        """
        # Total documents
        total_result = await self.db.execute(
            select(func.count(Document.id))
            .where(Document.user_id == user.id, Document.is_active == True)
        )
        total_documents = total_result.scalar()
        
        # Documents by file type
        type_result = await self.db.execute(
            select(Document.file_type, func.count(Document.id))
            .where(Document.user_id == user.id, Document.is_active == True)
            .group_by(Document.file_type)
        )
        documents_by_type = {row[0]: row[1] for row in type_result.fetchall()}
        
        # Total storage used
        storage_result = await self.db.execute(
            select(func.sum(Document.file_size))
            .where(Document.user_id == user.id, Document.is_active == True)
        )
        total_storage = storage_result.scalar() or 0
        
        # Documents with embeddings
        embedded_result = await self.db.execute(
            select(func.count(Document.id))
            .where(
                Document.user_id == user.id,
                Document.is_active == True,
                Document.embedding.is_not(None)
            )
        )
        documents_with_embeddings = embedded_result.scalar()
        
        # Recent uploads
        recent_result = await self.db.execute(
            select(func.count(Document.id))
            .where(
                Document.user_id == user.id,
                Document.is_active == True,
                Document.created_at >= func.date_trunc('week', func.now())
            )
        )
        recent_uploads = recent_result.scalar()
        
        return {
            "total_documents": total_documents,
            "documents_by_type": documents_by_type,
            "total_storage_bytes": total_storage,
            "total_storage_mb": round(total_storage / 1024 / 1024, 2),
            "documents_with_embeddings": documents_with_embeddings,
            "embedding_coverage_percent": (
                round(documents_with_embeddings / total_documents * 100, 1)
                if total_documents > 0 else 0
            ),
            "recent_uploads": recent_uploads
        }
    
    def _validate_file(self, file_content: bytes, upload_data: DocumentUpload) -> None:
        """Validate uploaded file."""
        # Check file size
        if len(file_content) > settings.max_file_size_mb * 1024 * 1024:
            raise ValidationError(f"File size exceeds {settings.max_file_size_mb} MB limit")
        
        # Check file type
        file_ext = self._get_file_extension(upload_data.filename)
        if file_ext not in settings.allowed_file_types:
            raise ValidationError(
                f"File type '{file_ext}' not allowed. "
                f"Allowed types: {', '.join(settings.allowed_file_types)}"
            )
        
        # Check content type
        if not upload_data.content_type:
            raise ValidationError("Content type is required")
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename."""
        return filename.split(".")[-1].lower() if "." in filename else ""
    
    async def _check_duplicate(self, user_id: int, content_hash: str) -> Optional[Document]:
        """Check if document with same content already exists."""
        result = await self.db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.content_hash == content_hash,
                Document.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def _process_document_embeddings(self, document: Document) -> None:
        """Process document embeddings in background."""
        try:
            # Update processing status
            document.processing_status = "processing"
            await self.db.commit()
            
            # Generate embedding for the full document
            embedding = await self.llm_service.generate_embedding(
                document.content[:8000]  # Limit content for embedding
            )
            
            # Store embedding
            await self.vector_service.store_document_embedding(document.id, embedding)
            
            # Update processing status
            document.processing_status = "completed"
            document.chunk_count = 1  # For now, treating whole document as one chunk
            await self.db.commit()
            
            logger.info("Document embeddings processed", document_id=document.id)
            
        except Exception as e:
            logger.error("Document embedding processing failed", document_id=document.id, error=str(e))
            
            # Update error status
            document.processing_status = "failed"
            document.processing_error = str(e)
            await self.db.commit()