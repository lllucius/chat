"""Vector store service for managing document embeddings and similarity search."""

import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from pgvector.sqlalchemy import Vector

from app.models.document import Document
from app.models.message import Message
from app.schemas.document import DocumentSearchResult
from app.schemas.message import MessageSearchResult
from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorService:
    """Service for vector operations and similarity search."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def store_document_embedding(
        self, 
        document_id: int, 
        embedding: List[float]
    ) -> None:
        """
        Store document embedding in the vector store.
        
        Args:
            document_id: Document ID
            embedding: Embedding vector
        """
        try:
            # Update document with embedding
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise VectorStoreError(f"Document {document_id} not found")
            
            # Convert embedding to pgvector format
            document.embedding = embedding
            await self.db.commit()
            
            logger.info("Document embedding stored", document_id=document_id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to store document embedding", error=str(e))
            raise VectorStoreError(f"Failed to store embedding: {str(e)}")
    
    async def store_message_embedding(
        self, 
        message_id: int, 
        embedding: List[float]
    ) -> None:
        """
        Store message embedding for semantic search.
        
        Args:
            message_id: Message ID
            embedding: Embedding vector
        """
        try:
            # Update message with embedding (stored as JSON)
            result = await self.db.execute(
                select(Message).where(Message.id == message_id)
            )
            message = result.scalar_one_or_none()
            
            if not message:
                raise VectorStoreError(f"Message {message_id} not found")
            
            # Store embedding as JSON string
            message.embedding = json.dumps(embedding)
            await self.db.commit()
            
            logger.info("Message embedding stored", message_id=message_id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to store message embedding", error=str(e))
            raise VectorStoreError(f"Failed to store embedding: {str(e)}")
    
    async def search_documents(
        self,
        query_embedding: List[float],
        user_id: Optional[int] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentSearchResult]:
        """
        Search documents using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            user_id: Optional user ID filter
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            filter_metadata: Optional metadata filters
            
        Returns:
            List of document search results
        """
        try:
            # Build base query
            query = select(
                Document,
                (1 - Document.embedding.cosine_distance(query_embedding)).label("similarity")
            ).where(
                Document.is_active == True,
                Document.embedding.is_not(None),
                (1 - Document.embedding.cosine_distance(query_embedding)) >= similarity_threshold
            )
            
            # Add user filter if specified
            if user_id:
                query = query.where(
                    (Document.user_id == user_id) | (Document.is_public == True)
                )
            else:
                query = query.where(Document.is_public == True)
            
            # Order by similarity and limit results
            query = query.order_by(
                (1 - Document.embedding.cosine_distance(query_embedding)).desc()
            ).limit(limit)
            
            result = await self.db.execute(query)
            rows = result.all()
            
            search_results = []
            for document, similarity in rows:
                # Update access statistics
                document.access_count += 1
                document.last_accessed = func.now()
                
                search_results.append(
                    DocumentSearchResult(
                        document=document,
                        similarity_score=float(similarity),
                        relevant_chunks=[]  # TODO: Implement chunk extraction
                    )
                )
            
            await self.db.commit()
            
            logger.info(
                "Document search completed",
                results_count=len(search_results),
                user_id=user_id,
                threshold=similarity_threshold
            )
            
            return search_results
            
        except Exception as e:
            logger.error("Document search failed", error=str(e))
            raise VectorStoreError(f"Document search failed: {str(e)}")
    
    async def search_messages(
        self,
        query_embedding: List[float],
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[MessageSearchResult]:
        """
        Search messages using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            user_id: Optional user ID filter (via conversation)
            conversation_id: Optional conversation ID filter
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of message search results
        """
        try:
            # For message search, we need to use raw SQL due to JSON embedding storage
            similarity_sql = """
                SELECT m.*, c.user_id,
                       1 - (m.embedding::vector <=> %s::vector) as similarity
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE m.embedding IS NOT NULL
                  AND m.is_deleted = false
                  AND 1 - (m.embedding::vector <=> %s::vector) >= %s
            """
            
            params = [query_embedding, query_embedding, similarity_threshold]
            
            # Add filters
            if user_id:
                similarity_sql += " AND c.user_id = %s"
                params.append(user_id)
            
            if conversation_id:
                similarity_sql += " AND m.conversation_id = %s"
                params.append(conversation_id)
            
            similarity_sql += " ORDER BY similarity DESC LIMIT %s"
            params.append(limit)
            
            result = await self.db.execute(text(similarity_sql), params)
            rows = result.fetchall()
            
            search_results = []
            for row in rows:
                # Create message object
                message = Message(
                    id=row.id,
                    conversation_id=row.conversation_id,
                    content=row.content,
                    role=row.role,
                    message_type=row.message_type,
                    metadata=row.metadata,
                    is_edited=row.is_edited,
                    is_deleted=row.is_deleted,
                    token_count=row.token_count,
                    processing_time=row.processing_time,
                    model_used=row.model_used,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                )
                
                search_results.append(
                    MessageSearchResult(
                        message=message,
                        similarity_score=float(row.similarity),
                        highlights=[]  # TODO: Implement highlighting
                    )
                )
            
            logger.info(
                "Message search completed",
                results_count=len(search_results),
                user_id=user_id,
                conversation_id=conversation_id
            )
            
            return search_results
            
        except Exception as e:
            logger.error("Message search failed", error=str(e))
            raise VectorStoreError(f"Message search failed: {str(e)}")
    
    async def find_similar_documents(
        self,
        document_id: int,
        limit: int = 5,
        similarity_threshold: float = 0.8
    ) -> List[DocumentSearchResult]:
        """
        Find documents similar to a given document.
        
        Args:
            document_id: Reference document ID
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of similar documents
        """
        try:
            # Get the reference document's embedding
            result = await self.db.execute(
                select(Document.embedding, Document.user_id, Document.is_public)
                .where(Document.id == document_id)
            )
            row = result.first()
            
            if not row or not row.embedding:
                raise VectorStoreError(f"Document {document_id} not found or has no embedding")
            
            reference_embedding = row.embedding
            user_id = row.user_id
            is_public = row.is_public
            
            # Search for similar documents
            query = select(
                Document,
                (1 - Document.embedding.cosine_distance(reference_embedding)).label("similarity")
            ).where(
                Document.id != document_id,  # Exclude the reference document
                Document.is_active == True,
                Document.embedding.is_not(None),
                (1 - Document.embedding.cosine_distance(reference_embedding)) >= similarity_threshold
            )
            
            # Apply visibility filters
            if not is_public:
                query = query.where(
                    (Document.user_id == user_id) | (Document.is_public == True)
                )
            else:
                query = query.where(Document.is_public == True)
            
            query = query.order_by(
                (1 - Document.embedding.cosine_distance(reference_embedding)).desc()
            ).limit(limit)
            
            result = await self.db.execute(query)
            rows = result.all()
            
            similar_documents = []
            for document, similarity in rows:
                similar_documents.append(
                    DocumentSearchResult(
                        document=document,
                        similarity_score=float(similarity),
                        relevant_chunks=[]
                    )
                )
            
            logger.info(
                "Similar documents found",
                reference_document_id=document_id,
                results_count=len(similar_documents)
            )
            
            return similar_documents
            
        except Exception as e:
            logger.error("Similar document search failed", error=str(e))
            raise VectorStoreError(f"Similar document search failed: {str(e)}")
    
    async def get_vector_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.
        
        Returns:
            Dictionary with vector store statistics
        """
        try:
            # Count documents with embeddings
            doc_result = await self.db.execute(
                select(func.count(Document.id))
                .where(Document.embedding.is_not(None))
            )
            documents_with_embeddings = doc_result.scalar()
            
            # Count messages with embeddings
            msg_result = await self.db.execute(
                select(func.count(Message.id))
                .where(Message.embedding.is_not(None))
            )
            messages_with_embeddings = msg_result.scalar()
            
            # Total documents and messages
            total_docs_result = await self.db.execute(select(func.count(Document.id)))
            total_documents = total_docs_result.scalar()
            
            total_msgs_result = await self.db.execute(select(func.count(Message.id)))
            total_messages = total_msgs_result.scalar()
            
            stats = {
                "total_documents": total_documents,
                "documents_with_embeddings": documents_with_embeddings,
                "document_embedding_coverage": (
                    documents_with_embeddings / total_documents * 100 
                    if total_documents > 0 else 0
                ),
                "total_messages": total_messages,
                "messages_with_embeddings": messages_with_embeddings,
                "message_embedding_coverage": (
                    messages_with_embeddings / total_messages * 100 
                    if total_messages > 0 else 0
                ),
                "vector_dimension": 1536  # OpenAI embedding dimension
            }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get vector stats", error=str(e))
            raise VectorStoreError(f"Failed to get vector stats: {str(e)}")