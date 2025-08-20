"""Authentication service for user management."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import structlog

from chat.models import User, UserCreate, UserResponse, UserLogin, Token
from chat.core import hash_password, verify_password, generate_user_token, get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for authentication and user management."""
    
    async def create_user(self, user_data: UserCreate, db_session: AsyncSession) -> UserResponse:
        """Create a new user.
        
        Args:
            user_data: User creation data
            db_session: Database session
            
        Returns:
            Created user response
            
        Raises:
            HTTPException: If user already exists
        """
        logger.info("Creating new user", username=user_data.username, email=user_data.email)
        
        # Check if user already exists
        existing_user = await self._get_user_by_username_or_email(
            user_data.username, user_data.email, db_session
        )
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
        )
        
        db_session.add(db_user)
        await db_session.commit()
        await db_session.refresh(db_user)
        
        logger.info("User created successfully", user_id=str(db_user.id))
        
        return UserResponse.from_orm(db_user)
    
    async def authenticate_user(self, login_data: UserLogin, db_session: AsyncSession) -> Optional[User]:
        """Authenticate user credentials.
        
        Args:
            login_data: Login credentials
            db_session: Database session
            
        Returns:
            User if authentication successful, None otherwise
        """
        logger.info("Authenticating user", username=login_data.username)
        
        # Get user by username or email
        user = await self._get_user_by_username_or_email(
            login_data.username, login_data.username, db_session
        )
        
        if not user:
            logger.warning("User not found", username=login_data.username)
            return None
        
        if not user.is_active:
            logger.warning("User account is inactive", user_id=str(user.id))
            return None
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            logger.warning("Invalid password", user_id=str(user.id))
            return None
        
        logger.info("User authenticated successfully", user_id=str(user.id))
        return user
    
    async def login(self, login_data: UserLogin, db_session: AsyncSession) -> Token:
        """Login user and generate access token.
        
        Args:
            login_data: Login credentials
            db_session: Database session
            
        Returns:
            Access token
            
        Raises:
            HTTPException: If authentication fails
        """
        user = await self.authenticate_user(login_data, db_session)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate access token
        access_token = generate_user_token(str(user.id), user.username)
        
        logger.info("User logged in successfully", user_id=str(user.id))
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes in seconds
        )
    
    async def get_user_by_id(self, user_id: str, db_session: AsyncSession) -> Optional[User]:
        """Get user by ID.
        
        Args:
            user_id: User ID
            db_session: Database session
            
        Returns:
            User if found, None otherwise
        """
        try:
            result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by ID", user_id=user_id, error=str(e))
            return None
    
    async def get_user_by_username(self, username: str, db_session: AsyncSession) -> Optional[User]:
        """Get user by username.
        
        Args:
            username: Username
            db_session: Database session
            
        Returns:
            User if found, None otherwise
        """
        try:
            result = await db_session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by username", username=username, error=str(e))
            return None
    
    async def _get_user_by_username_or_email(
        self, username: str, email: str, db_session: AsyncSession
    ) -> Optional[User]:
        """Get user by username or email.
        
        Args:
            username: Username
            email: Email
            db_session: Database session
            
        Returns:
            User if found, None otherwise
        """
        try:
            result = await db_session.execute(
                select(User).where(
                    (User.username == username) | (User.email == email)
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                "Failed to get user by username or email",
                username=username,
                email=email,
                error=str(e)
            )
            return None
    
    async def update_user(
        self, user_id: str, update_data: dict, db_session: AsyncSession
    ) -> Optional[UserResponse]:
        """Update user information.
        
        Args:
            user_id: User ID
            update_data: Data to update
            db_session: Database session
            
        Returns:
            Updated user response
        """
        user = await self.get_user_by_id(user_id, db_session)
        if not user:
            return None
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(user, field) and value is not None:
                if field == "password":
                    setattr(user, "hashed_password", hash_password(value))
                else:
                    setattr(user, field, value)
        
        await db_session.commit()
        await db_session.refresh(user)
        
        logger.info("User updated successfully", user_id=user_id)
        
        return UserResponse.model_validate(user)
    
    async def deactivate_user(self, user_id: str, db_session: AsyncSession) -> bool:
        """Deactivate user account.
        
        Args:
            user_id: User ID
            db_session: Database session
            
        Returns:
            True if successful, False otherwise
        """
        user = await self.get_user_by_id(user_id, db_session)
        if not user:
            return False
        
        user.is_active = False
        await db_session.commit()
        
        logger.info("User deactivated", user_id=user_id)
        return True


# Global auth service instance
auth_service = AuthService()