"""Database operations for doctor profiles and appointment slot availability."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DoctorNotFoundError
from app.models.domain import Doctor, Slot, SlotStatus


async def list_doctors(
    db: AsyncSession,
    *,
    speciality: str | None = None,
    include_slots: bool = False,
) -> list[Doctor]:
    """Return all doctors, optionally filtered by speciality (case-insensitive substring)."""
    stmt = select(Doctor).order_by(Doctor.id.asc())
    if include_slots:
        stmt = stmt.options(selectinload(Doctor.slots))
    if speciality:
        stmt = stmt.where(Doctor.speciality.ilike(f"%{speciality.strip()}%"))

    result = await db.scalars(stmt)
    return list(result.all())


async def get_doctor_by_id(
    db: AsyncSession,
    doctor_id: int,
    *,
    include_slots: bool = True,
) -> Doctor:
    """Return a single doctor by primary key or raise DoctorNotFoundError."""
    stmt = select(Doctor).where(Doctor.id == doctor_id)
    if include_slots:
        stmt = stmt.options(selectinload(Doctor.slots))

    doctor = await db.scalar(stmt)
    if doctor is None:
        raise DoctorNotFoundError(f"Doctor with id={doctor_id} was not found.")
    return doctor


async def get_doctor_availability(
    db: AsyncSession,
    *,
    doctor_id: int | None = None,
    doctor_name: str | None = None,
    speciality: str | None = None,
    appointment_date: date | None = None,
    only_available: bool = True,
) -> list[Slot]:
    """Query appointment slots filtered by doctor, speciality, date, and availability."""
    if doctor_id is not None:
        # Validate doctor exists so invalid IDs produce an explicit 404 instead of silent empty lists.
        await get_doctor_by_id(db, doctor_id, include_slots=False)

    stmt = (
        select(Slot)
        .join(Slot.doctor)
        .options(selectinload(Slot.doctor))
        .order_by(Slot.appointment_date.asc(), Slot.appointment_time.asc(), Slot.doctor_id.asc())
    )

    if only_available:
        stmt = stmt.where(Slot.status == SlotStatus.AVAILABLE.value)
    if doctor_id is not None:
        stmt = stmt.where(Slot.doctor_id == doctor_id)
    if doctor_name:
        stmt = stmt.where(Doctor.name.ilike(f"%{doctor_name.strip()}%"))
    if speciality:
        stmt = stmt.where(Doctor.speciality.ilike(f"%{speciality.strip()}%"))
    if appointment_date is not None:
        stmt = stmt.where(Slot.appointment_date == appointment_date)

    result = await db.scalars(stmt)
    return list(result.all())
