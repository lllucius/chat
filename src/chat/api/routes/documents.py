"""Document management routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from chat.core import get_db_session
from chat.models import (
    User,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentProcessingStatus,
)
from chat.services import document_service, vector_store_service
from chat.api.dependencies import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Upload a document for processing and indexing.
    
    Args:
        file: File to upload
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Document response
    """
    return await document_service.upload_document(file, str(current_user.id), db_session)


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> List[DocumentResponse]:
    """List user's documents.
    
    Args:
        current_user: Current authenticated user
        db_session: Database session
        limit: Maximum number of documents
        offset: Offset for pagination
        
    Returns:
        List of documents
    """
    return await document_service.list_user_documents(
        str(current_user.id), db_session, limit, offset
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Get a specific document.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Document details
    """
    document = await document_service.get_document(document_id, db_session)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check if user owns the document
    if document.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )
    
    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a document.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Success message
    """
    success = await document_service.delete_document(
        document_id, str(current_user.id), db_session
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/status", response_model=DocumentProcessingStatus)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> DocumentProcessingStatus:
    """Get document processing status.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Processing status
    """
    status_info = await document_service.get_processing_status(document_id, db_session)
    
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Verify user owns the document by checking if we can get it
    document = await document_service.get_document(document_id, db_session)
    if not document or document.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )
    
    return status_info


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    search_request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> DocumentSearchResponse:
    """Search documents using vector similarity.
    
    Args:
        search_request: Search parameters
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Search results
    """
    return await vector_store_service.search_documents(
        query=search_request.query,
        limit=search_request.limit,
        similarity_threshold=search_request.similarity_threshold,
        document_ids=search_request.document_ids,
        user_id=str(current_user.id),
    )