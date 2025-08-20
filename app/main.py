"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import structlog

from app.config import settings
from app.database import init_db, close_db
from app.core.logging import setup_logging
from app.core.exceptions import ChatAPIException
from app.api.v1 import auth, chat, conversations, messages, documents, profiles, prompts, analytics
from app.api import health


# Set up logging
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Chat API application")
    
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Chat API application")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ChatAPIException)
async def chat_api_exception_handler(request: Request, exc: ChatAPIException):
    """Handle custom Chat API exceptions."""
    logger.error(
        "API Exception",
        status_code=exc.status_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "details": exc.details,
                "status_code": exc.status_code
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled Exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "details": str(exc) if settings.debug else None,
                "status_code": 500
            }
        }
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP requests and responses."""
    start_time = structlog.get_logger().info(
        "Request started",
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent"),
    )
    
    response = await call_next(request)
    
    structlog.get_logger().info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration_ms=int((structlog.get_logger()._context.get("time", 0)) * 1000)
    )
    
    return response


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix=settings.api_v1_prefix, tags=["Authentication"])
app.include_router(chat.router, prefix=settings.api_v1_prefix, tags=["Chat"])
app.include_router(conversations.router, prefix=settings.api_v1_prefix, tags=["Conversations"])
app.include_router(messages.router, prefix=settings.api_v1_prefix, tags=["Messages"])
app.include_router(documents.router, prefix=settings.api_v1_prefix, tags=["Documents"])
app.include_router(profiles.router, prefix=settings.api_v1_prefix, tags=["Profiles"])
app.include_router(prompts.router, prefix=settings.api_v1_prefix, tags=["Prompts"])
app.include_router(analytics.router, prefix=settings.api_v1_prefix, tags=["Analytics"])


def custom_openapi():
    """Custom OpenAPI schema generation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["contact"] = {
        "name": "Chat API Team",
        "email": "support@chat-api.com",
    }
    
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Add tags metadata
    openapi_schema["tags"] = [
        {
            "name": "Health",
            "description": "Health check and system status endpoints"
        },
        {
            "name": "Authentication",
            "description": "User authentication and authorization"
        },
        {
            "name": "Chat",
            "description": "Chat and messaging functionality"
        },
        {
            "name": "Conversations",
            "description": "Conversation management"
        },
        {
            "name": "Messages",
            "description": "Message operations and search"
        },
        {
            "name": "Documents",
            "description": "Document upload and knowledge base management"
        },
        {
            "name": "Profiles",
            "description": "LLM profile and settings management"
        },
        {
            "name": "Prompts",
            "description": "Prompt template management"
        },
        {
            "name": "Analytics",
            "description": "Usage analytics and metrics"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Chat API",
        "version": settings.api_version,
        "docs_url": "/docs" if settings.debug else None,
        "health_check": "/healthz"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )