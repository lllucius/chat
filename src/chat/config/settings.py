"""Configuration management module."""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Enable auto-reload")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # OpenAI Configuration
    openai_api_key: str = Field(description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", 
        description="OpenAI embedding model"
    )
    openai_temperature: float = Field(default=0.7, description="OpenAI temperature")
    openai_max_tokens: int = Field(default=4096, description="OpenAI max tokens")
    
    # Database Configuration
    database_url: str = Field(description="Database connection URL")
    database_echo: bool = Field(default=False, description="Enable SQLAlchemy echo")
    
    # Vector Store Configuration
    vector_store_type: str = Field(default="postgres", description="Vector store type")
    vector_dimension: int = Field(default=1536, description="Vector dimension")
    
    # Authentication Configuration
    secret_key: str = Field(description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, 
        description="Access token expiration in minutes"
    )
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format")
    
    # Document Processing
    max_file_size: int = Field(default=10485760, description="Max file size in bytes")
    allowed_file_types: List[str] = Field(
        default=[".pdf", ".txt", ".md", ".docx"], 
        description="Allowed file types"
    )
    chunk_size: int = Field(default=1000, description="Document chunk size")
    chunk_overlap: int = Field(default=200, description="Document chunk overlap")
    
    # LLM Configuration
    default_system_prompt: str = Field(
        default="You are a helpful AI assistant. Provide accurate and helpful responses to user questions.",
        description="Default system prompt"
    )
    conversation_memory_size: int = Field(
        default=10, 
        description="Number of messages to keep in memory"
    )
    enable_streaming: bool = Field(default=True, description="Enable streaming responses")
    
    # CLI Configuration
    cli_history_file: str = Field(default=".chat_history", description="CLI history file")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"


# Global settings instance
settings = Settings()