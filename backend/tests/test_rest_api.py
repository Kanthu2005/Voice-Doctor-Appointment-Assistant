import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.database import create_engine_for_url, get_db, init_db
from app.main import create_app


class RestApiTests(unittest.IsolatedAsyncioTestCase):
    """Comprehensive verification of all Step 3 FastAPI REST endpoints."""

    async def asyncSetUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_api.db"
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

    async def test_doctors_and_availability_endpoints(self) -> None:
        transport = ASGITransport(app=self.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # List all doctors
            all_docs = await client.get("/api/doctors")
            self.assertEqual(all_docs.status_code, 200)
            self.assertEqual(len(all_docs.json()), 6)

            # Filter doctors by speciality
            cardio_docs = await client.get("/api/doctors", params={"speciality": "Cardiology"})
            self.assertEqual(cardio_docs.status_code, 200)
            self.assertEqual(len(cardio_docs.json()), 1)
            doctor_id = cardio_docs.json()[0]["id"]

            # Get doctor by ID
            doc_detail = await client.get(f"/api/doctors/{doctor_id}")
            self.assertEqual(doc_detail.status_code, 200)
            detail_json = doc_detail.json()
            self.assertEqual(detail_json["speciality"], "Cardiology")
            self.assertGreater(len(detail_json["slots"]), 0)

            # Nonexistent doctor returns 404
            missing_doc = await client.get("/api/doctors/99999")
            self.assertEqual(missing_doc.status_code, 404)

            # Filter availability by doctor_id and appointment_date
            first_date = detail_json["slots"][0]["appointment_date"]
            avail = await client.get(
                "/api/availability",
                params={"doctor_id": doctor_id, "appointment_date": first_date},
            )
            self.assertEqual(avail.status_code, 200)
            avail_slots = avail.json()
            self.assertGreater(len(avail_slots), 0)
            self.assertTrue(all(s["doctor_id"] == doctor_id for s in avail_slots))
            self.assertTrue(all(s["appointment_date"] == first_date for s in avail_slots))

    async def test_appointments_booking_duplicate_prevention_cancel_and_stats(self) -> None:
        transport = ASGITransport(app=self.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            stats_before = (await client.get("/api/dashboard/stats")).json()
            self.assertEqual(stats_before["total_doctors"], 6)
            self.assertEqual(stats_before["active_appointments"], 0)
            initial_available = stats_before["available_slots"]

            # Pick two slots for Doctor 1 on the same date, and one slot for Doctor 2
            doc1_avail = (await client.get("/api/availability", params={"doctor_id": 1})).json()
            doc2_avail = (await client.get("/api/availability", params={"doctor_id": 2})).json()
            slot1 = doc1_avail[0]
            slot2_same_day = next(
                s
                for s in doc1_avail
                if s["id"] != slot1["id"] and s["appointment_date"] == slot1["appointment_date"]
            )
            slot_doc2 = doc2_avail[0]

            # 1. Invalid numeric phone rejected with 422
            bad_phone = await client.post(
                "/api/appointments",
                json={"patient_phone": 9876543210, "slot_id": slot1["id"]},
            )
            self.assertEqual(bad_phone.status_code, 422)

            # 2. Book slot1 via composite (doctor_id, date, time)
            book_resp = await client.post(
                "/api/appointments",
                json={
                    "patient_phone": "+919876543210",
                    "doctor_id": slot1["doctor_id"],
                    "appointment_date": slot1["appointment_date"],
                    "appointment_time": slot1["appointment_time"],
                },
            )
            self.assertEqual(book_resp.status_code, 201)
            appt_id = book_resp.json()["appointment"]["id"]

            # 3. Another caller cannot double-book slot1 (409)
            double_book = await client.post(
                "/api/appointments",
                json={"patient_phone": "07911123456", "slot_id": slot1["id"]},
            )
            self.assertEqual(double_book.status_code, 409)

            # 4. Same caller cannot create duplicate booking with same doctor on same date (409)
            dup_same_doc = await client.post(
                "/api/appointments",
                json={"patient_phone": "+919876543210", "slot_id": slot2_same_day["id"]},
            )
            self.assertEqual(dup_same_doc.status_code, 409)

            # 5. Book slot_doc2 for second caller
            book2 = await client.post(
                "/api/appointments",
                json={"patient_phone": "07911123456", "slot_id": slot_doc2["id"]},
            )
            self.assertEqual(book2.status_code, 201)

            # 6. List appointments filtered by phone
            filtered_appts = await client.get(
                "/api/appointments",
                params={"patient_phone": "+919876543210"},
            )
            self.assertEqual(filtered_appts.status_code, 200)
            self.assertEqual(len(filtered_appts.json()), 1)

            # 7. Dashboard stats reflect 2 active bookings
            stats_mid = (await client.get("/api/dashboard/stats")).json()
            self.assertEqual(stats_mid["active_appointments"], 2)
            self.assertEqual(stats_mid["booked_slots"], 2)
            self.assertEqual(stats_mid["available_slots"], initial_available - 2)

            # 8. Cancel first appointment -> releases slot1 & updates stats
            cancel_resp = await client.post(f"/api/appointments/{appt_id}/cancel")
            self.assertEqual(cancel_resp.status_code, 200)
            self.assertEqual(cancel_resp.json()["appointment"]["status"], "cancelled")

            # Re-cancelling returns 409
            recancel_resp = await client.post(f"/api/appointments/{appt_id}/cancel")
            self.assertEqual(recancel_resp.status_code, 409)

            # Cancelling missing ID returns 404
            missing_cancel = await client.post("/api/appointments/99999/cancel")
            self.assertEqual(missing_cancel.status_code, 404)

            stats_after = (await client.get("/api/dashboard/stats")).json()
            self.assertEqual(stats_after["active_appointments"], 1)
            self.assertEqual(stats_after["cancelled_appointments"], 1)
            self.assertEqual(stats_after["available_slots"], initial_available - 1)

    async def test_cors_and_swagger_openapi_docs(self) -> None:
        transport = ASGITransport(app=self.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            cors_resp = await client.options(
                "/api/doctors",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
            self.assertEqual(cors_resp.status_code, 200)
            self.assertEqual(
                cors_resp.headers.get("access-control-allow-origin"),
                "http://localhost:5173",
            )

            docs_resp = await client.get("/docs")
            self.assertEqual(docs_resp.status_code, 200)

            openapi_resp = await client.get("/openapi.json")
            self.assertEqual(openapi_resp.status_code, 200)
            paths = openapi_resp.json()["paths"]
            expected_paths = {
                "/api/health",
                "/api/doctors",
                "/api/doctors/{doctor_id}",
                "/api/availability",
                "/api/appointments",
                "/api/appointments/{appointment_id}/cancel",
                "/api/dashboard/stats",
            }
            self.assertTrue(expected_paths.issubset(set(paths.keys())))


if __name__ == "__main__":
    unittest.main()
