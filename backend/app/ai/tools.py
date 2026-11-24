"""Gemini function-calling tools backed by the SQLite domain service layer."""

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.models.domain import Appointment, AppointmentStatus
from app.schemas.appointment import (
    AppointmentBookRequest,
    AppointmentCancelRequest,
    validate_phone_string,
)
from app.services import appointment_service, doctor_service


def _serialize_appointment(appointment: Appointment) -> dict[str, Any]:
    return {
        "appointment_id": appointment.id,
        "patient_phone": appointment.patient_phone,
        "doctor_id": appointment.doctor_id,
        "doctor_name": appointment.doctor.name,
        "speciality": appointment.doctor.speciality,
        "slot_id": appointment.slot_id,
        "appointment_date": appointment.appointment_date.isoformat(),
        "appointment_time": appointment.appointment_time,
        "status": str(appointment.status),
    }


def _parse_iso_date(date_text: str | None) -> tuple[date | None, str | None]:
    if date_text is None or not date_text.strip():
        return None, None
    try:
        return date.fromisoformat(date_text.strip()), None
    except ValueError:
        return None, f"Invalid appointment_date '{date_text}'. Expected YYYY-MM-DD format."


async def check_doctor_availability(
    db: AsyncSession,
    doctor_name: str | None = None,
    speciality: str | None = None,
    appointment_date: str | None = None,
) -> dict[str, Any]:
    """Query SQLite for matching doctors and currently available appointment slots."""
    parsed_date, date_error = _parse_iso_date(appointment_date)
    if date_error:
        return {"ok": False, "error": date_error}

    doctors = await doctor_service.list_doctors(db, speciality=speciality)
    if doctor_name:
        needle = doctor_name.strip().lower()
        doctors = [doc for doc in doctors if needle in doc.name.lower()]

    slots = await doctor_service.get_doctor_availability(
        db,
        doctor_name=doctor_name,
        speciality=speciality,
        appointment_date=parsed_date,
        only_available=True,
    )

    doctor_summaries = [
        {
            "doctor_id": doc.id,
            "name": doc.name,
            "speciality": doc.speciality,
            "qualification": doc.qualification,
            "experience_years": doc.experience,
            "consultation_fee": doc.consultation_fee,
            "available_days": doc.available_days,
        }
        for doc in doctors
    ]

    available_slots = [
        {
            "slot_id": slot.id,
            "doctor_id": slot.doctor_id,
            "doctor_name": slot.doctor.name,
            "speciality": slot.doctor.speciality,
            "appointment_date": slot.appointment_date.isoformat(),
            "appointment_time": slot.appointment_time,
            "consultation_fee": slot.doctor.consultation_fee,
        }
        for slot in slots
    ]

    if not available_slots:
        return {
            "ok": True,
            "count": 0,
            "doctors": doctor_summaries,
            "available_slots": [],
            "message": "No available slots matched those criteria in the database.",
        }

    return {
        "ok": True,
        "count": len(available_slots),
        "doctors": doctor_summaries,
        "available_slots": available_slots,
        "message": f"Found {len(available_slots)} available slot(s).",
    }


async def book_appointment(
    db: AsyncSession,
    caller_phone: str,
    doctor_id: int,
    appointment_date: str,
    appointment_time: str,
    phone_confirmed: bool = False,
) -> dict[str, Any]:
    """Book an appointment in SQLite after validating phone confirmation and slot availability."""
    try:
        normalized_phone = validate_phone_string(caller_phone)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    if not phone_confirmed:
        return {
            "ok": False,
            "requires_phone_confirmation": True,
            "caller_phone": normalized_phone,
            "message": (
                f"Phone number {normalized_phone} has not been confirmed yet. "
                f"Repeat '{normalized_phone}' to the caller and ask them to confirm before booking."
            ),
        }

    parsed_date, date_error = _parse_iso_date(appointment_date)
    if date_error or parsed_date is None:
        return {"ok": False, "error": date_error or "appointment_date is required in YYYY-MM-DD format."}

    try:
        payload = AppointmentBookRequest(
            patient_phone=normalized_phone,
            doctor_id=doctor_id,
            appointment_date=parsed_date,
            appointment_time=appointment_time,
        )
        appointment = await appointment_service.book_appointment(db, payload)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except DomainError as exc:
        return {"ok": False, "error": exc.detail}

    return {
        "ok": True,
        "message": "Appointment booked successfully.",
        "appointment": _serialize_appointment(appointment),
    }


