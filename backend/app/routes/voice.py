import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from loguru import logger
from pydantic import BaseModel

from app.core.config import get_settings
from app.db import AsyncSessionLocal
from app.voice import VoiceConfigurationError, VoicePipelineConfig, run_voice_session

router = APIRouter(tags=["Voice"])


class VoiceStatusResponse(BaseModel):
    """Non-sensitive configuration readiness status for the Pipecat voice pipeline."""

    configured: bool
    missing_credentials: list[str]
    stt_provider: str
    llm_provider: str
    tts_provider: str
    vad_provider: str
    transport: str
    websocket_path: str


@router.get(
    "/api/voice/status",
    response_model=VoiceStatusResponse,
    summary="Voice pipeline readiness status",
    description=(
        "Check whether required voice pipeline credentials are configured without "
        "exposing any API keys."
    ),
)
async def get_voice_status() -> VoiceStatusResponse:
    """Return pipeline readiness and active provider metadata (no secrets exposed)."""
    settings = get_settings()
    config = VoicePipelineConfig.from_settings(settings)
    missing = config.missing_fields()
    return VoiceStatusResponse(
        configured=len(missing) == 0,
        missing_credentials=missing,
        stt_provider="elevenlabs_realtime",
        llm_provider="google_gemini",
        tts_provider="elevenlabs",
        vad_provider="silero",
        transport="fastapi_websocket",
        websocket_path="/ws/voice",
    )


@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time bidirectional WebSocket endpoint for the Pipecat voice assistant."""
    settings = get_settings()
    config = VoicePipelineConfig.from_settings(settings)

    try:
        config.validate_required_keys()
    except VoiceConfigurationError as exc:
        await websocket.accept()
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": str(exc),
                    "fatal": True,
                }
            )
        )
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    allowed_origins = (
        [] if settings.app_env == "development" else list(settings.cors_origins)
    )

    try:
        await websocket.accept()
        await run_voice_session(
            websocket=websocket,
            config=config,
            session_factory=AsyncSessionLocal,
            allowed_origins=allowed_origins,
        )
    except ValueError as exc:
        logger.warning(f"Voice WebSocket rejected: {exc}")
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Connection origin not allowed.", "fatal": True})
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected by client.")
    except Exception as exc:
        logger.exception("Unhandled error in Pipecat voice session")
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Voice pipeline error: {exc.__class__.__name__}",
                        "fatal": True,
                    }
                )
            )
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
