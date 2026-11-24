from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class SlotRead(BaseModel):
    """Serialized view of an appointment time slot."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    appointment_date: date
    appointment_time: str
    status: str


class DoctorRead(BaseModel):
    """Serialized doctor profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    speciality: str
    qualification: str
    experience: int = Field(ge=0)
    consultation_fee: float = Field(ge=0)
    available_days: str


class DoctorWithSlotsRead(DoctorRead):
    """Doctor profile including associated time slots."""

    slots: list[SlotRead] = []


class AvailabilitySlotRead(SlotRead):
    """Slot with doctor metadata for availability search responses."""

    doctor_name: str
    speciality: str
    consultation_fee: float
