"""Browser-compatible PCM16 + JSON WebSocket frame serializer for Pipecat."""

import json
from typing import Any

from loguru import logger

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    InputAudioRawFrame,
    InputTransportMessageFrame,
    InterruptionFrame,
    OutputAudioRawFrame,
    OutputTransportMessageFrame,
    OutputTransportMessageUrgentFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer


class BrowserAudioJsonSerializer(FrameSerializer):
    """Serialize binary PCM16 audio and JSON transcript/control events for browsers.

    Wire contract:
    - Client -> Server (binary): Raw 16-bit PCM mono audio at `audio_in_sample_rate` (default 16 kHz).
    - Client -> Server (text): JSON control message (e.g. `{"type": "ping"}`).
    - Server -> Client (binary): Raw 16-bit PCM mono TTS audio at `audio_out_sample_rate` (default 16 kHz).
    - Server -> Client (text): JSON events (`transcript`, `vad`, `appointment_event`, `interruption`, `error`).
    """

    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        num_channels: int = 1,
        params: FrameSerializer.InputParams | None = None,
    ) -> None:
        super().__init__(
            params=params
            or FrameSerializer.InputParams(
                ignore_rtvi_messages=True,
                audio_in_sample_rate=sample_rate,
                audio_out_sample_rate=sample_rate,
            )
        )
        self._default_sample_rate = sample_rate
        self._num_channels = num_channels

    async def serialize(self, frame: Frame) -> str | bytes | None:
        """Convert outgoing Pipecat frames into WebSocket bytes or JSON strings."""
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio

        if isinstance(frame, (OutputTransportMessageFrame, OutputTransportMessageUrgentFrame)):
            if self.should_ignore_frame(frame):
                return None
            return json.dumps(frame.message)

        if isinstance(frame, InterruptionFrame):
            return json.dumps({"type": "interruption"})

        if isinstance(frame, ErrorFrame):
            return json.dumps(
                {
                    "type": "error",
                    "message": frame.error,
                    "fatal": frame.fatal,
                }
            )

        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        """Convert incoming WebSocket bytes or JSON text into Pipecat input frames."""
        if isinstance(data, (bytes, bytearray)):
            audio_bytes = bytes(data)
            if not audio_bytes:
                return None
            return InputAudioRawFrame(
                audio=audio_bytes,
                sample_rate=self._params.audio_in_sample_rate or self._default_sample_rate,
                num_channels=self._num_channels,
            )

        if isinstance(data, str):
            try:
                payload: Any = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Ignoring non-JSON text message received on voice WebSocket.")
                return None

            if isinstance(payload, dict):
                return InputTransportMessageFrame(message=payload)

        return None
