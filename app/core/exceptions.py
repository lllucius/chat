"""Custom exceptions for the Chat API application."""

from typing import Any, Optional


class ChatAPIException(Exception):
    """Base exception for Chat API."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Any] = None
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class AuthenticationError(ChatAPIException):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(ChatAPIException):
    """Exception raised for authorization failures."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=403, details=details)


class ValidationError(ChatAPIException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=422, details=details)


class NotFoundError(ChatAPIException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=404, details=details)


class ConflictError(ChatAPIException):
    """Exception raised for resource conflicts."""
    
    def __init__(self, message: str = "Resource conflict", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=409, details=details)


class RateLimitError(ChatAPIException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=429, details=details)


class ServiceUnavailableError(ChatAPIException):
    """Exception raised when a service is unavailable."""
    
    def __init__(self, message: str = "Service unavailable", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=503, details=details)


class LLMError(ChatAPIException):
    """Exception raised for LLM-related errors."""
    
    def __init__(self, message: str = "LLM processing error", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=502, details=details)


class VectorStoreError(ChatAPIException):
    """Exception raised for vector store errors."""
    
    def __init__(self, message: str = "Vector store error", details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=502, details=details)