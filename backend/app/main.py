from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.db import init_db
from app.routes import (
    appointments_router,
    availability_router,
    dashboard_router,
    doctors_router,
    health_router,
    voice_router,
)

OPENAPI_TAGS = [
    {"name": "Health", "description": "Service and database health diagnostics."},
    {"name": "Doctors", "description": "Doctor directory and speciality filtering."},
    {"name": "Availability", "description": "Available appointment slot lookup."},
    {"name": "Appointments", "description": "Booking, listing, and cancelling appointments."},
    {"name": "Dashboard", "description": "Aggregated clinic statistics."},
    {"name": "Voice", "description": "Pipecat real-time Voice AI WebSocket and status endpoints."},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Run startup and shutdown lifecycle tasks."""
    await init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        description=(
            "REST API and SQLite persistence backend for the Voice AI Doctor "
            "Appointment Assistant."
        ),
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": "Request validation failed.",
                "errors": [
                    {
                        "loc": list(err.get("loc", ())),
                        "msg": err.get("msg", "Invalid value"),
                        "type": err.get("type", "value_error"),
                    }
                    for err in exc.errors()
                ],
            },
        )

    @application.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(_: Request, __: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred while processing the request."},
        )

    application.include_router(health_router, prefix="/api")
    application.include_router(doctors_router, prefix="/api")
    application.include_router(availability_router, prefix="/api")
    application.include_router(appointments_router, prefix="/api")
    application.include_router(dashboard_router, prefix="/api")
    application.include_router(voice_router)
    return application


app = create_app()
