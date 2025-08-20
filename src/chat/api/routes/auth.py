"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chat.core import get_db_session
from chat.models import UserCreate, UserResponse, UserLogin, Token, User
from chat.services import auth_service
from chat.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db_session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Register a new user.
    
    Args:
        user_data: User registration data
        db_session: Database session
        
    Returns:
        Created user response
        
    Raises:
        HTTPException: If registration fails
    """
    return await auth_service.create_user(user_data, db_session)


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db_session: AsyncSession = Depends(get_db_session),
) -> Token:
    """Login user and get access token.
    
    Args:
        login_data: Login credentials
        db_session: Database session
        
    Returns:
        Access token
        
    Raises:
        HTTPException: If login fails
    """
    return await auth_service.login(login_data, db_session)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    return UserResponse.from_orm(current_user)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user),
) -> Token:
    """Refresh access token.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        New access token
    """
    from chat.core.security import generate_user_token
    
    access_token = generate_user_token(str(current_user.id), current_user.username)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60  # 30 minutes in seconds
    )