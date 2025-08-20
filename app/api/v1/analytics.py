"""Analytics endpoints."""

from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import AnalyticsSummary, UsageMetrics, PerformanceMetrics
from app.dependencies import get_current_active_user, get_analytics_service, get_current_superuser
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics")


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days_back: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get analytics summary for the user."""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        summary = await analytics_service.get_analytics_summary(
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id
        )
        
        return summary
        
    except Exception as e:
        logger.error("Analytics summary retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics summary"
        )


@router.get("/usage", response_model=List[UsageMetrics])
async def get_usage_metrics(
    period: str = Query("day", regex="^(hour|day|week|month)$"),
    days_back: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get usage metrics over time."""
    try:
        metrics = await analytics_service.get_usage_metrics(
            period=period,
            days_back=days_back,
            user_id=current_user.id
        )
        
        return metrics
        
    except Exception as e:
        logger.error("Usage metrics retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage metrics"
        )


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    days_back: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get performance metrics."""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        metrics = await analytics_service.get_performance_metrics(
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id
        )
        
        return metrics
        
    except Exception as e:
        logger.error("Performance metrics retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


# Admin-only endpoints
@router.get("/admin/summary", response_model=AnalyticsSummary)
async def get_admin_analytics_summary(
    days_back: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_superuser),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get system-wide analytics summary (admin only)."""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        summary = await analytics_service.get_analytics_summary(
            start_date=start_date,
            end_date=end_date,
            user_id=None  # System-wide
        )
        
        return summary
        
    except Exception as e:
        logger.error("Admin analytics summary retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system analytics summary"
        )