"""Configuration management for the Chat API application."""

import os
from typing import List, Optional
from pydantic import Field, PostgresDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    api_title: str = Field(default="Chat API", env="API_TITLE")
    api_description: str = Field(
        default="Advanced AI Chatbot Backend API Platform", 
        env="API_DESCRIPTION"
    )
    api_version: str = Field(default="1.0.0", env="API_VERSION")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], 
        env="CORS_ORIGINS"
    )
    
    # Database Configuration
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://chat_user:chat_password@localhost:5432/chat_db",
        env="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis Configuration
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # LLM Configuration
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-4", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, env="LLM_MAX_TOKENS")
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    
    # Vector Store Configuration
    vector_store_type: str = Field(default="pgvector", env="VECTOR_STORE_TYPE")
    vector_dimension: int = Field(default=1536, env="VECTOR_DIMENSION")
    
    # Authentication
    secret_key: str = Field(env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # File Upload Configuration
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    allowed_file_types: List[str] = Field(
        default=["pdf", "txt", "docx", "md"], 
        env="ALLOWED_FILE_TYPES"
    )
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    # Background Tasks
    enable_background_tasks: bool = Field(default=True, env="ENABLE_BACKGROUND_TASKS")
    background_task_queue_size: int = Field(default=100, env="BACKGROUND_TASK_QUEUE_SIZE")
    
    # Monitoring and Health Checks
    health_check_timeout: int = Field(default=30, env="HEALTH_CHECK_TIMEOUT")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")

    @validator("cors_origins", pre=True)
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("CORS origins must be a string or list")

    @validator("allowed_file_types", pre=True)
    def assemble_allowed_file_types(cls, v):
        """Parse allowed file types from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("Allowed file types must be a string or list")

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()