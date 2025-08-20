"""LLM service for managing language model interactions."""

import asyncio
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler

from app.config import settings
from app.schemas.chat import ChatMessage
from app.core.exceptions import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming responses."""
    
    def __init__(self) -> None:
        self.tokens: List[str] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Called when LLM starts running."""
        self.start_time = time.time()
        self.tokens = []
    
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called when a new token is generated."""
        self.tokens.append(token)
    
    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM ends running."""
        self.end_time = time.time()
    
    def get_processing_time(self) -> float:
        """Get the total processing time."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


class LLMService:
    """Service for managing LLM interactions."""
    
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            openai_api_key=settings.openai_api_key,
            model_name=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            streaming=True
        )
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            model=settings.embedding_model
        )
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of chat messages
            system_prompt: Optional system prompt
            temperature: Override temperature
            max_tokens: Override max tokens
            stream: Enable streaming
            **kwargs: Additional LLM parameters
            
        Returns:
            Response containing message, metadata, and metrics
        """
        try:
            # Configure LLM for this request
            llm_kwargs = {}
            if temperature is not None:
                llm_kwargs["temperature"] = temperature
            if max_tokens is not None:
                llm_kwargs["max_tokens"] = max_tokens
            
            # Update LLM parameters if provided
            if llm_kwargs:
                self.llm = ChatOpenAI(
                    openai_api_key=settings.openai_api_key,
                    model_name=settings.llm_model,
                    streaming=stream,
                    **llm_kwargs
                )
            
            # Convert messages to LangChain format
            langchain_messages = self._convert_messages(messages, system_prompt)
            
            # Set up callback handler for metrics
            callback_handler = StreamingCallbackHandler()
            
            start_time = time.time()
            
            if stream:
                # Handle streaming response
                response_content = ""
                async for chunk in self._stream_response(langchain_messages, callback_handler):
                    response_content += chunk
                
                processing_time = callback_handler.get_processing_time()
                token_count = len(callback_handler.tokens)
            else:
                # Handle non-streaming response
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self.llm.invoke(langchain_messages, callbacks=[callback_handler])
                )
                response_content = response.content
                processing_time = time.time() - start_time
                token_count = len(response_content.split())  # Rough token count
            
            logger.info(
                "LLM response generated",
                model=settings.llm_model,
                token_count=token_count,
                processing_time=processing_time,
                stream=stream
            )
            
            return {
                "content": response_content,
                "model_used": settings.llm_model,
                "token_count": token_count,
                "processing_time": processing_time,
                "metadata": {
                    "temperature": temperature or settings.llm_temperature,
                    "max_tokens": max_tokens or settings.llm_max_tokens,
                    "stream": stream
                }
            }
            
        except Exception as e:
            logger.error("LLM generation failed", error=str(e))
            raise LLMError(f"Failed to generate response: {str(e)}")
    
    async def stream_response(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from the LLM.
        
        Args:
            messages: List of chat messages
            system_prompt: Optional system prompt
            temperature: Override temperature
            max_tokens: Override max tokens
            **kwargs: Additional LLM parameters
            
        Yields:
            Response chunks
        """
        try:
            # Configure LLM for streaming
            llm_kwargs = {"streaming": True}
            if temperature is not None:
                llm_kwargs["temperature"] = temperature
            if max_tokens is not None:
                llm_kwargs["max_tokens"] = max_tokens
            
            streaming_llm = ChatOpenAI(
                openai_api_key=settings.openai_api_key,
                model_name=settings.llm_model,
                **llm_kwargs
            )
            
            # Convert messages to LangChain format
            langchain_messages = self._convert_messages(messages, system_prompt)
            
            # Stream the response
            async for chunk in streaming_llm.astream(langchain_messages):
                if chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error("LLM streaming failed", error=str(e))
            raise LLMError(f"Failed to stream response: {str(e)}")
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.embeddings.embed_documents(texts)
            )
            
            logger.info("Embeddings generated", text_count=len(texts))
            return embeddings
            
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise LLMError(f"Failed to generate embeddings: {str(e)}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.embeddings.embed_query(text)
            )
            
            return embedding
            
        except Exception as e:
            logger.error("Single embedding generation failed", error=str(e))
            raise LLMError(f"Failed to generate embedding: {str(e)}")
    
    def _convert_messages(
        self, 
        messages: List[ChatMessage], 
        system_prompt: Optional[str] = None
    ) -> List[Any]:
        """Convert ChatMessage objects to LangChain message format."""
        langchain_messages = []
        
        # Add system prompt if provided
        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))
        
        # Convert chat messages
        for message in messages:
            if message.role == "user":
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                langchain_messages.append(AIMessage(content=message.content))
            elif message.role == "system":
                langchain_messages.append(SystemMessage(content=message.content))
        
        return langchain_messages
    
    async def _stream_response(
        self, 
        messages: List[Any], 
        callback_handler: StreamingCallbackHandler
    ) -> AsyncGenerator[str, None]:
        """Internal method to handle streaming response."""
        try:
            async for chunk in self.llm.astream(messages, callbacks=[callback_handler]):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error("Internal streaming failed", error=str(e))
            raise