async def cancel_appointment(
    db: AsyncSession,
    caller_phone: str,
    appointment_id: int | None = None,
    phone_confirmed: bool = False,
    cancellation_confirmed: bool = False,
) -> dict[str, Any]:
    """Find caller appointments by phone, enforce selection and confirmation, and cancel."""
    try:
        normalized_phone = validate_phone_string(caller_phone)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    if not phone_confirmed:
        return {
            "ok": False,
            "requires_phone_confirmation": True,
            "caller_phone": normalized_phone,
            "message": (
                f"Phone number {normalized_phone} is not confirmed yet. "
                f"Repeat '{normalized_phone}' to the caller and ask for confirmation first."
            ),
        }

    active_appointments = await appointment_service.list_appointments(
        db,
        patient_phone=normalized_phone,
        status=AppointmentStatus.BOOKED,
    )

    if not active_appointments:
        return {
            "ok": False,
            "error": f"No active booked appointments were found for phone number {normalized_phone}.",
        }

    target: Appointment | None = None
    if appointment_id is not None:
        target = next((item for item in active_appointments if item.id == appointment_id), None)
        if target is None:
            return {
                "ok": False,
                "error": (
                    f"No active appointment with ID {appointment_id} was found for "
                    f"phone number {normalized_phone}."
                ),
                "appointments": [_serialize_appointment(item) for item in active_appointments],
            }
    elif len(active_appointments) > 1:
        return {
            "ok": False,
            "requires_selection": True,
            "caller_phone": normalized_phone,
            "appointments": [_serialize_appointment(item) for item in active_appointments],
            "message": (
                f"Found {len(active_appointments)} active appointments for {normalized_phone}. "
                "Read the options to the caller and ask them to choose which appointment ID to cancel."
            ),
        }
    else:
        target = active_appointments[0]

    if not cancellation_confirmed:
        return {
            "ok": False,
            "requires_cancellation_confirmation": True,
            "selected_appointment": _serialize_appointment(target),
            "message": (
                f"Please ask the caller to confirm cancelling appointment #{target.id} with "
                f"{target.doctor.name} on {target.appointment_date.isoformat()} at {target.appointment_time}."
            ),
        }

    try:
        cancelled = await appointment_service.cancel_appointment(
            db,
            AppointmentCancelRequest(appointment_id=target.id),
        )
    except DomainError as exc:
        return {"ok": False, "error": exc.detail}

    return {
        "ok": True,
        "message": "Appointment cancelled and time slot released.",
        "cancelled_appointment": _serialize_appointment(cancelled),
    }


ToolHandler = Callable[..., Awaitable[dict[str, Any]]]

TOOL_REGISTRY: dict[str, ToolHandler] = {
    "check_doctor_availability": check_doctor_availability,
    "book_appointment": book_appointment,
    "cancel_appointment": cancel_appointment,
}


async def execute_tool_call(
    db: AsyncSession,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch a Gemini function call to the matching local async Python tool."""
    handler = TOOL_REGISTRY.get(name)
    if handler is None:
        return {"ok": False, "error": f"Unknown tool '{name}'."}

    try:
        return await handler(db, **arguments)
    except TypeError as exc:
        return {"ok": False, "error": f"Invalid arguments for '{name}': {exc}"}


GEMINI_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="check_doctor_availability",
            description=(
                "Query the SQLite database for available doctors and open appointment slots. "
                "Always call this before quoting any doctor schedule or availability."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "doctor_name": {
                        "type": "string",
                        "description": "Optional doctor name or partial name (e.g. 'Dr. Aarav Mehta').",
                    },
                    "speciality": {
                        "type": "string",
                        "description": "Optional medical speciality (e.g. 'Cardiology', 'Dermatology').",
                    },
                    "appointment_date": {
                        "type": "string",
                        "description": "Optional date filter in YYYY-MM-DD format.",
                    },
                },
            },
        ),
        types.FunctionDeclaration(
            name="book_appointment",
            description=(
                "Book an available appointment slot in SQLite. Only set phone_confirmed=true "
                "after repeating the complete phone number to the caller and receiving confirmation."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "caller_phone": {
                        "type": "string",
                        "description": "Caller's spoken phone number as a string (preserving leading zeros and '+').",
                    },
                    "doctor_id": {
                        "type": "integer",
                        "description": "Numeric ID of the selected doctor.",
                    },
                    "appointment_date": {
                        "type": "string",
                        "description": "Appointment date in YYYY-MM-DD format.",
                    },
                    "appointment_time": {
                        "type": "string",
                        "description": "Exact slot time string (e.g. '09:30 AM').",
                    },
                    "phone_confirmed": {
                        "type": "boolean",
                        "description": "Must be true only after the caller explicitly confirmed the repeated phone number.",
                    },
                },
                "required": [
                    "caller_phone",
                    "doctor_id",
                    "appointment_date",
                    "appointment_time",
                    "phone_confirmed",
                ],
            },
        ),
        types.FunctionDeclaration(
            name="cancel_appointment",
            description=(
                "Find and cancel a caller's appointment by phone number and optional appointment ID. "
                "Requires phone confirmation first, selection if multiple appointments exist, and "
                "explicit cancellation confirmation before executing."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "caller_phone": {
                        "type": "string",
                        "description": "Caller's spoken phone number as a string.",
                    },
                    "appointment_id": {
                        "type": "integer",
                        "description": "Optional appointment ID selected by the caller when multiple bookings exist.",
                    },
                    "phone_confirmed": {
                        "type": "boolean",
                        "description": "Must be true only after the caller confirmed their repeated phone number.",
                    },
                    "cancellation_confirmed": {
                        "type": "boolean",
                        "description": "Must be true only after the caller confirmed cancelling the selected appointment.",
                    },
                },
                "required": [
                    "caller_phone",
                    "phone_confirmed",
                    "cancellation_confirmed",
                ],
            },
        ),
    ]
)
