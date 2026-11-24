from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.doctor import AvailabilitySlotRead
from app.schemas.error import ErrorResponse
from app.services import doctor_service

router = APIRouter(tags=["Availability"])


@router.get(
    "/availability",
    response_model=list[AvailabilitySlotRead],
    summary="Get available appointment slots",
    description="Retrieve available appointment slots filtered by doctor, speciality, and/or date.",
    responses={
        404: {"model": ErrorResponse, "description": "Specified doctor_id was not found"},
    },
)
async def get_availability(
    doctor_id: int | None = Query(default=None, gt=0, description="Filter by doctor ID."),
    doctor_name: str | None = Query(
        default=None,
        description="Filter by doctor name (case-insensitive substring match).",
    ),
    speciality: str | None = Query(
        default=None,
        description="Filter by doctor speciality (case-insensitive substring match).",
    ),
    appointment_date: date | None = Query(
        default=None,
        description="Filter by slot date in YYYY-MM-DD format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[AvailabilitySlotRead]:
    """Return available appointment slots matching the provided filters."""
    slots = await doctor_service.get_doctor_availability(
        db,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        speciality=speciality,
        appointment_date=appointment_date,
        only_available=True,
    )
    return [
        AvailabilitySlotRead(
            id=slot.id,
            doctor_id=slot.doctor_id,
            appointment_date=slot.appointment_date,
            appointment_time=slot.appointment_time,
            status=slot.status,
            doctor_name=slot.doctor.name,
            speciality=slot.doctor.speciality,
            consultation_fee=slot.doctor.consultation_fee,
        )
        for slot in slots
    ]
