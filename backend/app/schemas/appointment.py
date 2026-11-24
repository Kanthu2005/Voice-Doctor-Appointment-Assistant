import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.domain import AppointmentStatus

_PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\-\s]{5,22}[0-9]$")


def validate_phone_string(value: object) -> str:
    """Validate and normalize a phone number while strictly keeping it a string.

    Rejects raw numeric inputs so callers never silently drop leading zeros
    or country-code prefixes.
    """
    if not isinstance(value, str):
        raise ValueError("patient_phone must be a string to preserve leading zeros and country codes.")

    raw = value.strip()
    if not _PHONE_PATTERN.match(raw):
        raise ValueError(
            "Invalid phone number format. Provide 7-15 digits with optional leading '+'."
        )

    canonical = re.sub(r"[\s\-]+", "", raw)
    digit_count = sum(ch.isdigit() for ch in canonical)
    if digit_count < 7 or digit_count > 15:
        raise ValueError("Phone number must contain between 7 and 15 digits.")

    return canonical


class AppointmentBookRequest(BaseModel):
    """Request payload for booking a doctor appointment."""

    patient_phone: str = Field(
        ...,
        description="Caller phone number kept as string (e.g. '+919876543210' or '07911123456').",
    )
    slot_id: int | None = Field(default=None, gt=0)
    doctor_id: int | None = Field(default=None, gt=0)
    appointment_date: date | None = None
    appointment_time: str | None = Field(default=None, min_length=3, max_length=20)

    @field_validator("patient_phone", mode="before")
    @classmethod
    def check_patient_phone(cls, value: object) -> str:
        return validate_phone_string(value)

    @field_validator("appointment_time")
    @classmethod
    def normalize_time(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def verify_slot_selector(self) -> "AppointmentBookRequest":
        has_slot_id = self.slot_id is not None
        has_composite = (
            self.doctor_id is not None
            and self.appointment_date is not None
            and self.appointment_time is not None
        )
        if not has_slot_id and not has_composite:
            raise ValueError(
                "Provide either 'slot_id' or all of 'doctor_id', 'appointment_date', and 'appointment_time'."
            )
        return self


class AppointmentCancelRequest(BaseModel):
    """Request payload for cancelling an existing appointment."""

    appointment_id: int | None = Field(default=None, gt=0)
    patient_phone: str | None = None
    doctor_id: int | None = Field(default=None, gt=0)
    appointment_date: date | None = None
    appointment_time: str | None = Field(default=None, min_length=3, max_length=20)

    @field_validator("patient_phone", mode="before")
    @classmethod
    def check_patient_phone(cls, value: object) -> str | None:
        if value is None:
            return None
        return validate_phone_string(value)

    @field_validator("appointment_time")
    @classmethod
    def normalize_time(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def verify_identifier(self) -> "AppointmentCancelRequest":
        if self.appointment_id is None and self.patient_phone is None:
            raise ValueError("Provide either 'appointment_id' or 'patient_phone' to cancel.")
        return self


class AppointmentRead(BaseModel):
    """Serialized appointment record returned by API and service methods."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_phone: str
    doctor_id: int
    slot_id: int
    doctor_name: str
    speciality: str
    appointment_date: date
    appointment_time: str
    status: AppointmentStatus | str
    created_at: datetime


class AppointmentActionResponse(BaseModel):
    """Structured response for appointment booking and cancellation endpoints."""

    message: str
    appointment: AppointmentRead
