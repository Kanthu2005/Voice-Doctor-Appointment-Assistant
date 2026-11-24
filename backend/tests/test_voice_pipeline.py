import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipecat.adapters.llm.services.gemini_adapter import GeminiLLMAdapter
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    ErrorFrame,
    InputAudioRawFrame,
    InputTransportMessageFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    OutputAudioRawFrame,
    OutputTransportMessageUrgentFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport

from app.core.config import Settings
from app.db.database import create_engine_for_url, init_db
from app.main import create_app
from app.models.domain import AppointmentStatus, Slot, SlotStatus
from app.voice import (
    BrowserAudioJsonSerializer,
    TranscriptBridgeProcessor,
    VoiceConfigurationError,
    VoicePipelineConfig,
    build_pipecat_tools_schema,
    build_voice_pipeline,
    register_voice_tools,
)


class _DummyWebSocket:
    """Minimal WebSocket double for testing Pipecat pipeline assembly."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.client_state = None
        self.application_state = None


class VoicePipelineTests(unittest.IsolatedAsyncioTestCase):
    """Independent verification of Pipecat 1.17.0 pipeline, transport, VAD, and tools."""

    async def asyncSetUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_voice.db"
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

    async def test_config_validation_and_status_endpoint_never_exposes_keys(self) -> None:
        bad_config = VoicePipelineConfig(
            gemini_api_key="your_google_gemini_api_key_here",
            gemini_model="gemini-2.5-flash",
            elevenlabs_api_key="",
            elevenlabs_voice_id="your_elevenlabs_voice_id_here",
            elevenlabs_stt_model="scribe_v2_realtime",
            elevenlabs_tts_model="eleven_turbo_v2_5",
        )
        with self.assertRaises(VoiceConfigurationError):
            bad_config.validate_required_keys()

        app = create_app()
        fake_settings = Settings(
            gemini_api_key="your_google_gemini_api_key_here",
            elevenlabs_api_key="0123456789abcdef" * 4,
            elevenlabs_voice_id="your_elevenlabs_voice_id_here",
        )
        from unittest.mock import patch

        with patch("app.routes.voice.get_settings", return_value=fake_settings):
            with TestClient(app) as client:
                status_resp = client.get("/api/voice/status")
                self.assertEqual(status_resp.status_code, 200)
                payload = status_resp.json()
                self.assertFalse(payload["configured"])
                self.assertEqual(
                    payload["missing_credentials"],
                    ["GEMINI_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"],
                )
                self.assertEqual(payload["stt_provider"], "elevenlabs_realtime")
                self.assertEqual(payload["llm_provider"], "google_gemini")
                self.assertEqual(payload["tts_provider"], "elevenlabs")
                self.assertEqual(payload["vad_provider"], "silero")
                self.assertEqual(payload["websocket_path"], "/ws/voice")
                self.assertEqual(
                    set(payload.keys()),
                    {
                        "configured",
                        "missing_credentials",
                        "stt_provider",
                        "llm_provider",
                        "tts_provider",
                        "vad_provider",
                        "transport",
                        "websocket_path",
                    },
                )
                raw_text = json.dumps(payload)
                self.assertNotIn("AIza", raw_text)
                self.assertNotIn("sk_", raw_text)

                # Missing/invalid keys over WebSocket returns structured error without crashing
                with client.websocket_connect("/ws/voice") as ws:
                    msg = json.loads(ws.receive_text())
                    self.assertEqual(msg["type"], "error")
                    self.assertTrue(msg["fatal"])
                    self.assertIn("Key ID", msg["message"])

    async def test_browser_serializer_roundtrip(self) -> None:
        serializer = BrowserAudioJsonSerializer(sample_rate=16000)

        pcm = b"\x00\x01\x02\x03" * 80
        in_frame = await serializer.deserialize(pcm)
        self.assertIsInstance(in_frame, InputAudioRawFrame)
        assert isinstance(in_frame, InputAudioRawFrame)
        self.assertEqual(in_frame.audio, pcm)
        self.assertEqual(in_frame.sample_rate, 16000)

        ctrl_frame = await serializer.deserialize('{"type": "ping"}')
        self.assertIsInstance(ctrl_frame, InputTransportMessageFrame)

        out_audio = await serializer.serialize(
            OutputAudioRawFrame(audio=pcm, sample_rate=16000, num_channels=1)
        )
        self.assertEqual(out_audio, pcm)

        out_transcript = await serializer.serialize(
            OutputTransportMessageUrgentFrame(
                message={"type": "transcript", "role": "user", "text": "Hello", "final": True}
            )
        )
        self.assertEqual(json.loads(str(out_transcript))["text"], "Hello")

        out_interrupt = await serializer.serialize(InterruptionFrame())
        self.assertEqual(json.loads(str(out_interrupt))["type"], "interruption")

        out_err = await serializer.serialize(ErrorFrame(error="STT timeout", fatal=False))
        self.assertEqual(json.loads(str(out_err))["message"], "STT timeout")

    async def test_transcript_bridge_forwards_user_and_assistant_frames(self) -> None:
        bridge = TranscriptBridgeProcessor()
        pushed: list[object] = []

        async def _capture(frame: object, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
            pushed.append(frame)

        bridge.push_frame = _capture  # type: ignore[method-assign]

        await bridge.process_frame(
            TranscriptionFrame(text="Book Dr. Aarav", user_id="caller", timestamp="2026-11-24"),
            FrameDirection.DOWNSTREAM,
        )
        await bridge.process_frame(LLMFullResponseStartFrame(), FrameDirection.DOWNSTREAM)
        await bridge.process_frame(LLMTextFrame(text="Sure, "), FrameDirection.DOWNSTREAM)
        await bridge.process_frame(LLMTextFrame(text="what is your phone number?"), FrameDirection.DOWNSTREAM)
        await bridge.process_frame(LLMFullResponseEndFrame(), FrameDirection.DOWNSTREAM)

        urgent_msgs = [
            f.message for f in pushed if isinstance(f, OutputTransportMessageUrgentFrame)
        ]
        self.assertEqual(
            urgent_msgs,
            [
                {"type": "transcript", "role": "user", "text": "Book Dr. Aarav", "final": True},
                {
                    "type": "transcript",
                    "role": "assistant",
                    "text": "Sure, what is your phone number?",
                    "final": True,
                },
            ],
        )

    async def test_pipecat_pipeline_assembly_and_gemini_tools_adapter(self) -> None:
        tools_schema = build_pipecat_tools_schema()
        provider_tools = GeminiLLMAdapter().to_provider_tools_format(tools_schema)
        self.assertEqual(len(provider_tools), 1)
        fn_decls = provider_tools[0]["function_declarations"]
        self.assertEqual(
            {fn["name"] for fn in fn_decls},
            {"check_doctor_availability", "book_appointment", "cancel_appointment"},
        )

        config = VoicePipelineConfig.from_settings(
            Settings(
                gemini_api_key="test-gemini-key",
                elevenlabs_api_key="test-elevenlabs-key",
                elevenlabs_voice_id="test-voice-id",
            )
        )
        bundle = build_voice_pipeline(
            websocket=_DummyWebSocket(),  # type: ignore[arg-type]
            config=config,
            session_factory=self.session_factory,
        )

        self.assertIsInstance(bundle.transport, FastAPIWebsocketTransport)
        self.assertIsInstance(bundle.vad, SileroVADAnalyzer)
        self.assertIsInstance(bundle.stt, ElevenLabsRealtimeSTTService)
        self.assertIsInstance(bundle.llm, GoogleLLMService)
        self.assertIsInstance(bundle.tts, ElevenLabsTTSService)

        # Confirm all three functions are registered on GoogleLLMService
        self.assertTrue(bundle.llm.has_function("check_doctor_availability"))
        self.assertTrue(bundle.llm.has_function("book_appointment"))
        self.assertTrue(bundle.llm.has_function("cancel_appointment"))

        await bundle.worker.cancel()

    async def test_registered_pipecat_tool_handlers_end_to_end_booking_and_cancel(self) -> None:
        captured_handlers: dict[str, object] = {}
        queued_frames: list[object] = []

        class _MockLLM:
            def register_function(self, name: str, handler: object) -> None:
                captured_handlers[name] = handler

        class _MockWorker:
            async def queue_frame(self, frame: object) -> None:
                queued_frames.append(frame)

        register_voice_tools(
            _MockLLM(),  # type: ignore[arg-type]
            self.session_factory,
            worker_getter=lambda: _MockWorker(),  # type: ignore[arg-type, return-value]
        )

        async def _call(fn_name: str, args: dict[str, object]) -> dict[str, object]:
            results: list[dict[str, object]] = []

            async def _callback(res: dict[str, object], **_: object) -> None:
                results.append(res)

            handler = captured_handlers[fn_name]
            params = FunctionCallParams(
                function_name=fn_name,
                tool_call_id="call_1",
                arguments=args,
                llm=SimpleNamespace(),  # type: ignore[arg-type]
                pipeline_worker=SimpleNamespace(),  # type: ignore[arg-type]
                context=SimpleNamespace(),  # type: ignore[arg-type]
                result_callback=_callback,  # type: ignore[arg-type]
            )
            await handler(params)  # type: ignore[misc]
            return results[0]

        # 1. Check availability
        avail = await _call("check_doctor_availability", {"speciality": "Cardiology"})
        self.assertTrue(avail["ok"])
        slot = avail["available_slots"][0]  # type: ignore[index]

        # 2. Unconfirmed phone blocked
        blocked = await _call(
            "book_appointment",
            {
                "caller_phone": "+919876543210",
                "doctor_id": slot["doctor_id"],
                "appointment_date": slot["appointment_date"],
                "appointment_time": slot["appointment_time"],
                "phone_confirmed": False,
            },
        )
        self.assertFalse(blocked["ok"])
        self.assertTrue(blocked["requires_phone_confirmation"])

        # 3. Confirmed booking persists in SQLite and queues appointment_event
        booked = await _call(
            "book_appointment",
            {
                "caller_phone": "+919876543210",
                "doctor_id": slot["doctor_id"],
                "appointment_date": slot["appointment_date"],
                "appointment_time": slot["appointment_time"],
                "phone_confirmed": True,
            },
        )
        self.assertTrue(booked["ok"])
        appt_id = booked["appointment"]["appointment_id"]  # type: ignore[index]
        self.assertEqual(len(queued_frames), 1)
        self.assertEqual(queued_frames[0].message["action"], "booked")  # type: ignore[attr-defined]

        # 4. Confirmed cancellation cancels in SQLite, releases slot, and queues event
        cancelled = await _call(
            "cancel_appointment",
            {
                "caller_phone": "+919876543210",
                "appointment_id": appt_id,
                "phone_confirmed": True,
                "cancellation_confirmed": True,
            },
        )
        self.assertTrue(cancelled["ok"])
        self.assertEqual(
            cancelled["cancelled_appointment"]["status"],  # type: ignore[index]
            AppointmentStatus.CANCELLED.value,
        )
        self.assertEqual(len(queued_frames), 2)
        self.assertEqual(queued_frames[1].message["action"], "cancelled")  # type: ignore[attr-defined]

        async with self.session_factory() as db:
            db_slot = await db.scalar(select(Slot).where(Slot.id == slot["slot_id"]))
            assert db_slot is not None
            self.assertEqual(db_slot.status, SlotStatus.AVAILABLE.value)


if __name__ == "__main__":
    unittest.main()
