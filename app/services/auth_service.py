"""Authentication service for user management and authentication."""

from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.profile import Profile
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for user authentication and management."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user
            
        Raises:
            ConflictError: If username or email already exists
        """
        # Check if username already exists
        existing_user = await self.get_user_by_username(user_data.username)
        if existing_user:
            raise ConflictError(f"Username '{user_data.username}' already exists")
        
        # Check if email already exists
        existing_email = await self.get_user_by_email(user_data.email)
        if existing_email:
            raise ConflictError(f"Email '{user_data.email}' already exists")
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=user_data.is_active
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # Create default profile
        await self._create_default_profile(user)
        
        logger.info("User created", user_id=user.id, username=user.username)
        return user
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            Authenticated user or None if authentication fails
        """
        user = await self.get_user_by_username(username)
        if not user:
            user = await self.get_user_by_email(username)
        
        if not user or not verify_password(password, user.hashed_password):
            logger.warning("Authentication failed", username=username)
            return None
        
        if not user.is_active:
            logger.warning("Inactive user login attempt", username=username)
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        logger.info("User authenticated", user_id=user.id, username=user.username)
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email address
            
        Returns:
            User or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """
        Update user information.
        
        Args:
            user_id: User ID
            user_data: Updated user data
            
        Returns:
            Updated user
            
        Raises:
            NotFoundError: If user not found
            ConflictError: If username or email conflict
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        # Check for conflicts if username or email is being updated
        if user_data.username and user_data.username != user.username:
            existing = await self.get_user_by_username(user_data.username)
            if existing and existing.id != user_id:
                raise ConflictError(f"Username '{user_data.username}' already exists")
        
        if user_data.email and user_data.email != user.email:
            existing = await self.get_user_by_email(user_data.email)
            if existing and existing.id != user_id:
                raise ConflictError(f"Email '{user_data.email}' already exists")
        
        # Update fields
        for field, value in user_data.model_dump(exclude_unset=True).items():
            if field == "password":
                user.hashed_password = get_password_hash(value)
            else:
                setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info("User updated", user_id=user.id, username=user.username)
        return user
    
    async def _create_default_profile(self, user: User) -> Profile:
        """Create a default profile for a new user."""
        profile = Profile(
            user_id=user.id,
            name="Default",
            description="Default chat profile",
            is_default=True
        )
        
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile