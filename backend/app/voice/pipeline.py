"""Pipecat real-time Voice AI pipeline: Silero VAD -> ElevenLabs STT -> Gemini LLM -> ElevenLabs TTS."""

from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame, OutputTransportMessageUrgentFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.elevenlabs.stt import CommitStrategy, ElevenLabsRealtimeSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from app.ai.prompts import build_system_prompt
from app.core.config import Settings
from app.voice.processors import TranscriptBridgeProcessor
from app.voice.serializer import BrowserAudioJsonSerializer
from app.voice.tools import build_pipecat_tools_schema, register_voice_tools

_PLACEHOLDER_PREFIX = "your_"


class VoiceConfigurationError(RuntimeError):
    """Raised when required Gemini or ElevenLabs credentials are missing or placeholders."""


def _is_configured(value: str) -> bool:
    cleaned = (value or "").strip()
    return bool(cleaned) and not cleaned.startswith(_PLACEHOLDER_PREFIX)


@dataclass(frozen=True, slots=True)
class VoicePipelineConfig:
    """Typed configuration for the Pipecat real-time voice pipeline."""

    gemini_api_key: str
    gemini_model: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    elevenlabs_stt_model: str
    elevenlabs_tts_model: str
    sample_rate: int = 16000
    vad_stop_secs: float = 0.6

    @classmethod
    def from_settings(cls, settings: Settings) -> "VoicePipelineConfig":
        """Build pipeline configuration from application settings."""
        return cls(
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            elevenlabs_api_key=settings.elevenlabs_api_key,
            elevenlabs_voice_id=settings.elevenlabs_voice_id,
            elevenlabs_stt_model=settings.elevenlabs_stt_model,
            elevenlabs_tts_model=settings.elevenlabs_tts_model,
        )

    def missing_fields(self) -> list[str]:
        """Return list of missing or placeholder credential environment variable names."""
        missing: list[str] = []
        if not _is_configured(self.gemini_api_key):
            missing.append("GEMINI_API_KEY")
        if not _is_configured(self.elevenlabs_api_key):
            missing.append("ELEVENLABS_API_KEY")
        if not _is_configured(self.elevenlabs_voice_id):
            missing.append("ELEVENLABS_VOICE_ID")
        return missing

    def validate_required_keys(self) -> None:
        """Raise VoiceConfigurationError if required credentials are missing."""
        missing = self.missing_fields()
        if missing:
            raise VoiceConfigurationError(
                "Missing required voice pipeline credentials in backend/.env: "
                + ", ".join(missing)
            )


@dataclass(slots=True)
class VoicePipelineBundle:
    """Assembled Pipecat pipeline, worker, transport, and services for a single call."""

    transport: FastAPIWebsocketTransport
    pipeline: Pipeline
    worker: PipelineWorker
    context: LLMContext
    stt: ElevenLabsRealtimeSTTService
    llm: GoogleLLMService
    tts: ElevenLabsTTSService
    vad: SileroVADAnalyzer


def build_voice_pipeline(
    websocket: WebSocket,
    config: VoicePipelineConfig,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    allowed_origins: list[str] | None = None,
    session_timeout: int | None = 600,
) -> VoicePipelineBundle:
    """Assemble all Pipecat 1.17 processors for a browser WebSocket voice session."""
    config.validate_required_keys()

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_in_sample_rate=config.sample_rate,
            audio_in_channels=1,
            audio_out_enabled=True,
            audio_out_sample_rate=config.sample_rate,
            audio_out_channels=1,
            add_wav_header=False,
            serializer=BrowserAudioJsonSerializer(sample_rate=config.sample_rate),
            session_timeout=session_timeout,
            allowed_origins=allowed_origins or [],
        ),
    )

    vad = SileroVADAnalyzer(params=VADParams(stop_secs=config.vad_stop_secs))

    stt = ElevenLabsRealtimeSTTService(
        api_key=config.elevenlabs_api_key,
        commit_strategy=CommitStrategy.MANUAL,
        sample_rate=config.sample_rate,
        settings=ElevenLabsRealtimeSTTService.Settings(
            model=config.elevenlabs_stt_model,
        ),
    )

    llm = GoogleLLMService(
        api_key=config.gemini_api_key,
        settings=GoogleLLMService.Settings(
            model=config.gemini_model,
            temperature=0.2,
        ),
    )

    tts = ElevenLabsTTSService(
        api_key=config.elevenlabs_api_key,
        sample_rate=config.sample_rate,
        settings=ElevenLabsTTSService.Settings(
            voice=config.elevenlabs_voice_id,
            model=config.elevenlabs_tts_model,
        ),
    )

    system_prompt = build_system_prompt()
    tools = build_pipecat_tools_schema()
    context = LLMContext(
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "The caller has just connected. Greet them warmly as Maya from the clinic "
                    "and ask how you can help them today."
                ),
            },
        ],
        tools=tools,
    )

    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=vad),
    )

    user_transcript_bridge = TranscriptBridgeProcessor(name="UserTranscriptBridge")
    assistant_transcript_bridge = TranscriptBridgeProcessor(name="AssistantTranscriptBridge")

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_transcript_bridge,
            context_aggregator.user(),
            llm,
            assistant_transcript_bridge,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=config.sample_rate,
            audio_out_sample_rate=config.sample_rate,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    register_voice_tools(llm, session_factory, worker_getter=lambda: worker)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_: Any, __: WebSocket) -> None:
        logger.info("Voice WebSocket client connected; starting Pipecat call session.")
        await worker.queue_frame(
            OutputTransportMessageUrgentFrame(
                message={"type": "status", "state": "connected"}
            )
        )
        await worker.queue_frame(LLMRunFrame())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_: Any, __: WebSocket) -> None:
        logger.info("Voice WebSocket client disconnected; shutting down pipeline worker.")
        await worker.cancel()

    @transport.event_handler("on_session_timeout")
    async def on_session_timeout(_: Any, __: WebSocket) -> None:
        logger.warning("Voice WebSocket session timed out; cancelling pipeline worker.")
        await worker.queue_frame(
            OutputTransportMessageUrgentFrame(
                message={"type": "error", "message": "Voice session timed out.", "fatal": True}
            )
        )
        await worker.cancel()

    return VoicePipelineBundle(
        transport=transport,
        pipeline=pipeline,
        worker=worker,
        context=context,
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
    )


async def run_voice_session(
    websocket: WebSocket,
    config: VoicePipelineConfig,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    allowed_origins: list[str] | None = None,
) -> None:
    """Build and run a Pipecat voice pipeline for the lifetime of a WebSocket call."""
    bundle = build_voice_pipeline(
        websocket=websocket,
        config=config,
        session_factory=session_factory,
        allowed_origins=allowed_origins,
    )
    runner = PipelineRunner(handle_sigint=False, handle_sigterm=False)
    await runner.run(bundle.worker)
