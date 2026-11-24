import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import (
    ASSISTANT_SYSTEM_PROMPT,
    GEMINI_TOOLS,
    GeminiAppointmentAssistant,
    GeminiConfigurationError,
    book_appointment,
    cancel_appointment,
    check_doctor_availability,
)
from app.core.config import Settings
from app.db.database import create_engine_for_url, init_db
from app.models.domain import AppointmentStatus, Slot, SlotStatus


class _FakeAsyncModels:
    """Scripted fake for `client.aio.models` that exercises the Gemini tool loop."""

    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    async def generate_content(
        self,
        *,
        model: str,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> object:
        self.calls.append({"model": model, "contents": list(contents), "config": config})
        return self._responses.pop(0)


class _FakeGenAIClient:
    def __init__(self, responses: list[object]) -> None:
        self.models_stub = _FakeAsyncModels(responses)
        self.aio = SimpleNamespace(models=self.models_stub)


def _make_function_call_response(name: str, args: dict[str, object]) -> object:
    part = types.Part.from_function_call(name=name, args=args)
    content = types.Content(role="model", parts=[part])
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(
        candidates=[candidate],
        function_calls=[part.function_call],
        text=None,
    )


def _make_text_response(text: str) -> object:
    part = types.Part.from_text(text=text)
    content = types.Content(role="model", parts=[part])
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(
        candidates=[candidate],
        function_calls=[],
        text=text,
    )


class AIToolsAndGeminiTests(unittest.IsolatedAsyncioTestCase):
    """Independent tests for all 3 AI functions, rules, and Gemini function-calling loop."""

    async def asyncSetUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_ai.db"
        self.engine = create_engine_for_url(f"sqlite+aiosqlite:///{db_path.as_posix()}")
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        await init_db(target_engine=self.engine, session_factory=self.session_factory, seed=True)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp_dir.cleanup()

    async def test_function_1_check_doctor_availability(self) -> None:
        async with self.session_factory() as db:
            res = await check_doctor_availability(db, speciality="Cardiology")
            self.assertTrue(res["ok"])
            self.assertGreater(res["count"], 0)
            self.assertEqual(len(res["doctors"]), 1)
            self.assertEqual(res["doctors"][0]["speciality"], "Cardiology")
            self.assertTrue(
                all(slot["speciality"] == "Cardiology" for slot in res["available_slots"])
            )

            first_slot = res["available_slots"][0]
            filtered = await check_doctor_availability(
                db,
                doctor_name="Aarav",
                appointment_date=first_slot["appointment_date"],
            )
            self.assertTrue(filtered["ok"])
            self.assertGreater(filtered["count"], 0)
            self.assertTrue(
                all(
                    slot["appointment_date"] == first_slot["appointment_date"]
                    for slot in filtered["available_slots"]
                )
            )

            bad_date = await check_doctor_availability(db, appointment_date="25-11-2026")
            self.assertFalse(bad_date["ok"])

            none_found = await check_doctor_availability(db, speciality="NonExistent")
            self.assertTrue(none_found["ok"])
            self.assertEqual(none_found["count"], 0)
            self.assertEqual(none_found["available_slots"], [])

    async def test_function_2_book_appointment_requires_confirmation_and_persists(self) -> None:
        async with self.session_factory() as db:
            avail = await check_doctor_availability(db, speciality="Dermatology")
            slot = avail["available_slots"][0]

            # Must not book before phone number confirmation
            unconfirmed = await book_appointment(
                db,
                caller_phone="07911123456",
                doctor_id=slot["doctor_id"],
                appointment_date=slot["appointment_date"],
                appointment_time=slot["appointment_time"],
                phone_confirmed=False,
            )
            self.assertFalse(unconfirmed["ok"])
            self.assertTrue(unconfirmed["requires_phone_confirmation"])

            # Verify slot is still available in SQLite
            db_slot = await db.scalar(select(Slot).where(Slot.id == slot["slot_id"]))
            assert db_slot is not None
            self.assertEqual(db_slot.status, SlotStatus.AVAILABLE.value)

            # Confirmed phone books the appointment
            confirmed = await book_appointment(
                db,
                caller_phone="07911123456",
                doctor_id=slot["doctor_id"],
                appointment_date=slot["appointment_date"],
                appointment_time=slot["appointment_time"],
                phone_confirmed=True,
            )
            self.assertTrue(confirmed["ok"])
            self.assertEqual(confirmed["appointment"]["patient_phone"], "07911123456")
            self.assertEqual(confirmed["appointment"]["status"], AppointmentStatus.BOOKED.value)

            # Re-booking same slot fails gracefully
            double_attempt = await book_appointment(
                db,
                caller_phone="+919876543210",
                doctor_id=slot["doctor_id"],
                appointment_date=slot["appointment_date"],
                appointment_time=slot["appointment_time"],
                phone_confirmed=True,
            )
            self.assertFalse(double_attempt["ok"])

    async def test_function_3_cancel_appointment_selection_and_confirmation(self) -> None:
        async with self.session_factory() as db:
            neuro_slot = (await check_doctor_availability(db, speciality="Neurology"))[
                "available_slots"
            ][0]
            ortho_slot = (await check_doctor_availability(db, speciality="Orthopaedics"))[
                "available_slots"
            ][0]

            phone = "+919876543210"
            b1 = await book_appointment(
                db,
                caller_phone=phone,
                doctor_id=neuro_slot["doctor_id"],
                appointment_date=neuro_slot["appointment_date"],
                appointment_time=neuro_slot["appointment_time"],
                phone_confirmed=True,
            )
            b2 = await book_appointment(
                db,
                caller_phone=phone,
                doctor_id=ortho_slot["doctor_id"],
                appointment_date=ortho_slot["appointment_date"],
                appointment_time=ortho_slot["appointment_time"],
                phone_confirmed=True,
            )
            self.assertTrue(b1["ok"] and b2["ok"])
            appt1_id = b1["appointment"]["appointment_id"]

            # 1. Requires phone confirmation first
            no_phone_conf = await cancel_appointment(
                db, caller_phone=phone, phone_confirmed=False, cancellation_confirmed=False
            )
            self.assertFalse(no_phone_conf["ok"])
            self.assertTrue(no_phone_conf["requires_phone_confirmation"])

            # 2. Multiple appointments exist -> asks caller to select appointment_id
            multi = await cancel_appointment(
                db, caller_phone=phone, phone_confirmed=True, cancellation_confirmed=False
            )
            self.assertFalse(multi["ok"])
            self.assertTrue(multi["requires_selection"])
            self.assertEqual(len(multi["appointments"]), 2)

            # 3. Specific appointment selected -> still requires cancellation confirmation
            need_confirm = await cancel_appointment(
                db,
                caller_phone=phone,
                appointment_id=appt1_id,
                phone_confirmed=True,
                cancellation_confirmed=False,
            )
            self.assertFalse(need_confirm["ok"])
            self.assertTrue(need_confirm["requires_cancellation_confirmation"])
            self.assertEqual(need_confirm["selected_appointment"]["appointment_id"], appt1_id)

            # 4. Confirmed cancellation cancels appointment and releases slot in SQLite
            cancelled = await cancel_appointment(
                db,
                caller_phone=phone,
                appointment_id=appt1_id,
                phone_confirmed=True,
                cancellation_confirmed=True,
            )
            self.assertTrue(cancelled["ok"])
            self.assertEqual(
                cancelled["cancelled_appointment"]["status"],
                AppointmentStatus.CANCELLED.value,
            )

            released_slot = await db.scalar(
                select(Slot).where(Slot.id == neuro_slot["slot_id"])
            )
            assert released_slot is not None
            self.assertEqual(released_slot.status, SlotStatus.AVAILABLE.value)

    async def test_gemini_config_prompt_tools_and_function_calling_loop(self) -> None:
        # Missing API key raises explicit configuration error
        with self.assertRaises(GeminiConfigurationError):
            GeminiAppointmentAssistant(
                settings=Settings(gemini_api_key="your_google_gemini_api_key_here")
            )

        # Prompt & tool declaration sanity checks
        self.assertIn("NEVER assume", ASSISTANT_SYSTEM_PROMPT)
        declared_names = {fn.name for fn in GEMINI_TOOLS.function_declarations or []}
        self.assertEqual(
            declared_names,
            {"check_doctor_availability", "book_appointment", "cancel_appointment"},
        )

        async with self.session_factory() as db:
            avail = await check_doctor_availability(db, speciality="Paediatrics")
            slot = avail["available_slots"][0]

            fake_client = _FakeGenAIClient(
                responses=[
                    _make_function_call_response(
                        "check_doctor_availability",
                        {"speciality": "Paediatrics"},
                    ),
                    _make_function_call_response(
                        "book_appointment",
                        {
                            "caller_phone": "07911123456",
                            "doctor_id": slot["doctor_id"],
                            "appointment_date": slot["appointment_date"],
                            "appointment_time": slot["appointment_time"],
                            "phone_confirmed": True,
                        },
                    ),
                    _make_text_response(
                        f"Your appointment with {slot['doctor_name']} on "
                        f"{slot['appointment_date']} at {slot['appointment_time']} is confirmed."
                    ),
                ]
            )

            assistant = GeminiAppointmentAssistant(
                settings=Settings(gemini_api_key="test-key", gemini_model="gemini-2.5-flash"),
                client=fake_client,
            )
            result = await assistant.process_turn(
                db,
                "Please book the Paediatrics slot for my confirmed number 07911123456.",
            )

            self.assertEqual(len(result.tool_calls), 2)
            self.assertEqual(result.tool_calls[0].name, "check_doctor_availability")
            self.assertTrue(result.tool_calls[0].result["ok"])
            self.assertEqual(result.tool_calls[1].name, "book_appointment")
            self.assertTrue(result.tool_calls[1].result["ok"])
            self.assertIn("confirmed", result.reply_text.lower())

            # Verify slot was genuinely mutated in SQLite by the Gemini tool call loop
            db_slot = await db.scalar(select(Slot).where(Slot.id == slot["slot_id"]))
            assert db_slot is not None
            self.assertEqual(db_slot.status, SlotStatus.BOOKED.value)


if __name__ == "__main__":
    unittest.main()
