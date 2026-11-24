import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pipecat.services.llm_service import FunctionCallParams
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.database import create_engine_for_url, get_db, init_db
from app.main import create_app
from app.voice import register_voice_tools


class EndToEndWorkflowTests(unittest.IsolatedAsyncioTestCase):
    """Full end-to-end Booking and Cancellation workflow tests across Pipecat tools, SQLite, and REST APIs."""

    async def asyncSetUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_e2e.db"
        self.engine = create_engine_for_url(f"sqlite+aiosqlite:///{db_path.as_posix()}")
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        await init_db(target_engine=self.engine, session_factory=self.session_factory, seed=True)

        self.app: FastAPI = create_app()

        async def _override_get_db():
            async with self.session_factory() as session:
                yield session

        self.app.dependency_overrides[get_db] = _override_get_db

        self.tool_handlers: dict[str, object] = {}
        self.emitted_events: list[dict[str, object]] = []

        class _MockLLM:
            def __init__(self, target: dict[str, object]) -> None:
                self._target = target

            def register_function(self, name: str, handler: object) -> None:
                self._target[name] = handler

        class _MockWorker:
            def __init__(self, sink: list[dict[str, object]]) -> None:
                self._sink = sink

            async def queue_frame(self, frame: object) -> None:
                msg = getattr(frame, "message", None)
                if isinstance(msg, dict):
                    self._sink.append(msg)

        register_voice_tools(
            _MockLLM(self.tool_handlers),  # type: ignore[arg-type]
            self.session_factory,
            worker_getter=lambda: _MockWorker(self.emitted_events),  # type: ignore[arg-type, return-value]
        )

    async def asyncTearDown(self) -> None:
        self.app.dependency_overrides.clear()
        await self.engine.dispose()
        self._tmp_dir.cleanup()

    async def _invoke_voice_tool(
        self, name: str, arguments: dict[str, object]
    ) -> dict[str, object]:
        results: list[dict[str, object]] = []

        async def _callback(res: dict[str, object], **_: object) -> None:
            results.append(res)

        handler = self.tool_handlers[name]
        params = FunctionCallParams(
            function_name=name,
            tool_call_id=f"call_{name}",
            arguments=arguments,
            llm=SimpleNamespace(),  # type: ignore[arg-type]
            pipeline_worker=SimpleNamespace(),  # type: ignore[arg-type]
            context=SimpleNamespace(),  # type: ignore[arg-type]
            result_callback=_callback,  # type: ignore[arg-type]
        )
        await handler(params)  # type: ignore[misc]
        return results[0]

    async def test_complete_booking_and_cancellation_workflows_update_dashboard(self) -> None:
        transport = ASGITransport(app=self.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Initial dashboard state from SQLite
            initial_stats = (await client.get("/api/dashboard/stats")).json()
            initial_available = initial_stats["available_slots"]
            self.assertEqual(initial_stats["total_doctors"], 6)
            self.assertEqual(initial_stats["active_appointments"], 0)

            # --- WORKFLOW 1: BOOKING ---
            # 1. Caller requests Cardiology -> check_doctor_availability queries SQLite
            cardio_avail = await self._invoke_voice_tool(
                "check_doctor_availability",
                {"speciality": "Cardiology"},
            )
            self.assertTrue(cardio_avail["ok"])
            chosen_slot = cardio_avail["available_slots"][0]  # type: ignore[index]

            # 2. Caller gives phone number, unconfirmed booking must wait for confirmation
            caller_phone = "07911123456"
            pending_confirm = await self._invoke_voice_tool(
                "book_appointment",
                {
                    "caller_phone": caller_phone,
                    "doctor_id": chosen_slot["doctor_id"],
                    "appointment_date": chosen_slot["appointment_date"],
                    "appointment_time": chosen_slot["appointment_time"],
                    "phone_confirmed": False,
                },
            )
            self.assertFalse(pending_confirm["ok"])
            self.assertTrue(pending_confirm["requires_phone_confirmation"])

            # 3. Caller confirms phone number -> appointment saved to SQLite
            booked = await self._invoke_voice_tool(
                "book_appointment",
                {
                    "caller_phone": caller_phone,
                    "doctor_id": chosen_slot["doctor_id"],
                    "appointment_date": chosen_slot["appointment_date"],
                    "appointment_time": chosen_slot["appointment_time"],
                    "phone_confirmed": True,
                },
            )
            self.assertTrue(booked["ok"])
            cardio_appt_id = booked["appointment"]["appointment_id"]  # type: ignore[index]
            self.assertEqual(self.emitted_events[-1]["action"], "booked")

            # 4. Dashboard APIs reflect the booked appointment & updated slot availability immediately
            stats_after_book = (await client.get("/api/dashboard/stats")).json()
            self.assertEqual(stats_after_book["active_appointments"], 1)
            self.assertEqual(stats_after_book["booked_slots"], 1)
            self.assertEqual(stats_after_book["available_slots"], initial_available - 1)

            avail_after_book = (
                await client.get(
                    "/api/availability",
                    params={"doctor_id": chosen_slot["doctor_id"]},
                )
            ).json()
            self.assertFalse(any(s["id"] == chosen_slot["slot_id"] for s in avail_after_book))

            appts_after_book = (await client.get("/api/appointments")).json()
            self.assertEqual(len(appts_after_book), 1)
            self.assertEqual(appts_after_book[0]["patient_phone"], caller_phone)

            # Book a second appointment (Dermatology) so caller has multiple bookings for cancellation test
            derm_avail = await self._invoke_voice_tool(
                "check_doctor_availability",
                {"speciality": "Dermatology"},
            )
            derm_slot = derm_avail["available_slots"][0]  # type: ignore[index]
            second_book = await self._invoke_voice_tool(
                "book_appointment",
                {
                    "caller_phone": caller_phone,
                    "doctor_id": derm_slot["doctor_id"],
                    "appointment_date": derm_slot["appointment_date"],
                    "appointment_time": derm_slot["appointment_time"],
                    "phone_confirmed": True,
                },
            )
            self.assertTrue(second_book["ok"])

            # --- WORKFLOW 2: CANCELLATION ---
            # 1. Caller asks to cancel with confirmed phone, no appointment selected -> asks selection
            select_prompt = await self._invoke_voice_tool(
                "cancel_appointment",
                {
                    "caller_phone": caller_phone,
                    "phone_confirmed": True,
                    "cancellation_confirmed": False,
                },
            )
            self.assertFalse(select_prompt["ok"])
            self.assertTrue(select_prompt["requires_selection"])
            self.assertEqual(len(select_prompt["appointments"]), 2)

            # 2. Caller selects Cardiology appointment -> asks explicit cancellation confirmation
            confirm_prompt = await self._invoke_voice_tool(
                "cancel_appointment",
                {
                    "caller_phone": caller_phone,
                    "appointment_id": cardio_appt_id,
                    "phone_confirmed": True,
                    "cancellation_confirmed": False,
                },
            )
            self.assertFalse(confirm_prompt["ok"])
            self.assertTrue(confirm_prompt["requires_cancellation_confirmation"])

            # 3. Caller confirms cancellation -> cancelled in SQLite, slot released, event emitted
            cancelled = await self._invoke_voice_tool(
                "cancel_appointment",
                {
                    "caller_phone": caller_phone,
                    "appointment_id": cardio_appt_id,
                    "phone_confirmed": True,
                    "cancellation_confirmed": True,
                },
            )
            self.assertTrue(cancelled["ok"])
            self.assertEqual(self.emitted_events[-1]["action"], "cancelled")

            # 4. Dashboard APIs reflect cancellation, released slot, and updated stats
            stats_after_cancel = (await client.get("/api/dashboard/stats")).json()
            self.assertEqual(stats_after_cancel["active_appointments"], 1)
            self.assertEqual(stats_after_cancel["cancelled_appointments"], 1)
            self.assertEqual(stats_after_cancel["available_slots"], initial_available - 1)

            avail_after_cancel = (
                await client.get(
                    "/api/availability",
                    params={"doctor_id": chosen_slot["doctor_id"]},
                )
            ).json()
            self.assertTrue(any(s["id"] == chosen_slot["slot_id"] for s in avail_after_cancel))


if __name__ == "__main__":
    unittest.main()
