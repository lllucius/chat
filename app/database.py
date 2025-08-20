"""Database configuration and connection management."""

import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.config import settings

# Create the SQLAlchemy engine
engine = create_async_engine(
    str(settings.database_url),
    echo=settings.database_echo,
    poolclass=NullPool,  # Use NullPool for development
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database and install required extensions."""
    async with engine.begin() as conn:
        # Install pgvector extension
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("✓ pgvector extension installed")
        except Exception as e:
            print(f"Warning: Could not install pgvector extension: {e}")
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Database tables created")


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    print("✓ Database connections closed")


async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False