"""Dependency injection for FastAPI endpoints."""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import verify_token
from app.core.exceptions import AuthenticationError, NotFoundError
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.analytics_service import AnalyticsService

# Security scheme for JWT tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user.
    
    Args:
        credentials: JWT token credentials
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        username = verify_token(credentials.credentials, token_type="access")
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_username(username)
        if not user:
            raise NotFoundError(f"User {username} not found")
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        return user
    except (AuthenticationError, NotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current superuser.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Superuser
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get authentication service instance."""
    return AuthService(db)


def get_llm_service() -> LLMService:
    """Get LLM service instance."""
    return LLMService()


def get_vector_service(db: AsyncSession = Depends(get_db)) -> VectorService:
    """Get vector store service instance."""
    return VectorService(db)


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
    vector_service: VectorService = Depends(get_vector_service)
) -> ChatService:
    """Get chat service instance."""
    return ChatService(db, llm_service, vector_service)


def get_document_service(
    db: AsyncSession = Depends(get_db),
    vector_service: VectorService = Depends(get_vector_service)
) -> DocumentService:
    """Get document service instance."""
    return DocumentService(db, vector_service)


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    """Get analytics service instance."""
    return AnalyticsService(db)


# Optional dependency for authentication (allows anonymous access)
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    
    Args:
        credentials: Optional JWT token credentials
        db: Database session
        
    Returns:
        Current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        username = verify_token(credentials.credentials, token_type="access")
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_username(username)
        if user and user.is_active:
            return user
    except (AuthenticationError, NotFoundError):
        pass
    
    return None