"""Health check routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from chat.core import get_db_session
from chat.config import settings

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    timestamp: datetime
    version: str
    environment: str
    services: dict


@router.get("/", response_model=HealthResponse)
async def health_check(
    db_session: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    """Basic health check endpoint.
    
    Args:
        db_session: Database session
        
    Returns:
        Health status
    """
    # Check database connectivity
    database_status = "healthy"
    try:
        await db_session.execute("SELECT 1")
    except Exception:
        database_status = "unhealthy"
    
    # Check other services
    services = {
        "database": database_status,
        "llm_service": "healthy",  # Could add actual LLM health check
        "vector_store": "healthy",  # Could add actual vector store health check
    }
    
    overall_status = "healthy" if all(
        status == "healthy" for status in services.values()
    ) else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.environment,
        services=services,
    )


@router.get("/live")
async def liveness_probe() -> dict:
    """Kubernetes liveness probe endpoint.
    
    Returns:
        Simple OK response
    """
    return {"status": "ok"}


@router.get("/ready")
async def readiness_probe(
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Kubernetes readiness probe endpoint.
    
    Args:
        db_session: Database session
        
    Returns:
        Ready status
    """
    try:
        # Check if database is accessible
        await db_session.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        return {"status": "not ready"}