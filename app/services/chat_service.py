"""Chat service for managing conversations and messages."""

import asyncio
import time
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.profile import Profile
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, StreamingChatResponse
from app.schemas.conversation import ConversationCreate
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service for managing chat conversations and messages."""
    
    def __init__(
        self, 
        db: AsyncSession, 
        llm_service: LLMService, 
        vector_service: VectorService
    ) -> None:
        self.db = db
        self.llm_service = llm_service
        self.vector_service = vector_service
    
    async def create_conversation(
        self, 
        user: User, 
        title: str,
        context_settings: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            user: User creating the conversation
            title: Conversation title
            context_settings: Optional LLM context settings
            
        Returns:
            Created conversation
        """
        conversation = Conversation(
            title=title,
            user_id=user.id,
            context_settings=str(context_settings) if context_settings else None
        )
        
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        
        logger.info("Conversation created", conversation_id=conversation.id, user_id=user.id)
        return conversation
    
    async def get_conversation(
        self, 
        conversation_id: int, 
        user: User,
        include_messages: bool = False
    ) -> Conversation:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            user: User requesting the conversation
            include_messages: Whether to include messages
            
        Returns:
            Conversation
            
        Raises:
            NotFoundError: If conversation not found or access denied
        """
        query = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id
        )
        
        if include_messages:
            query = query.options(selectinload(Conversation.messages))
        
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        return conversation
    
    async def get_user_conversations(
        self, 
        user: User,
        limit: int = 50,
        offset: int = 0,
        include_inactive: bool = False
    ) -> List[Conversation]:
        """
        Get conversations for a user.
        
        Args:
            user: User requesting conversations
            limit: Maximum number of conversations
            offset: Offset for pagination
            include_inactive: Whether to include inactive conversations
            
        Returns:
            List of conversations
        """
        query = select(Conversation).where(Conversation.user_id == user.id)
        
        if not include_inactive:
            query = query.where(Conversation.is_active == True)
        
        query = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        conversations = result.scalars().all()
        
        return list(conversations)
    
    async def send_message(
        self,
        chat_request: ChatRequest,
        user: User
    ) -> ChatResponse:
        """
        Send a message and get AI response.
        
        Args:
            chat_request: Chat request with message and options
            user: User sending the message
            
        Returns:
            Chat response with AI message
        """
        start_time = time.time()
        
        # Get or create conversation
        if chat_request.conversation_id:
            conversation = await self.get_conversation(chat_request.conversation_id, user)
        else:
            conversation = await self.create_conversation(
                user=user,
                title=chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message
            )
        
        # Get profile settings
        profile = await self._get_user_profile(user, chat_request.profile_id)
        
        # Save user message
        user_message = await self._save_message(
            conversation_id=conversation.id,
            content=chat_request.message,
            role="user"
        )
        
        # Build context for LLM
        messages = await self._build_conversation_context(
            conversation,
            profile,
            chat_request.context
        )
        
        # Add current user message
        messages.append(ChatMessage(role="user", content=chat_request.message))
        
        # Get relevant documents if retrieval is enabled
        sources = []
        if chat_request.use_retrieval and profile.retrieval_enabled:
            sources = await self._retrieve_relevant_documents(
                chat_request.message,
                user,
                profile
            )
            
            # Add retrieved documents to context
            if sources:
                context_content = self._format_retrieval_context(sources)
                messages.insert(-1, ChatMessage(
                    role="system",
                    content=f"Relevant information from documents:\n{context_content}"
                ))
        
        # Generate AI response
        llm_response = await self.llm_service.generate_response(
            messages=messages,
            system_prompt=profile.system_prompt,
            temperature=chat_request.temperature or profile.temperature,
            max_tokens=chat_request.max_tokens or profile.max_tokens,
            stream=False
        )
        
        # Save AI message
        ai_message = await self._save_message(
            conversation_id=conversation.id,
            content=llm_response["content"],
            role="assistant",
            token_count=llm_response["token_count"],
            processing_time=llm_response["processing_time"],
            model_used=llm_response["model_used"],
            metadata=llm_response.get("metadata")
        )
        
        # Update conversation statistics
        await self._update_conversation_stats(conversation, llm_response["token_count"])
        
        # Update profile usage
        await self._update_profile_usage(profile, llm_response["token_count"])
        
        # Generate embeddings for messages (background task)
        asyncio.create_task(self._generate_message_embeddings(user_message, ai_message))
        
        processing_time = time.time() - start_time
        
        logger.info(
            "Chat message processed",
            conversation_id=conversation.id,
            user_id=user.id,
            processing_time=processing_time,
            token_count=llm_response["token_count"]
        )
        
        return ChatResponse(
            message=llm_response["content"],
            conversation_id=conversation.id,
            message_id=ai_message.id,
            model_used=llm_response["model_used"],
            token_count=llm_response["token_count"],
            processing_time=processing_time,
            sources=[{
                "document_id": source.document.id,
                "filename": source.document.filename,
                "similarity_score": source.similarity_score,
                "relevant_chunks": source.relevant_chunks
            } for source in sources],
            metadata=chat_request.metadata
        )
    
    async def stream_message(
        self,
        chat_request: ChatRequest,
        user: User
    ) -> AsyncGenerator[StreamingChatResponse, None]:
        """
        Send a message and stream AI response.
        
        Args:
            chat_request: Chat request with message and options
            user: User sending the message
            
        Yields:
            Streaming chat response chunks
        """
        # Get or create conversation
        if chat_request.conversation_id:
            conversation = await self.get_conversation(chat_request.conversation_id, user)
        else:
            conversation = await self.create_conversation(
                user=user,
                title=chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message
            )
        
        # Get profile settings
        profile = await self._get_user_profile(user, chat_request.profile_id)
        
        # Save user message
        user_message = await self._save_message(
            conversation_id=conversation.id,
            content=chat_request.message,
            role="user"
        )
        
        # Build context for LLM
        messages = await self._build_conversation_context(
            conversation,
            profile,
            chat_request.context
        )
        
        # Add current user message
        messages.append(ChatMessage(role="user", content=chat_request.message))
        
        # Get relevant documents if retrieval is enabled
        sources = []
        if chat_request.use_retrieval and profile.retrieval_enabled:
            sources = await self._retrieve_relevant_documents(
                chat_request.message,
                user,
                profile
            )
            
            # Add retrieved documents to context
            if sources:
                context_content = self._format_retrieval_context(sources)
                messages.insert(-1, ChatMessage(
                    role="system",
                    content=f"Relevant information from documents:\n{context_content}"
                ))
        
        # Stream AI response
        full_response = ""
        ai_message_id = None
        token_count = 0
        
        async for chunk in self.llm_service.stream_response(
            messages=messages,
            system_prompt=profile.system_prompt,
            temperature=chat_request.temperature or profile.temperature,
            max_tokens=chat_request.max_tokens or profile.max_tokens
        ):
            full_response += chunk
            token_count += 1  # Rough token count
            
            yield StreamingChatResponse(
                delta=chunk,
                conversation_id=conversation.id,
                message_id=ai_message_id,
                finished=False,
                metadata=chat_request.metadata
            )
        
        # Save complete AI message
        ai_message = await self._save_message(
            conversation_id=conversation.id,
            content=full_response,
            role="assistant",
            token_count=token_count,
            model_used=profile.model_name
        )
        
        # Update conversation and profile statistics
        await self._update_conversation_stats(conversation, token_count)
        await self._update_profile_usage(profile, token_count)
        
        # Generate embeddings (background task)
        asyncio.create_task(self._generate_message_embeddings(user_message, ai_message))
        
        # Send final chunk with completion info
        yield StreamingChatResponse(
            delta="",
            conversation_id=conversation.id,
            message_id=ai_message.id,
            finished=True,
            metadata={
                "token_count": token_count,
                "sources": [{
                    "document_id": source.document.id,
                    "filename": source.document.filename,
                    "similarity_score": source.similarity_score
                } for source in sources]
            }
        )
    
    async def _get_user_profile(self, user: User, profile_id: Optional[int] = None) -> Profile:
        """Get user profile for LLM settings."""
        if profile_id:
            result = await self.db.execute(
                select(Profile).where(
                    Profile.id == profile_id,
                    Profile.user_id == user.id,
                    Profile.is_active == True
                )
            )
            profile = result.scalar_one_or_none()
            if not profile:
                raise NotFoundError(f"Profile {profile_id} not found")
        else:
            # Get default profile
            result = await self.db.execute(
                select(Profile).where(
                    Profile.user_id == user.id,
                    Profile.is_default == True,
                    Profile.is_active == True
                )
            )
            profile = result.scalar_one_or_none()
            if not profile:
                raise NotFoundError("No default profile found for user")
        
        return profile
    
    async def _save_message(
        self,
        conversation_id: int,
        content: str,
        role: str,
        token_count: int = 0,
        processing_time: Optional[float] = None,
        model_used: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Save a message to the database."""
        message = Message(
            conversation_id=conversation_id,
            content=content,
            role=role,
            token_count=token_count,
            processing_time=processing_time,
            model_used=model_used,
            metadata=str(metadata) if metadata else None
        )
        
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        
        return message
    
    async def _build_conversation_context(
        self,
        conversation: Conversation,
        profile: Profile,
        additional_context: Optional[List[ChatMessage]] = None
    ) -> List[ChatMessage]:
        """Build conversation context for LLM."""
        messages = []
        
        # Add additional context if provided
        if additional_context:
            messages.extend(additional_context)
        
        # Get recent messages from conversation
        result = await self.db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.is_deleted == False
            )
            .order_by(Message.created_at.desc())
            .limit(20)  # Limit context to recent messages
        )
        recent_messages = result.scalars().all()
        
        # Convert to ChatMessage format (in chronological order)
        for message in reversed(recent_messages):
            messages.append(ChatMessage(
                role=message.role,
                content=message.content,
                metadata={"message_id": message.id}
            ))
        
        return messages
    
    async def _retrieve_relevant_documents(
        self,
        query: str,
        user: User,
        profile: Profile
    ) -> List[Any]:
        """Retrieve relevant documents for the query."""
        try:
            # Generate query embedding
            query_embedding = await self.llm_service.generate_embedding(query)
            
            # Search documents
            sources = await self.vector_service.search_documents(
                query_embedding=query_embedding,
                user_id=user.id,
                limit=profile.retrieval_top_k,
                similarity_threshold=profile.retrieval_score_threshold
            )
            
            return sources
            
        except Exception as e:
            logger.warning("Document retrieval failed", error=str(e))
            return []
    
    def _format_retrieval_context(self, sources: List[Any]) -> str:
        """Format retrieved documents for LLM context."""
        context_parts = []
        for i, source in enumerate(sources, 1):
            context_parts.append(
                f"Document {i}: {source.document.filename}\n"
                f"Content: {source.document.content[:500]}...\n"
                f"Relevance: {source.similarity_score:.2f}\n"
            )
        
        return "\n".join(context_parts)
    
    async def _update_conversation_stats(self, conversation: Conversation, token_count: int) -> None:
        """Update conversation statistics."""
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation.id)
            .values(
                message_count=Conversation.message_count + 1,
                total_tokens=Conversation.total_tokens + token_count,
                last_message_at=func.now(),
                updated_at=func.now()
            )
        )
        await self.db.commit()
    
    async def _update_profile_usage(self, profile: Profile, token_count: int) -> None:
        """Update profile usage statistics."""
        await self.db.execute(
            update(Profile)
            .where(Profile.id == profile.id)
            .values(
                usage_count=Profile.usage_count + 1,
                total_tokens_used=Profile.total_tokens_used + token_count,
                last_used=func.now(),
                updated_at=func.now()
            )
        )
        await self.db.commit()
    
    async def _generate_message_embeddings(self, *messages: Message) -> None:
        """Generate embeddings for messages (background task)."""
        try:
            for message in messages:
                if message.role in ("user", "assistant"):
                    embedding = await self.llm_service.generate_embedding(message.content)
                    await self.vector_service.store_message_embedding(message.id, embedding)
        except Exception as e:
            logger.warning("Failed to generate message embeddings", error=str(e))