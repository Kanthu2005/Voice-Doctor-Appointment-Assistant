from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.doctor import DoctorRead, DoctorWithSlotsRead
from app.schemas.error import ErrorResponse
from app.services import doctor_service

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get(
    "",
    response_model=list[DoctorRead],
    summary="List all doctors",
    description="Retrieve doctors from SQLite, optionally filtered by medical speciality.",
)
async def get_doctors(
    speciality: str | None = Query(
        default=None,
        description="Optional speciality filter (case-insensitive substring match, e.g. 'Cardiology').",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[DoctorRead]:
    """Return all doctors, optionally filtered by speciality."""
    doctors = await doctor_service.list_doctors(db, speciality=speciality)
    return [DoctorRead.model_validate(doctor) for doctor in doctors]


@router.get(
    "/{doctor_id}",
    response_model=DoctorWithSlotsRead,
    summary="Get doctor details",
    description="Retrieve a single doctor profile along with all scheduled appointment slots.",
    responses={
        404: {"model": ErrorResponse, "description": "Doctor not found"},
    },
)
async def get_doctor(
    doctor_id: int = Path(..., gt=0, description="Unique identifier of the doctor."),
    db: AsyncSession = Depends(get_db),
) -> DoctorWithSlotsRead:
    """Return a single doctor profile along with all of their slots."""
    doctor = await doctor_service.get_doctor_by_id(db, doctor_id, include_slots=True)
    return DoctorWithSlotsRead.model_validate(doctor)
