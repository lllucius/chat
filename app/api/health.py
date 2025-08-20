"""Health check endpoints."""

import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, check_db_connection
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService
from app.core.exceptions import VectorStoreError, LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/healthz")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/readyz")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive readiness check."""
    start_time = datetime.utcnow()
    health_status = {
        "status": "healthy",
        "timestamp": start_time.isoformat(),
        "checks": {}
    }
    
    # Check database connectivity
    try:
        db_healthy = await check_db_connection()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "message": "Database connection successful" if db_healthy else "Database connection failed"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database check failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # Check vector store
    try:
        vector_service = VectorService(db)
        vector_stats = await vector_service.get_vector_stats()
        health_status["checks"]["vector_store"] = {
            "status": "healthy",
            "message": "Vector store operational",
            "stats": vector_stats
        }
    except Exception as e:
        health_status["checks"]["vector_store"] = {
            "status": "unhealthy",
            "message": f"Vector store check failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # Check LLM service
    try:
        llm_service = LLMService()
        # Simple test to verify LLM is accessible
        test_result = await llm_service.generate_embedding("test")
        health_status["checks"]["llm_service"] = {
            "status": "healthy" if test_result else "unhealthy",
            "message": "LLM service operational" if test_result else "LLM service not responding"
        }
    except Exception as e:
        health_status["checks"]["llm_service"] = {
            "status": "unhealthy",
            "message": f"LLM service check failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # Calculate response time
    response_time = (datetime.utcnow() - start_time).total_seconds()
    health_status["response_time_seconds"] = response_time
    
    # Return appropriate status code
    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    
    return health_status


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Get basic system metrics."""
    try:
        # Database metrics
        vector_service = VectorService(db)
        vector_stats = await vector_service.get_vector_stats()
        
        # System metrics
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected",
                "vector_stats": vector_stats
            },
            "api": {
                "version": "1.0.0",
                "status": "operational"
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error("Metrics collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metrics collection failed: {str(e)}"
        )