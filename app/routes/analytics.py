"""GET /analytics."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.analytics_service import AnalyticsService
from app.models.schemas import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsSummary)
async def get_analytics(session: AsyncSession = Depends(get_db)):
    """Return dashboard analytics from post history."""
    service = AnalyticsService(session)
    return await service.get_summary()
