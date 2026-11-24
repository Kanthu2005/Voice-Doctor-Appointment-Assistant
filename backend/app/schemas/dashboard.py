from pydantic import BaseModel


class SpecialityStatsRead(BaseModel):
    """Per-speciality doctor, slot, and booking summary."""

    speciality: str
    doctor_count: int
    available_slots: int
    booked_appointments: int


class DashboardStatsRead(BaseModel):
    """Aggregated operational statistics for the clinical dashboard."""

    total_doctors: int
    total_slots: int
    available_slots: int
    booked_slots: int
    total_appointments: int
    active_appointments: int
    cancelled_appointments: int
    appointments_today: int
    speciality_breakdown: list[SpecialityStatsRead]
