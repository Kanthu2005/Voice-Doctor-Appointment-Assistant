from datetime import date

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationDomainError
from app.db import get_db
from app.models.domain import Appointment, AppointmentStatus
from app.schemas.appointment import (
    AppointmentActionResponse,
    AppointmentBookRequest,
    AppointmentCancelRequest,
    AppointmentRead,
    validate_phone_string,
)
from app.schemas.error import ErrorResponse, ValidationErrorResponse
from app.services import appointment_service

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _to_appointment_read(appointment: Appointment) -> AppointmentRead:
    return AppointmentRead(
        id=appointment.id,
        patient_phone=appointment.patient_phone,
        doctor_id=appointment.doctor_id,
        slot_id=appointment.slot_id,
        doctor_name=appointment.doctor.name,
        speciality=appointment.doctor.speciality,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        status=appointment.status,
        created_at=appointment.created_at,
    )


@router.get(
    "",
    response_model=list[AppointmentRead],
    summary="List appointments",
    description="Retrieve appointments from SQLite with optional phone, doctor, status, and date filters.",
    responses={
        422: {"model": ValidationErrorResponse, "description": "Invalid filter parameter"},
    },
)
async def get_appointments(
    patient_phone: str | None = Query(
        default=None,
        description="Filter by patient phone number (string preserving leading zeros and '+').",
    ),
    doctor_id: int | None = Query(default=None, gt=0, description="Filter by doctor ID."),
    appointment_status: AppointmentStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by appointment status ('booked' or 'cancelled').",
    ),
    appointment_date: date | None = Query(
        default=None,
        description="Filter by appointment date (YYYY-MM-DD).",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[AppointmentRead]:
    """List appointments with optional phone, doctor, status, and date filters."""
    normalized_phone: str | None = None
    if patient_phone is not None:
        try:
            normalized_phone = validate_phone_string(patient_phone)
        except ValueError as exc:
            raise ValidationDomainError(str(exc)) from exc

    appointments = await appointment_service.list_appointments(
        db,
        patient_phone=normalized_phone,
        doctor_id=doctor_id,
        status=appointment_status,
        appointment_date=appointment_date,
    )
    return [_to_appointment_read(item) for item in appointments]


@router.post(
    "",
    response_model=AppointmentActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an appointment",
    description=(
        "Book an available slot using a patient phone number. Validates slot availability "
        "and prevents double or duplicate bookings."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Doctor or slot not found"},
        409: {
            "model": ErrorResponse,
            "description": "Slot already booked or duplicate booking for patient",
        },
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
    },
)
async def create_appointment(
    payload: AppointmentBookRequest,
    db: AsyncSession = Depends(get_db),
) -> AppointmentActionResponse:
    """Create a new appointment for an available slot."""
    appointment = await appointment_service.book_appointment(db, payload)
    return AppointmentActionResponse(
        message="Appointment booked successfully.",
        appointment=_to_appointment_read(appointment),
    )


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentActionResponse,
    summary="Cancel an appointment",
    description="Cancel an existing appointment by ID and release its slot back to available.",
    responses={
        404: {"model": ErrorResponse, "description": "Appointment not found"},
        409: {"model": ErrorResponse, "description": "Appointment already cancelled"},
    },
)
async def cancel_appointment_by_id(
    appointment_id: int = Path(..., gt=0, description="ID of the appointment to cancel."),
    db: AsyncSession = Depends(get_db),
) -> AppointmentActionResponse:
    """Cancel a specific appointment by its ID and release its slot."""
    appointment = await appointment_service.cancel_appointment(
        db,
        AppointmentCancelRequest(appointment_id=appointment_id),
    )
    return AppointmentActionResponse(
        message="Appointment cancelled and slot released.",
        appointment=_to_appointment_read(appointment),
    )
