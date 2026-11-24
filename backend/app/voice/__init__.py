"""Pipecat voice AI pipeline package (Silero VAD + ElevenLabs STT/TTS + Google Gemini LLM)."""

from app.voice.pipeline import (
    VoiceConfigurationError,
    VoicePipelineBundle,
    VoicePipelineConfig,
    build_voice_pipeline,
    run_voice_session,
)
from app.voice.processors import TranscriptBridgeProcessor
from app.voice.serializer import BrowserAudioJsonSerializer
from app.voice.tools import build_pipecat_tools_schema, register_voice_tools

__all__ = [
    "BrowserAudioJsonSerializer",
    "TranscriptBridgeProcessor",
    "VoiceConfigurationError",
    "VoicePipelineBundle",
    "VoicePipelineConfig",
    "build_pipecat_tools_schema",
    "build_voice_pipeline",
    "register_voice_tools",
    "run_voice_session",
]
