"""Logging configuration and utilities."""

import sys
import structlog
from typing import Any, Dict
from chat.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib, settings.log_level.upper(), structlog.INFO)
        ),
        logger_factory=structlog.WriteLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name, typically __name__
        
    Returns:
        Configured structlog bound logger
    """
    return structlog.get_logger(name)


def log_request(
    logger: structlog.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    **kwargs: Any
) -> None:
    """Log HTTP request details.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        **kwargs: Additional context to log
    """
    logger.info(
        "HTTP request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        **kwargs
    )


def log_error(
    logger: structlog.BoundLogger,
    error: Exception,
    context: Dict[str, Any] = None,
) -> None:
    """Log error with context.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context dictionary
    """
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        **(context or {})
    )