"""Aggregated SQLite statistics service for the dashboard API."""

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Appointment, AppointmentStatus, Doctor, Slot, SlotStatus
from app.schemas.dashboard import DashboardStatsRead, SpecialityStatsRead


async def get_dashboard_stats(db: AsyncSession) -> DashboardStatsRead:
    """Compute real-time doctor, slot, and appointment metrics from SQLite."""
    total_doctors = int(await db.scalar(select(func.count(Doctor.id))) or 0)

    slot_counts = (
        await db.execute(
            select(
                func.count(Slot.id),
                func.coalesce(
                    func.sum(case((Slot.status == SlotStatus.AVAILABLE.value, 1), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(case((Slot.status == SlotStatus.BOOKED.value, 1), else_=0)),
                    0,
                ),
            )
        )
    ).one()

    total_slots = int(slot_counts[0] or 0)
    available_slots = int(slot_counts[1] or 0)
    booked_slots = int(slot_counts[2] or 0)

    today = date.today()
    appt_counts = (
        await db.execute(
            select(
                func.count(Appointment.id),
                func.coalesce(
                    func.sum(
                        case((Appointment.status == AppointmentStatus.BOOKED.value, 1), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case((Appointment.status == AppointmentStatus.CANCELLED.value, 1), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (Appointment.status == AppointmentStatus.BOOKED.value)
                                & (Appointment.appointment_date == today),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
        )
    ).one()

    total_appointments = int(appt_counts[0] or 0)
    active_appointments = int(appt_counts[1] or 0)
    cancelled_appointments = int(appt_counts[2] or 0)
    appointments_today = int(appt_counts[3] or 0)

    # Per-speciality breakdown using independent sub-aggregations to avoid join row multiplication.
    doc_by_spec = {
        row[0]: int(row[1])
        for row in (
            await db.execute(
                select(Doctor.speciality, func.count(Doctor.id)).group_by(Doctor.speciality)
            )
        ).all()
    }
    avail_by_spec = {
        row[0]: int(row[1])
        for row in (
            await db.execute(
                select(Doctor.speciality, func.count(Slot.id))
                .join(Slot, Slot.doctor_id == Doctor.id)
                .where(Slot.status == SlotStatus.AVAILABLE.value)
                .group_by(Doctor.speciality)
            )
        ).all()
    }
    booked_by_spec = {
        row[0]: int(row[1])
        for row in (
            await db.execute(
                select(Doctor.speciality, func.count(Appointment.id))
                .join(Appointment, Appointment.doctor_id == Doctor.id)
                .where(Appointment.status == AppointmentStatus.BOOKED.value)
                .group_by(Doctor.speciality)
            )
        ).all()
    }

    speciality_breakdown = [
        SpecialityStatsRead(
            speciality=speciality,
            doctor_count=doc_by_spec[speciality],
            available_slots=avail_by_spec.get(speciality, 0),
            booked_appointments=booked_by_spec.get(speciality, 0),
        )
        for speciality in sorted(doc_by_spec)
    ]

    return DashboardStatsRead(
        total_doctors=total_doctors,
        total_slots=total_slots,
        available_slots=available_slots,
        booked_slots=booked_slots,
        total_appointments=total_appointments,
        active_appointments=active_appointments,
        cancelled_appointments=cancelled_appointments,
        appointments_today=appointments_today,
        speciality_breakdown=speciality_breakdown,
    )
