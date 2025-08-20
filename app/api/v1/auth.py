"""Authentication endpoints."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth_service import AuthService
from app.schemas.user import User, UserCreate, UserLogin, Token
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.core.exceptions import AuthenticationError, ConflictError
from app.dependencies import get_current_user, get_current_active_user
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    try:
        auth_service = AuthService(db)
        user = await auth_service.create_user(user_data)
        
        logger.info("User registered", user_id=user.id, username=user.username)
        return user
        
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access token."""
    try:
        auth_service = AuthService(db)
        user = await auth_service.authenticate_user(form_data.username, form_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create tokens
        access_token = create_access_token(
            subject=user.username,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )
        refresh_token = create_refresh_token(
            subject=user.username,
            expires_delta=timedelta(days=settings.refresh_token_expire_days)
        )
        
        logger.info("User logged in", user_id=user.id, username=user.username)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        username = verify_token(refresh_token, token_type="refresh")
        
        # Get user
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_username(username)
        
        if not user or not user.is_active:
            raise AuthenticationError("Invalid user")
        
        # Create new access token
        access_token = create_access_token(
            subject=user.username,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )
        
        logger.info("Token refreshed", user_id=user.id, username=user.username)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,  # Keep the same refresh token
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout user (client should discard tokens)."""
    logger.info("User logged out", user_id=current_user.id, username=current_user.username)
    
    return {"message": "Successfully logged out"}