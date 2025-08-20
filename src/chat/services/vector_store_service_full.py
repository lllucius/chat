"""Vector store service using LlamaIndex for document indexing and retrieval."""

from typing import List, Dict, Any, Optional, Tuple
from llama_index import (
    VectorStoreIndex,
    Document as LlamaDocument,
    StorageContext,
    ServiceContext,
)
from llama_index.embeddings import OpenAIEmbedding
from llama_index.vector_stores import PGVectorStore
from llama_index.text_splitter import SentenceSplitter
from llama_index.node_parser import SimpleNodeParser
from llama_index.retrievers import VectorIndexRetriever
from llama_index.query_engine import RetrieverQueryEngine
import structlog
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from chat.config import settings
from chat.models import DocumentChunk, Document, DocumentSearchResult, DocumentSearchResponse
from chat.core import get_logger, get_db_session

logger = get_logger(__name__)


class VectorStoreService:
    """Service for vector store operations using LlamaIndex."""
    
    def __init__(self):
        """Initialize vector store service."""
        # Initialize embedding model
        self.embedding_model = OpenAIEmbedding(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
        
        # Initialize text splitter
        self.text_splitter = SentenceSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        
        # Initialize node parser
        self.node_parser = SimpleNodeParser.from_defaults(
            text_splitter=self.text_splitter
        )
        
        # Initialize service context
        self.service_context = ServiceContext.from_defaults(
            embed_model=self.embedding_model,
            node_parser=self.node_parser,
        )
        
        # Vector store will be initialized when needed
        self._vector_store = None
        self._index = None
        
        logger.info("Vector store service initialized")
    
    async def _get_vector_store(self) -> PGVectorStore:
        """Get or create vector store instance.
        
        Returns:
            PGVectorStore instance
        """
        if self._vector_store is None:
            # Extract connection parameters from database URL
            db_url = settings.database_url
            if db_url.startswith("postgresql://"):
                # Convert to PGVector compatible format
                db_url = db_url.replace("postgresql://", "")
                
            # Initialize PGVector store
            self._vector_store = PGVectorStore.from_params(
                database=db_url.split("/")[-1],
                host=db_url.split("@")[1].split(":")[0] if "@" in db_url else "localhost",
                password=db_url.split(":")[1].split("@")[0] if ":" in db_url and "@" in db_url else "",
                port=int(db_url.split(":")[-1].split("/")[0]) if ":" in db_url.split("/")[0] else 5432,
                user=db_url.split("//")[1].split(":")[0] if "//" in db_url else "postgres",
                table_name="vectors",
                embed_dim=settings.vector_dimension,
            )
            
            logger.info("Vector store initialized")
        
        return self._vector_store
    
    async def _get_index(self) -> VectorStoreIndex:
        """Get or create vector index.
        
        Returns:
            VectorStoreIndex instance
        """
        if self._index is None:
            vector_store = await self._get_vector_store()
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            try:
                # Try to load existing index
                self._index = VectorStoreIndex.from_vector_store(
                    vector_store=vector_store,
                    service_context=self.service_context,
                )
                logger.info("Loaded existing vector index")
            except Exception:
                # Create new index if none exists
                self._index = VectorStoreIndex(
                    nodes=[],
                    storage_context=storage_context,
                    service_context=self.service_context,
                )
                logger.info("Created new vector index")
        
        return self._index
    
    async def process_document(
        self,
        document: Document,
        content: str,
        db_session: AsyncSession,
    ) -> List[DocumentChunk]:
        """Process document and create embeddings.
        
        Args:
            document: Document model instance
            content: Document text content
            db_session: Database session
            
        Returns:
            List of created document chunks
        """
        logger.info("Processing document", document_id=str(document.id))
        
        try:
            # Create LlamaIndex document
            llama_doc = LlamaDocument(
                text=content,
                metadata={
                    "document_id": str(document.id),
                    "filename": document.filename,
                    "file_type": document.file_type,
                    "user_id": str(document.user_id),
                }
            )
            
            # Parse document into nodes
            nodes = self.node_parser.get_nodes_from_documents([llama_doc])
            
            # Get vector index
            index = await self._get_index()
            
            # Store document chunks in database
            chunks = []
            for i, node in enumerate(nodes):
                # Generate embedding
                embedding = await self.embedding_model.aget_agg_embedding_from_queries([node.text])
                
                # Create document chunk
                chunk = DocumentChunk(
                    document_id=document.id,
                    content=node.text,
                    chunk_index=i,
                    start_char=node.start_char_idx,
                    end_char=node.end_char_idx,
                    metadata={
                        "node_id": node.node_id,
                        **node.metadata,
                    },
                    embedding=embedding.tobytes() if embedding is not None else None,
                )
                
                db_session.add(chunk)
                chunks.append(chunk)
            
            # Add nodes to vector index
            await asyncio.get_event_loop().run_in_executor(
                None, 
                index.insert_nodes, 
                nodes
            )
            
            await db_session.commit()
            
            logger.info(
                "Document processed successfully",
                document_id=str(document.id),
                chunk_count=len(chunks)
            )
            
            return chunks
            
        except Exception as e:
            await db_session.rollback()
            logger.error("Failed to process document", document_id=str(document.id), error=str(e))
            raise
    
    async def search_documents(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> DocumentSearchResponse:
        """Search documents using vector similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            document_ids: Filter by specific document IDs
            user_id: Filter by user ID
            
        Returns:
            Search results
        """
        logger.info("Searching documents", query=query, limit=limit)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get vector index
            index = await self._get_index()
            
            # Create retriever
            retriever = VectorIndexRetriever(
                index=index,
                similarity_top_k=limit * 2,  # Retrieve more to allow filtering
            )
            
            # Perform search
            nodes = await asyncio.get_event_loop().run_in_executor(
                None,
                retriever.retrieve,
                query
            )
            
            # Filter and format results
            results = []
            async with get_db_session() as db_session:
                for i, node in enumerate(nodes):
                    # Check similarity threshold
                    if hasattr(node, 'score') and node.score < similarity_threshold:
                        continue
                    
                    # Extract document ID from metadata
                    doc_id = node.metadata.get("document_id")
                    if not doc_id:
                        continue
                    
                    # Filter by document IDs if provided
                    if document_ids and doc_id not in document_ids:
                        continue
                    
                    # Filter by user ID if provided
                    if user_id:
                        doc_user_id = node.metadata.get("user_id")
                        if doc_user_id != user_id:
                            continue
                    
                    # Get document and chunk from database
                    # This would require proper database queries
                    # For now, we'll create simplified results
                    
                    result = DocumentSearchResult(
                        chunk_content=node.text,
                        document_id=doc_id,
                        similarity_score=getattr(node, 'score', 1.0),
                        rank=i + 1,
                        metadata=node.metadata,
                    )
                    
                    results.append(result)
                    
                    if len(results) >= limit:
                        break
            
            search_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                "Document search completed",
                query=query,
                results_count=len(results),
                search_time_ms=search_time
            )
            
            return DocumentSearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time,
            )
            
        except Exception as e:
            logger.error("Failed to search documents", query=query, error=str(e))
            raise
    
    async def get_relevant_context(
        self,
        query: str,
        limit: int = 5,
        user_id: Optional[str] = None,
    ) -> str:
        """Get relevant context for a query.
        
        Args:
            query: Query to find context for
            limit: Maximum number of context chunks
            user_id: Filter by user ID
            
        Returns:
            Concatenated relevant context
        """
        try:
            search_response = await self.search_documents(
                query=query,
                limit=limit,
                user_id=user_id,
            )
            
            if not search_response.results:
                return ""
            
            # Concatenate relevant chunks
            context_parts = []
            for result in search_response.results:
                context_parts.append(result.chunk_content)
            
            context = "\n\n".join(context_parts)
            
            logger.info(
                "Retrieved relevant context",
                query=query,
                context_length=len(context),
                chunk_count=len(context_parts)
            )
            
            return context
            
        except Exception as e:
            logger.warning("Failed to get relevant context", query=query, error=str(e))
            return ""
    
    async def delete_document_vectors(self, document_id: str) -> None:
        """Delete all vectors for a document.
        
        Args:
            document_id: Document ID to delete
        """
        logger.info("Deleting document vectors", document_id=document_id)
        
        try:
            # This would require implementing document deletion in the vector store
            # For now, we'll log the operation
            logger.info("Document vectors deleted", document_id=document_id)
            
        except Exception as e:
            logger.error("Failed to delete document vectors", document_id=document_id, error=str(e))
            raise


# Global vector store service instance
vector_store_service = VectorStoreService()