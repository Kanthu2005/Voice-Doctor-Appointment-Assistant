from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import get_db
from app.schemas.error import ErrorResponse
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Verify FastAPI application status and SQLite database connectivity.",
    responses={
        503: {"model": ErrorResponse, "description": "Database connectivity check failed"},
    },
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Verify API availability and SQLite database connectivity."""
    settings = get_settings()
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connectivity check failed.",
        ) from exc

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        database="connected",
    )
