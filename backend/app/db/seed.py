"""Idempotent database seed data for doctors and upcoming appointment slots."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Doctor, Slot, SlotStatus

WEEKDAY_ABBR = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

SEED_DOCTORS: list[dict[str, object]] = [
    {
        "name": "Dr. Aarav Mehta",
        "speciality": "Cardiology",
        "qualification": "MBBS, MD, DM (Cardiology)",
        "experience": 14,
        "consultation_fee": 1200.0,
        "available_days": "Mon,Tue,Wed,Thu,Fri",
        "slot_times": ["09:30 AM", "10:30 AM", "11:30 AM", "03:00 PM", "04:30 PM"],
    },
    {
        "name": "Dr. Priya Nair",
        "speciality": "Dermatology",
        "qualification": "MBBS, MD (Dermatology)",
        "experience": 9,
        "consultation_fee": 800.0,
        "available_days": "Mon,Wed,Thu,Sat",
        "slot_times": ["10:00 AM", "11:00 AM", "02:00 PM", "03:30 PM", "05:00 PM"],
    },
    {
        "name": "Dr. Vikram Rao",
        "speciality": "Neurology",
        "qualification": "MBBS, MD, DM (Neurology)",
        "experience": 12,
        "consultation_fee": 1500.0,
        "available_days": "Tue,Wed,Thu,Fri",
        "slot_times": ["09:00 AM", "10:30 AM", "12:00 PM", "02:30 PM", "04:00 PM"],
    },
    {
        "name": "Dr. Rohan Kapoor",
        "speciality": "Orthopaedics",
        "qualification": "MBBS, MS (Orthopaedics)",
        "experience": 11,
        "consultation_fee": 1000.0,
        "available_days": "Mon,Tue,Thu,Fri,Sat",
        "slot_times": ["09:30 AM", "11:00 AM", "01:30 PM", "03:00 PM", "04:30 PM"],
    },
    {
        "name": "Dr. Sarah Smith",
        "speciality": "General Medicine",
        "qualification": "MBBS, MD (General Medicine)",
        "experience": 8,
        "consultation_fee": 600.0,
        "available_days": "Mon,Tue,Wed,Thu,Fri,Sat",
        "slot_times": ["09:00 AM", "10:00 AM", "11:30 AM", "02:00 PM", "04:00 PM"],
    },
    {
        "name": "Dr. Emily Rodriguez",
        "speciality": "Paediatrics",
        "qualification": "MBBS, MD (Paediatrics)",
        "experience": 10,
        "consultation_fee": 750.0,
        "available_days": "Mon,Tue,Wed,Fri,Sat",
        "slot_times": ["09:30 AM", "10:30 AM", "12:00 PM", "03:30 PM", "05:00 PM"],
    },
]


def _generate_slots_for_doctor(
    doctor: Doctor,
    slot_times: list[str],
    start_date: date,
    horizon_days: int = 7,
) -> list[Slot]:
    """Generate realistic available slots for matching working days in the next `horizon_days`."""
    working_days = {day.strip() for day in doctor.available_days.split(",") if day.strip()}
    generated: list[Slot] = []

    for offset in range(horizon_days):
        candidate_date = start_date + timedelta(days=offset)
        day_name = WEEKDAY_ABBR[candidate_date.weekday()]
        if day_name not in working_days:
            continue

        for time_str in slot_times:
            generated.append(
                Slot(
                    doctor_id=doctor.id,
                    appointment_date=candidate_date,
                    appointment_time=time_str,
                    status=SlotStatus.AVAILABLE.value,
                )
            )

    return generated


async def seed_database(
    session: AsyncSession,
    *,
    start_date: date | None = None,
    horizon_days: int = 7,
) -> int:
    """Populate initial doctors and available slots if the doctors table is empty.

    Returns the number of newly seeded doctors.
    """
    existing_count = await session.scalar(select(func.count(Doctor.id)))
    if existing_count and existing_count > 0:
        return 0

    anchor_date = start_date or date.today()
    created_doctors = 0

    for entry in SEED_DOCTORS:
        doctor = Doctor(
            name=str(entry["name"]),
            speciality=str(entry["speciality"]),
            qualification=str(entry["qualification"]),
            experience=int(entry["experience"]),  # type: ignore[arg-type]
            consultation_fee=float(entry["consultation_fee"]),  # type: ignore[arg-type]
            available_days=str(entry["available_days"]),
        )
        session.add(doctor)
        await session.flush()

        slot_times = list(entry["slot_times"])  # type: ignore[arg-type]
        slots = _generate_slots_for_doctor(
            doctor=doctor,
            slot_times=slot_times,
            start_date=anchor_date,
            horizon_days=horizon_days,
        )
        session.add_all(slots)
        created_doctors += 1

    await session.commit()
    return created_doctors
