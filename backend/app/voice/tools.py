"""Pipecat function tool schemas and handlers connected to the SQLite service layer."""

from collections.abc import Callable
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
from pipecat.adapters.llm.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import OutputTransportMessageUrgentFrame
from pipecat.pipeline.worker import PipelineWorker
from pipecat.services.llm_service import FunctionCallParams, LLMService

from app.ai.tools import (
    book_appointment,
    cancel_appointment,
    check_doctor_availability,
)


def build_pipecat_tools_schema() -> ToolsSchema:
    """Build Pipecat 1.17 ToolsSchema declaring the three clinic appointment functions."""
    check_availability_fn = FunctionSchema(
        name="check_doctor_availability",
        description=(
            "Query SQLite for matching doctors and available appointment slots. "
            "Always call this before quoting any doctor schedule or availability."
        ),
        properties={
            "doctor_name": {
                "type": "string",
                "description": "Optional doctor name or partial name (e.g. 'Dr. Aarav Mehta').",
            },
            "speciality": {
                "type": "string",
                "description": "Optional speciality filter (e.g. 'Cardiology', 'Dermatology').",
            },
            "appointment_date": {
                "type": "string",
                "description": "Optional date filter in YYYY-MM-DD format.",
            },
        },
        required=[],
    )

    book_appointment_fn = FunctionSchema(
        name="book_appointment",
        description=(
            "Book an available appointment slot in SQLite. Only set phone_confirmed=true "
            "after repeating the caller's full phone number and receiving explicit confirmation."
        ),
        properties={
            "caller_phone": {
                "type": "string",
                "description": "Caller's spoken phone number as a string preserving leading zeros and '+'.",
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
                "description": "True only after the caller explicitly confirmed the repeated phone number.",
            },
        },
        required=[
            "caller_phone",
            "doctor_id",
            "appointment_date",
            "appointment_time",
            "phone_confirmed",
        ],
    )

    cancel_appointment_fn = FunctionSchema(
        name="cancel_appointment",
        description=(
            "Find and cancel an active appointment using the caller's spoken phone number "
            "and optional appointment ID. Requires phone confirmation, selection if multiple "
            "appointments exist, and explicit cancellation confirmation."
        ),
        properties={
            "caller_phone": {
                "type": "string",
                "description": "Caller's spoken phone number as a string.",
            },
            "appointment_id": {
                "type": "integer",
                "description": "Optional appointment ID when selecting from multiple active bookings.",
            },
            "phone_confirmed": {
                "type": "boolean",
                "description": "True only after the caller confirmed their repeated phone number.",
            },
            "cancellation_confirmed": {
                "type": "boolean",
                "description": "True only after the caller confirmed cancelling the chosen appointment.",
            },
        },
        required=[
            "caller_phone",
            "phone_confirmed",
            "cancellation_confirmed",
        ],
    )

    return ToolsSchema(
        standard_tools=[
            check_availability_fn,
            book_appointment_fn,
            cancel_appointment_fn,
        ]
    )


def register_voice_tools(
    llm: LLMService,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    worker_getter: Callable[[], PipelineWorker | None] | None = None,
) -> None:
    """Register the three clinic tool handlers on a Pipecat LLMService."""

    async def _emit_appointment_event(action: str, payload: dict[str, Any]) -> None:
        if worker_getter is None:
            return
        worker = worker_getter()
        if worker is None:
            return
        await worker.queue_frame(
            OutputTransportMessageUrgentFrame(
                message={
                    "type": "appointment_event",
                    "action": action,
                    "appointment": payload,
                }
            )
        )

    async def handle_check_availability(params: FunctionCallParams) -> None:
        args = dict(params.arguments or {})
        try:
            async with session_factory() as db:
                result = await check_doctor_availability(
                    db,
                    doctor_name=args.get("doctor_name"),
                    speciality=args.get("speciality"),
                    appointment_date=args.get("appointment_date"),
                )
        except Exception as exc:
            logger.exception("Error executing check_doctor_availability tool")
            result = {"ok": False, "error": f"Database query failed: {exc}"}
        await params.result_callback(result)

    async def handle_book_appointment(params: FunctionCallParams) -> None:
        args = dict(params.arguments or {})
        try:
            async with session_factory() as db:
                result = await book_appointment(
                    db,
                    caller_phone=str(args.get("caller_phone", "")),
                    doctor_id=int(args["doctor_id"]) if args.get("doctor_id") is not None else 0,
                    appointment_date=str(args.get("appointment_date", "")),
                    appointment_time=str(args.get("appointment_time", "")),
                    phone_confirmed=bool(args.get("phone_confirmed", False)),
                )
            if result.get("ok") and "appointment" in result:
                await _emit_appointment_event("booked", result["appointment"])
        except Exception as exc:
            logger.exception("Error executing book_appointment tool")
            result = {"ok": False, "error": f"Booking failed: {exc}"}
        await params.result_callback(result)

    async def handle_cancel_appointment(params: FunctionCallParams) -> None:
        args = dict(params.arguments or {})
        raw_appt_id = args.get("appointment_id")
        appt_id = int(raw_appt_id) if raw_appt_id is not None else None
        try:
            async with session_factory() as db:
                result = await cancel_appointment(
                    db,
                    caller_phone=str(args.get("caller_phone", "")),
                    appointment_id=appt_id,
                    phone_confirmed=bool(args.get("phone_confirmed", False)),
                    cancellation_confirmed=bool(args.get("cancellation_confirmed", False)),
                )
            if result.get("ok") and "cancelled_appointment" in result:
                await _emit_appointment_event("cancelled", result["cancelled_appointment"])
        except Exception as exc:
            logger.exception("Error executing cancel_appointment tool")
            result = {"ok": False, "error": f"Cancellation failed: {exc}"}
        await params.result_callback(result)

    llm.register_function("check_doctor_availability", handle_check_availability)
    llm.register_function("book_appointment", handle_book_appointment)
    llm.register_function("cancel_appointment", handle_cancel_appointment)
