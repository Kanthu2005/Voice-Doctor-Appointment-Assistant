"""Pydantic request and response schemas package."""

from app.schemas.appointment import (
    AppointmentActionResponse,
    AppointmentBookRequest,
    AppointmentCancelRequest,
    AppointmentRead,
    validate_phone_string,
)
from app.schemas.dashboard import DashboardStatsRead, SpecialityStatsRead
from app.schemas.doctor import (
    AvailabilitySlotRead,
    DoctorRead,
    DoctorWithSlotsRead,
    SlotRead,
)
from app.schemas.error import ErrorResponse, ValidationErrorResponse
from app.schemas.health import HealthResponse

__all__ = [
    "AppointmentActionResponse",
    "AppointmentBookRequest",
    "AppointmentCancelRequest",
    "AppointmentRead",
    "AvailabilitySlotRead",
    "DashboardStatsRead",
    "DoctorRead",
    "DoctorWithSlotsRead",
    "ErrorResponse",
    "HealthResponse",
    "SlotRead",
    "SpecialityStatsRead",
    "ValidationErrorResponse",
    "validate_phone_string",
]
