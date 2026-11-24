from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.dashboard import DashboardStatsRead
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/stats",
    response_model=DashboardStatsRead,
    summary="Get dashboard statistics",
    description="Retrieve aggregated doctor, slot, and appointment metrics from SQLite.",
)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
) -> DashboardStatsRead:
    """Return real-time operational statistics for the clinical dashboard."""
    return await dashboard_service.get_dashboard_stats(db)
