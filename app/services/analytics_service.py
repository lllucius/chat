"""Analytics service for tracking usage metrics and statistics."""

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text

from app.models.analytics import Analytics
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.document import Document
from app.schemas.analytics import (
    AnalyticsCreate, AnalyticsSummary, AnalyticsQuery, 
    UsageMetrics, PerformanceMetrics, EntityStats
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Service for tracking and analyzing usage metrics."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def track_event(
        self,
        event_data: AnalyticsCreate,
        user_id: Optional[int] = None
    ) -> Analytics:
        """
        Track an analytics event.
        
        Args:
            event_data: Event data to track
            user_id: Optional user ID
            
        Returns:
            Created analytics record
        """
        now = datetime.utcnow()
        
        analytics = Analytics(
            date=now.date(),
            hour=now.hour,
            entity_type=event_data.entity_type,
            entity_id=event_data.entity_id,
            user_id=user_id or event_data.user_id,
            event_type=event_data.event_type,
            event_count=event_data.event_count,
            processing_time=event_data.processing_time,
            token_count=event_data.token_count,
            tokens_per_second=event_data.tokens_per_second,
            estimated_cost=event_data.estimated_cost,
            metadata=str(event_data.metadata) if event_data.metadata else None,
            error_type=event_data.error_type,
            error_message=event_data.error_message
        )
        
        self.db.add(analytics)
        await self.db.commit()
        await self.db.refresh(analytics)
        
        logger.debug(
            "Analytics event tracked",
            entity_type=event_data.entity_type,
            event_type=event_data.event_type,
            user_id=user_id
        )
        
        return analytics
    
    async def get_analytics_summary(
        self,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None
    ) -> AnalyticsSummary:
        """
        Get analytics summary for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            user_id: Optional user ID filter
            
        Returns:
            Analytics summary
        """
        base_query = select(Analytics).where(
            and_(
                Analytics.date >= start_date,
                Analytics.date <= end_date
            )
        )
        
        if user_id:
            base_query = base_query.where(Analytics.user_id == user_id)
        
        # Total events
        total_events_result = await self.db.execute(
            select(func.sum(Analytics.event_count))
            .select_from(base_query.subquery())
        )
        total_events = total_events_result.scalar() or 0
        
        # Unique users
        unique_users_result = await self.db.execute(
            select(func.count(func.distinct(Analytics.user_id)))
            .select_from(base_query.subquery())
            .where(Analytics.user_id.is_not(None))
        )
        unique_users = unique_users_result.scalar() or 0
        
        # Conversation stats
        conversation_stats = await self._get_entity_stats(
            start_date, end_date, "conversation", user_id
        )
        total_conversations = conversation_stats.get("total_events", 0)
        
        # Message stats
        message_stats = await self._get_entity_stats(
            start_date, end_date, "message", user_id
        )
        total_messages = message_stats.get("total_events", 0)
        
        # Token stats
        token_result = await self.db.execute(
            select(func.sum(Analytics.token_count))
            .select_from(base_query.subquery())
            .where(Analytics.token_count.is_not(None))
        )
        total_tokens = token_result.scalar() or 0
        
        # Cost stats
        cost_result = await self.db.execute(
            select(func.sum(Analytics.estimated_cost))
            .select_from(base_query.subquery())
            .where(Analytics.estimated_cost.is_not(None))
        )
        total_cost = cost_result.scalar() or 0.0
        
        # Average processing time
        avg_time_result = await self.db.execute(
            select(func.avg(Analytics.processing_time))
            .select_from(base_query.subquery())
            .where(Analytics.processing_time.is_not(None))
        )
        average_processing_time = avg_time_result.scalar() or 0.0
        
        # Error count
        error_result = await self.db.execute(
            select(func.sum(Analytics.event_count))
            .select_from(base_query.subquery())
            .where(Analytics.error_type.is_not(None))
        )
        error_count = error_result.scalar() or 0
        
        # Top entities
        top_entities_result = await self.db.execute(
            select(
                Analytics.entity_type,
                Analytics.entity_id,
                func.sum(Analytics.event_count).label("total_events")
            )
            .select_from(base_query.subquery())
            .where(Analytics.entity_id.is_not(None))
            .group_by(Analytics.entity_type, Analytics.entity_id)
            .order_by(func.sum(Analytics.event_count).desc())
            .limit(10)
        )
        top_entities = [
            {
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "total_events": row.total_events
            }
            for row in top_entities_result.fetchall()
        ]
        
        return AnalyticsSummary(
            date=end_date,
            total_events=total_events,
            unique_users=unique_users,
            total_conversations=total_conversations,
            total_messages=total_messages,
            total_tokens=total_tokens,
            total_cost=total_cost,
            average_processing_time=average_processing_time,
            error_count=error_count,
            top_entities=top_entities
        )
    
    async def get_usage_metrics(
        self,
        period: str = "day",
        days_back: int = 7,
        user_id: Optional[int] = None
    ) -> List[UsageMetrics]:
        """
        Get usage metrics over time.
        
        Args:
            period: Time period ('hour', 'day', 'week', 'month')
            days_back: Number of days to look back
            user_id: Optional user ID filter
            
        Returns:
            List of usage metrics
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Build time grouping based on period
        if period == "hour":
            time_group = func.date_trunc('hour', Analytics.created_at)
        elif period == "day":
            time_group = func.date_trunc('day', Analytics.created_at)
        elif period == "week":
            time_group = func.date_trunc('week', Analytics.created_at)
        else:  # month
            time_group = func.date_trunc('month', Analytics.created_at)
        
        base_query = select(Analytics).where(
            Analytics.created_at >= start_date
        )
        
        if user_id:
            base_query = base_query.where(Analytics.user_id == user_id)
        
        # Query metrics
        metrics_query = select(
            time_group.label("timestamp"),
            func.count(func.distinct(Analytics.user_id)).label("active_users"),
            func.sum(
                func.case(
                    (Analytics.entity_type == "conversation", Analytics.event_count),
                    else_=0
                )
            ).label("total_conversations"),
            func.sum(
                func.case(
                    (Analytics.entity_type == "message", Analytics.event_count),
                    else_=0
                )
            ).label("total_messages"),
            func.sum(Analytics.token_count).label("total_tokens"),
            func.avg(Analytics.processing_time).label("average_response_time"),
            func.sum(
                func.case(
                    (Analytics.error_type.is_not(None), Analytics.event_count),
                    else_=0
                )
            ).label("error_count"),
            func.sum(Analytics.estimated_cost).label("cost")
        ).select_from(base_query.subquery()).group_by(time_group).order_by(time_group)
        
        result = await self.db.execute(metrics_query)
        rows = result.fetchall()
        
        metrics = []
        for row in rows:
            total_events = (row.total_conversations or 0) + (row.total_messages or 0)
            error_rate = (
                (row.error_count or 0) / total_events * 100
                if total_events > 0 else 0.0
            )
            
            metrics.append(UsageMetrics(
                period=period,
                timestamp=row.timestamp,
                active_users=row.active_users or 0,
                total_conversations=row.total_conversations or 0,
                total_messages=row.total_messages or 0,
                total_tokens=row.total_tokens or 0,
                average_response_time=row.average_response_time or 0.0,
                error_rate=error_rate,
                cost=row.cost or 0.0
            ))
        
        return metrics
    
    async def get_performance_metrics(
        self,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None
    ) -> PerformanceMetrics:
        """
        Get performance metrics for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            user_id: Optional user ID filter
            
        Returns:
            Performance metrics
        """
        base_query = select(Analytics).where(
            and_(
                Analytics.date >= start_date,
                Analytics.date <= end_date,
                Analytics.processing_time.is_not(None)
            )
        )
        
        if user_id:
            base_query = base_query.where(Analytics.user_id == user_id)
        
        # Performance query
        perf_query = select(
            func.avg(Analytics.processing_time).label("avg_response_time"),
            func.percentile_cont(0.95).within_group(
                Analytics.processing_time
            ).label("p95_response_time"),
            func.percentile_cont(0.99).within_group(
                Analytics.processing_time
            ).label("p99_response_time"),
            func.avg(Analytics.tokens_per_second).label("tokens_per_second"),
            func.count(Analytics.id).label("total_requests"),
            func.sum(
                func.case(
                    (Analytics.error_type.is_not(None), Analytics.event_count),
                    else_=0
                )
            ).label("error_count")
        ).select_from(base_query.subquery())
        
        result = await self.db.execute(perf_query)
        row = result.first()
        
        total_requests = row.total_requests or 0
        error_count = row.error_count or 0
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0.0
        
        # Calculate availability (assuming errors affect availability)
        availability = max(0, 100 - error_rate)
        
        # Calculate requests per minute (rough estimate)
        days_diff = (end_date - start_date).days + 1
        requests_per_minute = total_requests / (days_diff * 24 * 60) if days_diff > 0 else 0
        
        return PerformanceMetrics(
            average_response_time=row.avg_response_time or 0.0,
            p95_response_time=row.p95_response_time or 0.0,
            p99_response_time=row.p99_response_time or 0.0,
            tokens_per_second=row.tokens_per_second or 0.0,
            requests_per_minute=requests_per_minute,
            error_rate=error_rate,
            availability=availability
        )
    
    async def get_entity_stats(
        self,
        entity_type: str,
        start_date: date,
        end_date: date,
        limit: int = 10
    ) -> List[EntityStats]:
        """
        Get statistics for specific entity type.
        
        Args:
            entity_type: Entity type to analyze
            start_date: Start date
            end_date: End date
            limit: Maximum number of results
            
        Returns:
            List of entity statistics
        """
        stats_query = select(
            Analytics.entity_id,
            func.sum(Analytics.event_count).label("total_usage"),
            func.max(Analytics.created_at).label("last_used"),
            func.avg(Analytics.processing_time).label("average_performance"),
            func.count(func.distinct(Analytics.user_id)).label("user_count")
        ).where(
            and_(
                Analytics.entity_type == entity_type,
                Analytics.date >= start_date,
                Analytics.date <= end_date,
                Analytics.entity_id.is_not(None)
            )
        ).group_by(Analytics.entity_id).order_by(
            func.sum(Analytics.event_count).desc()
        ).limit(limit)
        
        result = await self.db.execute(stats_query)
        rows = result.fetchall()
        
        entity_stats = []
        for row in rows:
            entity_stats.append(EntityStats(
                entity_type=entity_type,
                entity_id=row.entity_id,
                total_usage=row.total_usage or 0,
                last_used=row.last_used,
                average_performance=row.average_performance or 0.0,
                user_count=row.user_count or 0,
                metadata=None
            ))
        
        return entity_stats
    
    async def _get_entity_stats(
        self,
        start_date: date,
        end_date: date,
        entity_type: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get statistics for a specific entity type."""
        query = select(func.sum(Analytics.event_count)).where(
            and_(
                Analytics.date >= start_date,
                Analytics.date <= end_date,
                Analytics.entity_type == entity_type
            )
        )
        
        if user_id:
            query = query.where(Analytics.user_id == user_id)
        
        result = await self.db.execute(query)
        total_events = result.scalar() or 0
        
        return {"total_events": total_events}
    
    async def cleanup_old_analytics(self, days_to_keep: int = 90) -> int:
        """
        Clean up old analytics data.
        
        Args:
            days_to_keep: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        # Count records to be deleted
        count_result = await self.db.execute(
            select(func.count(Analytics.id)).where(Analytics.date < cutoff_date)
        )
        records_to_delete = count_result.scalar()
        
        # Delete old records
        await self.db.execute(
            text("DELETE FROM analytics WHERE date < :cutoff_date").bindparam(
                cutoff_date=cutoff_date
            )
        )
        await self.db.commit()
        
        logger.info(
            "Analytics cleanup completed",
            records_deleted=records_to_delete,
            cutoff_date=cutoff_date
        )
        
        return records_to_delete
    
    # Convenience methods for common tracking
    
    async def track_conversation_created(
        self,
        conversation_id: int,
        user_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track conversation creation."""
        await self.track_event(
            AnalyticsCreate(
                entity_type="conversation",
                entity_id=conversation_id,
                user_id=user_id,
                event_type="created",
                metadata=metadata
            ),
            user_id=user_id
        )
    
    async def track_message_sent(
        self,
        message_id: int,
        conversation_id: int,
        user_id: int,
        token_count: int,
        processing_time: float,
        model_used: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track message sending."""
        # Estimate cost (rough calculation for OpenAI GPT-4)
        estimated_cost = token_count * 0.00003  # $0.03 per 1K tokens
        tokens_per_second = token_count / processing_time if processing_time > 0 else 0
        
        await self.track_event(
            AnalyticsCreate(
                entity_type="message",
                entity_id=message_id,
                user_id=user_id,
                event_type="created",
                token_count=token_count,
                processing_time=processing_time,
                tokens_per_second=tokens_per_second,
                estimated_cost=estimated_cost,
                metadata={
                    "conversation_id": conversation_id,
                    "model_used": model_used,
                    **(metadata or {})
                }
            ),
            user_id=user_id
        )
    
    async def track_document_uploaded(
        self,
        document_id: int,
        user_id: int,
        file_size: int,
        file_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track document upload."""
        await self.track_event(
            AnalyticsCreate(
                entity_type="document",
                entity_id=document_id,
                user_id=user_id,
                event_type="created",
                metadata={
                    "file_size": file_size,
                    "file_type": file_type,
                    **(metadata or {})
                }
            ),
            user_id=user_id
        )
    
    async def track_error(
        self,
        entity_type: str,
        entity_id: Optional[int],
        user_id: Optional[int],
        error_type: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track error occurrence."""
        await self.track_event(
            AnalyticsCreate(
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                event_type="error",
                error_type=error_type,
                error_message=error_message,
                metadata=metadata
            ),
            user_id=user_id
        )