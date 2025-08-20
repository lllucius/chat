"""Document management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.document import Document, DocumentUpload, DocumentUpdate
from app.dependencies import get_current_active_user, get_document_service
from app.core.exceptions import ValidationError, NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents")


@router.post("/upload", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    tags: str = Query("", description="Comma-separated tags"),
    is_public: bool = Query(False, description="Make document public"),
    current_user: User = Depends(get_current_active_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Upload a document for knowledge base."""
    try:
        # Read file content
        file_content = await file.read()
        
        # Create upload data
        upload_data = DocumentUpload(
            filename=file.filename or "unnamed_file",
            content_type=file.content_type or "application/octet-stream",
            tags=tags,
            is_public=is_public
        )
        
        # Process upload
        document = await document_service.upload_document(
            user=current_user,
            file_content=file_content,
            upload_data=upload_data
        )
        
        logger.info(
            "Document uploaded",
            document_id=document.id,
            user_id=current_user.id,
            filename=document.filename
        )
        
        return document
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Document upload failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


@router.get("/", response_model=List[Document])
async def get_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    file_types: str = Query("", description="Comma-separated file types"),
    tags: str = Query("", description="Comma-separated tags"),
    include_public: bool = Query(True),
    current_user: User = Depends(get_current_active_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Get user documents."""
    try:
        file_type_list = file_types.split(",") if file_types else None
        tag_list = tags.split(",") if tags else None
        
        documents = await document_service.get_user_documents(
            user=current_user,
            limit=limit,
            offset=offset,
            file_types=file_type_list,
            tags=tag_list,
            include_public=include_public
        )
        
        return documents
        
    except Exception as e:
        logger.error("Document retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.get("/search")
async def search_documents(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_active_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Search documents using semantic similarity."""
    try:
        results = await document_service.search_documents(
            query=query,
            user=current_user,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        return {"results": results}
        
    except Exception as e:
        logger.error("Document search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search documents"
        )


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Get document by ID."""
    try:
        document = await document_service.get_document(document_id, current_user)
        return document
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )


@router.put("/{document_id}", response_model=Document)
async def update_document(
    document_id: int,
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Update document metadata."""
    try:
        document = await document_service.update_document(
            document_id=document_id,
            user=current_user,
            update_data=update_data
        )
        return document
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Delete document."""
    try:
        await document_service.delete_document(document_id, current_user)
        return {"message": "Document deleted successfully"}
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )


@router.get("/stats/summary")
async def get_document_stats(
    current_user: User = Depends(get_current_active_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Get document statistics for user."""
    try:
        stats = await document_service.get_document_stats(current_user)
        return stats
    except Exception as e:
        logger.error("Document stats retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document statistics"
        )