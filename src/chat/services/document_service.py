"""Document service for handling file uploads and processing."""

import os
import aiofiles
from typing import List, Optional, BinaryIO
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, UploadFile
import structlog
import asyncio
from datetime import datetime

from chat.config import settings
from chat.models import (
    Document,
    DocumentStatus,
    DocumentType,
    DocumentResponse,
    DocumentProcessingStatus,
    DocumentChunk,
)
from chat.services.vector_store_service import vector_store_service
from chat.core import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for document management and processing."""
    
    def __init__(self):
        """Initialize document service."""
        # Create upload directory if it doesn't exist
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        
        logger.info("Document service initialized", upload_dir=str(self.upload_dir))
    
    def _get_file_type(self, filename: str) -> DocumentType:
        """Get document type from filename.
        
        Args:
            filename: File name
            
        Returns:
            Document type
        """
        suffix = Path(filename).suffix.lower()
        
        type_mapping = {
            ".pdf": DocumentType.PDF,
            ".txt": DocumentType.TEXT,
            ".md": DocumentType.MARKDOWN,
            ".docx": DocumentType.DOCX,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
        }
        
        return type_mapping.get(suffix, DocumentType.TEXT)
    
    def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file.
        
        Args:
            file: Uploaded file
            
        Raises:
            HTTPException: If file is invalid
        """
        # Check file size
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size too large. Maximum size is {settings.max_file_size} bytes."
            )
        
        # Check file type
        file_suffix = Path(file.filename or "").suffix.lower()
        if file_suffix not in settings.allowed_file_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_file_types)}"
            )
    
    async def _save_file(self, file: UploadFile, document_id: str) -> str:
        """Save uploaded file to disk.
        
        Args:
            file: Uploaded file
            document_id: Document ID for filename
            
        Returns:
            File path
        """
        # Generate unique filename
        file_extension = Path(file.filename or "").suffix
        filename = f"{document_id}{file_extension}"
        file_path = self.upload_dir / filename
        
        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        
        logger.info("File saved", file_path=str(file_path), size=len(content))
        
        return str(file_path)
    
    async def _extract_text(self, file_path: str, file_type: DocumentType) -> str:
        """Extract text content from file.
        
        Args:
            file_path: Path to file
            file_type: Type of document
            
        Returns:
            Extracted text content
        """
        try:
            if file_type == DocumentType.TEXT or file_type == DocumentType.MARKDOWN:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    return await f.read()
            
            elif file_type == DocumentType.PDF:
                # For PDF extraction, you would typically use a library like PyPDF2 or pdfplumber
                # For now, we'll return a placeholder
                return f"PDF content extraction not implemented for {file_path}"
            
            elif file_type == DocumentType.DOCX:
                # For DOCX extraction, you would use python-docx
                # For now, we'll return a placeholder
                return f"DOCX content extraction not implemented for {file_path}"
            
            elif file_type == DocumentType.HTML:
                # For HTML extraction, you would use BeautifulSoup
                # For now, we'll return a placeholder
                return f"HTML content extraction not implemented for {file_path}"
            
            else:
                return f"Unknown file type: {file_type}"
                
        except Exception as e:
            logger.error("Failed to extract text", file_path=file_path, error=str(e))
            raise
    
    async def upload_document(
        self,
        file: UploadFile,
        user_id: str,
        db_session: AsyncSession,
    ) -> DocumentResponse:
        """Upload and process a document.
        
        Args:
            file: Uploaded file
            user_id: User ID
            db_session: Database session
            
        Returns:
            Document response
        """
        logger.info("Uploading document", filename=file.filename, user_id=user_id)
        
        # Validate file
        self._validate_file(file)
        
        # Create document record
        document = Document(
            user_id=user_id,
            filename=file.filename or "unknown",
            original_filename=file.filename or "unknown",
            file_size=file.size or 0,
            file_type=self._get_file_type(file.filename or ""),
            content_type=file.content_type or "application/octet-stream",
            status=DocumentStatus.UPLOADED,
        )
        
        db_session.add(document)
        await db_session.commit()
        await db_session.refresh(document)
        
        try:
            # Save file to disk
            file_path = await self._save_file(file, str(document.id))
            document.file_path = file_path
            
            # Update status to processing
            document.status = DocumentStatus.PROCESSING
            await db_session.commit()
            
            # Process document in background
            asyncio.create_task(self._process_document_background(document.id, db_session))
            
            logger.info("Document uploaded successfully", document_id=str(document.id))
            
            return DocumentResponse.from_orm(document)
            
        except Exception as e:
            # Update status to failed
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            await db_session.commit()
            
            logger.error("Failed to upload document", document_id=str(document.id), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload document"
            )
    
    async def _process_document_background(self, document_id: str, db_session: AsyncSession) -> None:
        """Process document in background.
        
        Args:
            document_id: Document ID
            db_session: Database session
        """
        try:
            # Get document
            result = await db_session.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document or not document.file_path:
                return
            
            # Extract text content
            content = await self._extract_text(document.file_path, document.file_type)
            document.content = content
            
            # Process with vector store
            chunks = await vector_store_service.process_document(document, content, db_session)
            
            # Update document status
            document.status = DocumentStatus.INDEXED
            document.indexed_at = datetime.utcnow()
            
            await db_session.commit()
            
            logger.info(
                "Document processed successfully",
                document_id=document_id,
                chunk_count=len(chunks)
            )
            
        except Exception as e:
            # Update status to failed
            try:
                result = await db_session.execute(
                    select(Document).where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()
                if document:
                    document.status = DocumentStatus.FAILED
                    document.error_message = str(e)
                    await db_session.commit()
            except Exception:
                pass  # Ignore secondary errors
            
            logger.error("Failed to process document", document_id=document_id, error=str(e))
    
    async def get_document(self, document_id: str, db_session: AsyncSession) -> Optional[DocumentResponse]:
        """Get document by ID.
        
        Args:
            document_id: Document ID
            db_session: Database session
            
        Returns:
            Document response if found
        """
        try:
            result = await db_session.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if document:
                # Get chunk count
                chunk_result = await db_session.execute(
                    select(DocumentChunk).where(DocumentChunk.document_id == document_id)
                )
                chunks = chunk_result.scalars().all()
                
                doc_response = DocumentResponse.from_orm(document)
                doc_response.chunk_count = len(chunks)
                return doc_response
            
            return None
            
        except Exception as e:
            logger.error("Failed to get document", document_id=document_id, error=str(e))
            return None
    
    async def list_user_documents(
        self,
        user_id: str,
        db_session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DocumentResponse]:
        """List documents for a user.
        
        Args:
            user_id: User ID
            db_session: Database session
            limit: Maximum number of documents
            offset: Offset for pagination
            
        Returns:
            List of document responses
        """
        try:
            result = await db_session.execute(
                select(Document)
                .where(Document.user_id == user_id)
                .order_by(Document.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            documents = result.scalars().all()
            
            return [DocumentResponse.from_orm(doc) for doc in documents]
            
        except Exception as e:
            logger.error("Failed to list user documents", user_id=user_id, error=str(e))
            return []
    
    async def delete_document(self, document_id: str, user_id: str, db_session: AsyncSession) -> bool:
        """Delete a document.
        
        Args:
            document_id: Document ID
            user_id: User ID (for authorization)
            db_session: Database session
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await db_session.execute(
                select(Document).where(
                    (Document.id == document_id) & (Document.user_id == user_id)
                )
            )
            document = result.scalar_one_or_none()
            
            if not document:
                return False
            
            # Delete file from disk
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)
            
            # Delete vectors from vector store
            await vector_store_service.delete_document_vectors(document_id)
            
            # Delete from database (chunks will be deleted via cascade)
            await db_session.delete(document)
            await db_session.commit()
            
            logger.info("Document deleted successfully", document_id=document_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete document", document_id=document_id, error=str(e))
            return False
    
    async def get_processing_status(
        self, document_id: str, db_session: AsyncSession
    ) -> Optional[DocumentProcessingStatus]:
        """Get document processing status.
        
        Args:
            document_id: Document ID
            db_session: Database session
            
        Returns:
            Processing status if found
        """
        document = await self.get_document(document_id, db_session)
        
        if not document:
            return None
        
        # Calculate progress based on status
        progress_mapping = {
            DocumentStatus.UPLOADED: 0.1,
            DocumentStatus.PROCESSING: 0.5,
            DocumentStatus.INDEXED: 1.0,
            DocumentStatus.FAILED: 0.0,
        }
        
        return DocumentProcessingStatus(
            document_id=document_id,
            status=document.status,
            progress=progress_mapping.get(document.status, 0.0),
            message=self._get_status_message(document.status),
            error=document.error_message,
        )
    
    def _get_status_message(self, status: DocumentStatus) -> str:
        """Get human-readable status message.
        
        Args:
            status: Document status
            
        Returns:
            Status message
        """
        messages = {
            DocumentStatus.UPLOADED: "Document uploaded successfully",
            DocumentStatus.PROCESSING: "Processing document and creating embeddings",
            DocumentStatus.INDEXED: "Document processed and indexed successfully",
            DocumentStatus.FAILED: "Document processing failed",
        }
        
        return messages.get(status, "Unknown status")


# Global document service instance
document_service = DocumentService()