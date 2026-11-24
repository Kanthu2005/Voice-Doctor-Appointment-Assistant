"""Transactional business logic for booking, listing, and cancelling appointments."""

from datetime import date

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AppointmentAlreadyCancelledError,
    AppointmentNotFoundError,
    DoctorNotFoundError,
    DuplicateBookingError,
    SlotAlreadyBookedError,
    SlotNotFoundError,
    ValidationDomainError,
)
from app.models.domain import Appointment, AppointmentStatus, Doctor, Slot, SlotStatus
from app.schemas.appointment import AppointmentBookRequest, AppointmentCancelRequest


async def _resolve_target_slot(db: AsyncSession, payload: AppointmentBookRequest) -> Slot:
    """Resolve the target slot from either slot_id or (doctor_id, date, time)."""
    if payload.slot_id is not None:
        slot = await db.scalar(
            select(Slot).options(selectinload(Slot.doctor)).where(Slot.id == payload.slot_id)
        )
        if slot is None:
            raise SlotNotFoundError(f"Slot with id={payload.slot_id} was not found.")
        return slot

    doctor_exists = await db.scalar(select(Doctor.id).where(Doctor.id == payload.doctor_id))
    if doctor_exists is None:
        raise DoctorNotFoundError(f"Doctor with id={payload.doctor_id} was not found.")

    slot = await db.scalar(
        select(Slot)
        .options(selectinload(Slot.doctor))
        .where(
            Slot.doctor_id == payload.doctor_id,
            Slot.appointment_date == payload.appointment_date,
            Slot.appointment_time == payload.appointment_time,
        )
    )
    if slot is None:
        raise SlotNotFoundError(
            f"No slot found for doctor_id={payload.doctor_id} on "
            f"{payload.appointment_date} at {payload.appointment_time}."
        )
    return slot


async def book_appointment(
    db: AsyncSession,
    payload: AppointmentBookRequest,
) -> Appointment:
    """Atomically book an available slot and create the corresponding appointment."""
    slot = await _resolve_target_slot(db, payload)

    if slot.status != SlotStatus.AVAILABLE.value:
        raise SlotAlreadyBookedError(
            f"Slot {slot.id} ({slot.appointment_date} {slot.appointment_time}) is already booked."
        )

    existing_same_doctor_date = await db.scalar(
        select(Appointment.id).where(
            Appointment.patient_phone == payload.patient_phone,
            Appointment.doctor_id == slot.doctor_id,
            Appointment.appointment_date == slot.appointment_date,
            Appointment.status == AppointmentStatus.BOOKED.value,
        )
    )
    if existing_same_doctor_date is not None:
        raise DuplicateBookingError(
            f"Phone '{payload.patient_phone}' already has an active appointment with "
            f"{slot.doctor.name} on {slot.appointment_date}."
        )

    existing_time_conflict = await db.scalar(
        select(Appointment.id).where(
            Appointment.patient_phone == payload.patient_phone,
            Appointment.appointment_date == slot.appointment_date,
            Appointment.appointment_time == slot.appointment_time,
            Appointment.status == AppointmentStatus.BOOKED.value,
        )
    )
    if existing_time_conflict is not None:
        raise DuplicateBookingError(
            f"Phone '{payload.patient_phone}' already has an active appointment on "
            f"{slot.appointment_date} at {slot.appointment_time}."
        )

    claim_result = await db.execute(
        update(Slot)
        .where(Slot.id == slot.id, Slot.status == SlotStatus.AVAILABLE.value)
        .values(status=SlotStatus.BOOKED.value)
    )
    if claim_result.rowcount != 1:  # type: ignore[attr-defined]
        await db.rollback()
        raise SlotAlreadyBookedError(
            f"Slot {slot.id} ({slot.appointment_date} {slot.appointment_time}) is already booked."
        )

    appointment = Appointment(
        patient_phone=payload.patient_phone,
        doctor_id=slot.doctor_id,
        slot_id=slot.id,
        appointment_date=slot.appointment_date,
        appointment_time=slot.appointment_time,
        status=AppointmentStatus.BOOKED.value,
    )
    db.add(appointment)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise SlotAlreadyBookedError("Selected slot is already booked.") from exc

    return await get_appointment_by_id(db, appointment.id)


async def cancel_appointment(
    db: AsyncSession,
    payload: AppointmentCancelRequest,
) -> Appointment:
    """Cancel a booked appointment and release its slot back to 'available'."""
    appointment: Appointment | None = None

    if payload.appointment_id is not None:
        appointment = await db.scalar(
            select(Appointment)
            .options(selectinload(Appointment.doctor), selectinload(Appointment.slot))
            .where(Appointment.id == payload.appointment_id)
        )
        if appointment is None:
            raise AppointmentNotFoundError(
                f"Appointment with id={payload.appointment_id} was not found."
            )
        if appointment.status == AppointmentStatus.CANCELLED.value:
            raise AppointmentAlreadyCancelledError(
                f"Appointment {appointment.id} is already cancelled."
            )
    else:
        stmt = (
            select(Appointment)
            .options(selectinload(Appointment.doctor), selectinload(Appointment.slot))
            .where(
                Appointment.patient_phone == payload.patient_phone,
                Appointment.status == AppointmentStatus.BOOKED.value,
            )
            .order_by(Appointment.appointment_date.asc(), Appointment.created_at.desc())
        )
        if payload.doctor_id is not None:
            stmt = stmt.where(Appointment.doctor_id == payload.doctor_id)
        if payload.appointment_date is not None:
            stmt = stmt.where(Appointment.appointment_date == payload.appointment_date)
        if payload.appointment_time is not None:
            stmt = stmt.where(Appointment.appointment_time == payload.appointment_time)

        matches = list((await db.scalars(stmt)).all())
        if not matches:
            raise AppointmentNotFoundError(
                f"No active booked appointment found for phone '{payload.patient_phone}'."
            )
        if len(matches) > 1:
            raise ValidationDomainError(
                "Multiple active appointments found for this phone number. "
                "Specify appointment_id or doctor_id/appointment_date/appointment_time."
            )
        appointment = matches[0]

    appointment.status = AppointmentStatus.CANCELLED.value
    await db.execute(
        update(Slot)
        .where(Slot.id == appointment.slot_id)
        .values(status=SlotStatus.AVAILABLE.value)
    )
    await db.commit()

    return await get_appointment_by_id(db, appointment.id)


async def get_appointment_by_id(db: AsyncSession, appointment_id: int) -> Appointment:
    """Fetch a single appointment with doctor details or raise AppointmentNotFoundError."""
    appointment = await db.scalar(
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.id == appointment_id)
    )
    if appointment is None:
        raise AppointmentNotFoundError(f"Appointment with id={appointment_id} was not found.")
    return appointment


async def list_appointments(
    db: AsyncSession,
    *,
    patient_phone: str | None = None,
    doctor_id: int | None = None,
    status: AppointmentStatus | None = None,
    appointment_date: date | None = None,
) -> list[Appointment]:
    """List appointments ordered newest first, with optional filters."""
    stmt = (
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .order_by(Appointment.created_at.desc(), Appointment.id.desc())
    )

    if patient_phone is not None:
        stmt = stmt.where(Appointment.patient_phone == patient_phone)
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if status is not None:
        stmt = stmt.where(Appointment.status == status.value)
    if appointment_date is not None:
        stmt = stmt.where(Appointment.appointment_date == appointment_date)

    result = await db.scalars(stmt)
    return list(result.all())
