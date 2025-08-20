"""LLM service using LangChain for conversation management."""

from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import AsyncCallbackHandler
import asyncio
import structlog

from chat.config import settings
from chat.models import MessageRole, MessageResponse
from chat.core import get_logger

logger = get_logger(__name__)


class StreamingCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming LLM responses."""
    
    def __init__(self):
        self.tokens = []
        self.done = False
    
    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Handle new token from LLM."""
        self.tokens.append(token)
    
    async def on_llm_end(self, response, **kwargs: Any) -> None:
        """Handle LLM completion."""
        self.done = True


class LLMService:
    """Service for LLM operations using LangChain."""
    
    def __init__(self):
        """Initialize LLM service."""
        self.chat_model = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens,
            openai_api_key=settings.openai_api_key,
        )
        
        self.streaming_model = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens,
            openai_api_key=settings.openai_api_key,
            streaming=True,
        )
        
        logger.info("LLM service initialized", model=settings.openai_model)
    
    def _create_memory(self, conversation_history: List[MessageResponse]) -> ConversationBufferWindowMemory:
        """Create conversation memory from history.
        
        Args:
            conversation_history: List of previous messages
            
        Returns:
            Configured memory instance
        """
        memory = ConversationBufferWindowMemory(
            k=settings.conversation_memory_size,
            return_messages=True
        )
        
        # Add conversation history to memory
        for message in conversation_history:
            if message.role == MessageRole.USER:
                memory.chat_memory.add_user_message(message.content)
            elif message.role == MessageRole.ASSISTANT:
                memory.chat_memory.add_ai_message(message.content)
        
        return memory
    
    def _messages_to_langchain(
        self,
        messages: List[MessageResponse],
        system_prompt: Optional[str] = None
    ) -> List[BaseMessage]:
        """Convert message history to LangChain format.
        
        Args:
            messages: List of messages
            system_prompt: Optional system prompt
            
        Returns:
            List of LangChain messages
        """
        langchain_messages = []
        
        # Add system prompt if provided
        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))
        elif not any(msg.role == MessageRole.SYSTEM for msg in messages):
            # Add default system prompt if none exists
            langchain_messages.append(SystemMessage(content=settings.default_system_prompt))
        
        # Convert messages
        for message in messages:
            if message.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=message.content))
            elif message.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=message.content))
        
        return langchain_messages
    
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
        
        # Create model with custom parameters if provided
        model = self.chat_model
        if temperature is not None or max_tokens is not None:
            model = ChatOpenAI(
                model=settings.openai_model,
                temperature=temperature or settings.openai_temperature,
                max_tokens=max_tokens or settings.openai_max_tokens,
                openai_api_key=settings.openai_api_key,
            )
        
        # Prepare messages
        messages = self._messages_to_langchain(conversation_history, system_prompt)
        messages.append(HumanMessage(content=user_message))
        
        try:
            # Generate response
            response = await model.agenerate([messages])
            response_text = response.generations[0][0].text
            
            logger.info(
                "Response generated",
                response_length=len(response_text),
                token_usage=response.llm_output.get("token_usage") if response.llm_output else None
            )
            
            return response_text
            
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
        
        # Create streaming callback handler
        callback_handler = StreamingCallbackHandler()
        
        # Create model with custom parameters if provided
        model = ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature or settings.openai_temperature,
            max_tokens=max_tokens or settings.openai_max_tokens,
            openai_api_key=settings.openai_api_key,
            streaming=True,
            callbacks=[callback_handler],
        )
        
        # Prepare messages
        messages = self._messages_to_langchain(conversation_history, system_prompt)
        messages.append(HumanMessage(content=user_message))
        
        try:
            # Start generation in background
            task = asyncio.create_task(model.agenerate([messages]))
            
            # Stream tokens as they arrive
            while not callback_handler.done:
                if callback_handler.tokens:
                    token = callback_handler.tokens.pop(0)
                    yield token
                else:
                    await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
            
            # Yield any remaining tokens
            while callback_handler.tokens:
                yield callback_handler.tokens.pop(0)
            
            # Wait for completion
            await task
            
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
            messages = [HumanMessage(content=title_prompt)]
            response = await self.chat_model.agenerate([messages])
            title = response.generations[0][0].text.strip()
            
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