"""LLM service using OpenAI for conversation management."""

from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
import json
import structlog
import openai

from chat.config import settings
from chat.models import MessageRole, MessageResponse
from chat.core import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for LLM operations using OpenAI."""
    
    def __init__(self):
        """Initialize LLM service."""
        # Initialize OpenAI client
        openai.api_key = settings.openai_api_key
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        
        logger.info("LLM service initialized", model=settings.openai_model)
    
    def _messages_to_openai(
        self,
        messages: List[MessageResponse],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Convert message history to OpenAI format.
        
        Args:
            messages: List of messages
            system_prompt: Optional system prompt
            
        Returns:
            List of OpenAI messages
        """
        openai_messages = []
        
        # Add system prompt if provided
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        elif not any(msg.role == MessageRole.SYSTEM for msg in messages):
            # Add default system prompt if none exists
            openai_messages.append({"role": "system", "content": settings.default_system_prompt})
        
        # Convert messages
        for message in messages:
            if message.role == MessageRole.USER:
                openai_messages.append({"role": "user", "content": message.content})
            elif message.role == MessageRole.ASSISTANT:
                openai_messages.append({"role": "assistant", "content": message.content})
            elif message.role == MessageRole.SYSTEM:
                openai_messages.append({"role": "system", "content": message.content})
        
        return openai_messages
    
    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[MessageResponse],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate response to user message.
        
        Args:
            user_message: User's message
            conversation_history: Previous conversation messages
            system_prompt: Optional custom system prompt
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Returns:
            Generated response text
        """
        logger.info("Generating response", user_message_length=len(user_message))
        
        # Prepare messages
        messages = self._messages_to_openai(conversation_history, system_prompt)
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Generate response
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=temperature or settings.openai_temperature,
                max_tokens=max_tokens or settings.openai_max_tokens,
            )
            
            response_text = response.choices[0].message.content
            
            logger.info(
                "Response generated",
                response_length=len(response_text) if response_text else 0,
                token_usage=response.usage.model_dump() if response.usage else None
            )
            
            return response_text or ""
            
        except Exception as e:
            logger.error("Failed to generate response", error=str(e))
            raise
    
    async def stream_response(
        self,
        user_message: str,
        conversation_history: List[MessageResponse],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response to user message.
        
        Args:
            user_message: User's message
            conversation_history: Previous conversation messages
            system_prompt: Optional custom system prompt
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Yields:
            Response tokens as they are generated
        """
        logger.info("Streaming response", user_message_length=len(user_message))
        
        # Prepare messages
        messages = self._messages_to_openai(conversation_history, system_prompt)
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Stream response
            stream = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=temperature or settings.openai_temperature,
                max_tokens=max_tokens or settings.openai_max_tokens,
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info("Response streaming completed")
            
        except Exception as e:
            logger.error("Failed to stream response", error=str(e))
            raise
    
    async def generate_title(self, conversation_messages: List[MessageResponse]) -> str:
        """Generate a title for the conversation.
        
        Args:
            conversation_messages: Messages in the conversation
            
        Returns:
            Generated title
        """
        if not conversation_messages:
            return "New Conversation"
        
        # Use first user message or a summary of the conversation
        first_user_message = next(
            (msg.content for msg in conversation_messages if msg.role == MessageRole.USER),
            "New Conversation"
        )
        
        # Create a prompt to generate a title
        title_prompt = f"""Generate a short, descriptive title (max 5 words) for a conversation that starts with:
        "{first_user_message[:100]}..."
        
        Title:"""
        
        try:
            messages = [{"role": "user", "content": title_prompt}]
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=0.3,
                max_tokens=20,
            )
            
            title = response.choices[0].message.content or ""
            
            # Clean up the title
            title = title.replace('"', '').replace("'", '').strip()
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title or "New Conversation"
            
        except Exception as e:
            logger.warning("Failed to generate title", error=str(e))
            return "New Conversation"


# Global LLM service instance
llm_service = LLMService()