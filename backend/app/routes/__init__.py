"""FastAPI API and WebSocket route modules."""

from app.routes.appointments import router as appointments_router
from app.routes.availability import router as availability_router
from app.routes.dashboard import router as dashboard_router
from app.routes.doctors import router as doctors_router
from app.routes.health import router as health_router
from app.routes.voice import router as voice_router

__all__ = [
    "appointments_router",
    "availability_router",
    "dashboard_router",
    "doctors_router",
    "health_router",
    "voice_router",
]
