import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AppointmentAlreadyCancelledError,
    AppointmentNotFoundError,
    DoctorNotFoundError,
    SlotAlreadyBookedError,
)
from app.db.database import create_engine_for_url, get_db, init_db
from app.main import create_app
from app.models.domain import Appointment, AppointmentStatus, Doctor, Slot, SlotStatus
from app.schemas.appointment import AppointmentBookRequest, AppointmentCancelRequest
from app.services import appointment_service, doctor_service


class DatabaseAndServiceTests(unittest.IsolatedAsyncioTestCase):
    """End-to-end verification of SQLite schema, seed data, relationships, services, and routes."""

    async def asyncSetUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_appointments.db"
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

    async def asyncTearDown(self) -> None:
        self.app.dependency_overrides.clear()
        await self.engine.dispose()
        self._tmp_dir.cleanup()

    async def test_database_tables_and_foreign_keys_created(self) -> None:
        async with self.engine.connect() as conn:
            table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            fk_enabled = (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one()

        self.assertIn("doctors", table_names)
        self.assertIn("slots", table_names)
        self.assertIn("appointments", table_names)
        self.assertEqual(fk_enabled, 1)

    async def test_seed_doctors_and_idempotency(self) -> None:
        async with self.session_factory() as session:
            doctors = await doctor_service.list_doctors(session, include_slots=True)
            self.assertGreaterEqual(len(doctors), 6)

            specialities = {doc.speciality for doc in doctors}
            expected = {
                "Cardiology",
                "Dermatology",
                "Neurology",
                "Orthopaedics",
                "General Medicine",
                "Paediatrics",
            }
            self.assertTrue(expected.issubset(specialities))

            for doc in doctors:
                self.assertGreater(len(doc.slots), 0)
                for slot in doc.slots:
                    self.assertEqual(slot.status, SlotStatus.AVAILABLE.value)

        # Calling init_db again must not duplicate doctors or slots
        await init_db(target_engine=self.engine, session_factory=self.session_factory, seed=True)
        async with self.session_factory() as session:
            doctors_after = await doctor_service.list_doctors(session)
            self.assertEqual(len(doctors_after), len(doctors))

    async def test_relationships_between_doctor_slot_and_appointment(self) -> None:
        async with self.session_factory() as session:
            slots = await doctor_service.get_doctor_availability(session, speciality="Cardiology")
            self.assertGreater(len(slots), 0)
            target_slot = slots[0]

            booked = await appointment_service.book_appointment(
                session,
                AppointmentBookRequest(
                    patient_phone="07911123456",
                    slot_id=target_slot.id,
                ),
            )
            self.assertEqual(booked.patient_phone, "07911123456")

            doctor = await session.scalar(
                select(Doctor)
                .options(selectinload(Doctor.slots), selectinload(Doctor.appointments))
                .where(Doctor.id == target_slot.doctor_id)
            )
            self.assertIsNotNone(doctor)
            assert doctor is not None
            self.assertTrue(any(a.id == booked.id for a in doctor.appointments))
            self.assertTrue(any(s.id == target_slot.id and s.status == "booked" for s in doctor.slots))

            loaded_appt = await session.scalar(
                select(Appointment)
                .options(selectinload(Appointment.doctor), selectinload(Appointment.slot))
                .where(Appointment.id == booked.id)
            )
            assert loaded_appt is not None
            self.assertEqual(loaded_appt.doctor.id, doctor.id)
            self.assertEqual(loaded_appt.slot.id, target_slot.id)
            self.assertEqual(loaded_appt.slot.status, SlotStatus.BOOKED.value)

    async def test_prevent_double_booking_and_release_on_cancel(self) -> None:
        async with self.session_factory() as session:
            slots = await doctor_service.get_doctor_availability(session, speciality="Dermatology")
            slot = slots[0]

            first_booking = await appointment_service.book_appointment(
                session,
                AppointmentBookRequest(
                    patient_phone="+919876543210",
                    slot_id=slot.id,
                ),
            )
            self.assertEqual(first_booking.status, AppointmentStatus.BOOKED.value)
            self.assertEqual(first_booking.patient_phone, "+919876543210")

            # Attempting to book the same slot by slot_id must fail
            with self.assertRaises(SlotAlreadyBookedError):
                await appointment_service.book_appointment(
                    session,
                    AppointmentBookRequest(
                        patient_phone="+14155550199",
                        slot_id=slot.id,
                    ),
                )

            # Attempting to book the same slot by (doctor_id, date, time) must also fail
            with self.assertRaises(SlotAlreadyBookedError):
                await appointment_service.book_appointment(
                    session,
                    AppointmentBookRequest(
                        patient_phone="+14155550199",
                        doctor_id=slot.doctor_id,
                        appointment_date=slot.appointment_date,
                        appointment_time=slot.appointment_time,
                    ),
                )

            # Cancelling by phone number releases the slot
            cancelled = await appointment_service.cancel_appointment(
                session,
                AppointmentCancelRequest(patient_phone="+919876543210"),
            )
            self.assertEqual(cancelled.status, AppointmentStatus.CANCELLED.value)

            refreshed_slot = await session.scalar(select(Slot).where(Slot.id == slot.id))
            assert refreshed_slot is not None
            self.assertEqual(refreshed_slot.status, SlotStatus.AVAILABLE.value)

            # Double-cancelling the same appointment ID must fail
            with self.assertRaises(AppointmentAlreadyCancelledError):
                await appointment_service.cancel_appointment(
                    session,
                    AppointmentCancelRequest(appointment_id=first_booking.id),
                )

            # Released slot can now be booked by a new patient
            rebooked = await appointment_service.book_appointment(
                session,
                AppointmentBookRequest(
                    patient_phone="00442079460958",
                    slot_id=slot.id,
                ),
            )
            self.assertEqual(rebooked.status, AppointmentStatus.BOOKED.value)
            self.assertEqual(rebooked.patient_phone, "00442079460958")

    async def test_phone_validation_and_not_found_errors(self) -> None:
        # Formatted phone numbers canonicalize consistently while preserving '+' and leading zeros
        req_spaced = AppointmentBookRequest(patient_phone="+91 98765-43210", slot_id=1)
        self.assertEqual(req_spaced.patient_phone, "+919876543210")

        req_zero = AppointmentBookRequest(patient_phone="079 1112 3456", slot_id=1)
        self.assertEqual(req_zero.patient_phone, "07911123456")

        # Numeric input must be rejected so leading zeros are never lost
        with self.assertRaises(ValidationError):
            AppointmentBookRequest(patient_phone=7911123456, slot_id=1)  # type: ignore[arg-type]

        with self.assertRaises(ValidationError):
            AppointmentBookRequest(patient_phone="123", slot_id=1)

        async with self.session_factory() as session:
            with self.assertRaises(DoctorNotFoundError):
                await doctor_service.get_doctor_by_id(session, 9999)

            with self.assertRaises(AppointmentNotFoundError):
                await appointment_service.cancel_appointment(
                    session,
                    AppointmentCancelRequest(patient_phone="+910000000000"),
                )

    async def test_api_routes_end_to_end(self) -> None:
        transport = ASGITransport(app=self.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            health_resp = await client.get("/api/health")
            self.assertEqual(health_resp.status_code, 200)
            self.assertEqual(health_resp.json()["database"], "connected")

            doctors_resp = await client.get("/api/doctors")
            self.assertEqual(doctors_resp.status_code, 200)
            doctors = doctors_resp.json()
            self.assertEqual(len(doctors), 6)

            avail_resp = await client.get("/api/availability", params={"speciality": "Neurology"})
            self.assertEqual(avail_resp.status_code, 200)
            slots = avail_resp.json()
            self.assertGreater(len(slots), 0)
            slot_id = slots[0]["id"]

            # Book via API preserving leading zero phone number
            book_resp = await client.post(
                "/api/appointments",
                json={"patient_phone": "07911123456", "slot_id": slot_id},
            )
            self.assertEqual(book_resp.status_code, 201)
            body = book_resp.json()
            self.assertEqual(body["message"], "Appointment booked successfully.")
            booked = body["appointment"]
            self.assertEqual(booked["patient_phone"], "07911123456")
            self.assertEqual(booked["status"], "booked")

            # Duplicate booking returns 409 Conflict
            dup_resp = await client.post(
                "/api/appointments",
                json={"patient_phone": "+919988776655", "slot_id": slot_id},
            )
            self.assertEqual(dup_resp.status_code, 409)

            # Cancel via API releases the slot
            cancel_resp = await client.post(
                f"/api/appointments/{booked['id']}/cancel",
            )
            self.assertEqual(cancel_resp.status_code, 200)
            self.assertEqual(cancel_resp.json()["appointment"]["status"], "cancelled")

            # Slot is available again in /api/availability
            avail_after = await client.get("/api/availability", params={"speciality": "Neurology"})
            self.assertTrue(any(s["id"] == slot_id for s in avail_after.json()))


if __name__ == "__main__":
    unittest.main()
