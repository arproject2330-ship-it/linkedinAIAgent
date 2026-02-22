"""Analytics from post history: best days, times, top posts, and performance insights for agents."""
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import PostHistory
from app.models.schemas import AnalyticsSummary, PerformanceInsights

from app.utils.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Compute analytics and performance insights from PostHistory."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_summary(self) -> AnalyticsSummary:
        """Dashboard summary: totals, best days/times, top posts."""
        result = await self.session.execute(
            select(
                func.count(PostHistory.id).label("total_posts"),
                func.coalesce(func.sum(PostHistory.impressions), 0).label("total_impressions"),
                func.avg(PostHistory.engagement_rate).label("avg_engagement"),
            )
        )
        row = result.one_or_none()
        if not row or row.total_posts == 0:
            return AnalyticsSummary()

        # Best days and times from published_at; top posts by impressions
        all_posts_result = await self.session.execute(
            select(PostHistory)
            .order_by(PostHistory.impressions.desc().nullslast(), PostHistory.published_at.desc())
            .limit(100)
        )
        posts = list(all_posts_result.scalars().all())

        day_counts: dict[str, int] = defaultdict(int)
        time_slots: dict[str, int] = defaultdict(int)
        top_posts: list[dict[str, Any]] = []
        for p in posts:
            if p.published_at:
                day_name = p.published_at.strftime("%A")
                day_counts[day_name] += (p.impressions or 0) or 1
                hour = p.published_at.hour
                slot = f"{hour:02d}:00-{(hour+1)%24:02d}:00"
                time_slots[slot] += (p.impressions or 0) or 1
            top_posts.append({
                "id": p.id,
                "content_preview": (p.content_text or "")[:200],
                "impressions": p.impressions,
                "engagement_rate": p.engagement_rate,
                "published_at": p.published_at.isoformat() if p.published_at else None,
            })

        best_days = sorted(day_counts.keys(), key=lambda d: day_counts[d], reverse=True)[:5]
        best_times = sorted(time_slots.keys(), key=lambda t: time_slots[t], reverse=True)[:5]

        return AnalyticsSummary(
            total_posts=row.total_posts or 0,
            total_impressions=int(row.total_impressions or 0),
            avg_engagement_rate=float(row.avg_engagement or 0),
            best_days=best_days,
            best_times=best_times,
            top_posts=top_posts[:10],
        )

    async def get_performance_insights(self) -> PerformanceInsights:
        """Structured insights for the Performance Intelligence Agent."""
        summary = await self.get_summary()
        # Infer ideal length from top posts (simplified: medium length)
        ideal_length = "150-300 words for body; hook under 2 lines"
        return PerformanceInsights(
            best_days=summary.best_days,
            best_time_ranges=summary.best_times,
            ideal_length=ideal_length,
            top_topics=[],  # Could add NLP/keyword extraction later
            hook_style_pattern="Strong opening line; question or stat or story",
        )