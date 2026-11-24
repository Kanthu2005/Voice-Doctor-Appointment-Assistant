"""Custom Pipecat frame processors for real-time voice transcript & error forwarding."""

from loguru import logger

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    InterimTranscriptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    OutputTransportMessageUrgentFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class TranscriptBridgeProcessor(FrameProcessor):
    """Forward STT/LLM transcripts, VAD state, and errors to the browser WebSocket."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._assistant_buffer: list[str] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, VADUserStartedSpeakingFrame):
            await self.push_frame(
                OutputTransportMessageUrgentFrame(
                    message={"type": "vad", "speaking": True}
                )
            )
        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            await self.push_frame(
                OutputTransportMessageUrgentFrame(
                    message={"type": "vad", "speaking": False}
                )
            )
        elif isinstance(frame, InterimTranscriptionFrame) and frame.text.strip():
            await self.push_frame(
                OutputTransportMessageUrgentFrame(
                    message={
                        "type": "transcript",
                        "role": "user",
                        "text": frame.text,
                        "final": False,
                    }
                )
            )
        elif isinstance(frame, TranscriptionFrame) and frame.text.strip():
            await self.push_frame(
                OutputTransportMessageUrgentFrame(
                    message={
                        "type": "transcript",
                        "role": "user",
                        "text": frame.text,
                        "final": True,
                    }
                )
            )
        elif isinstance(frame, LLMFullResponseStartFrame):
            self._assistant_buffer.clear()
        elif isinstance(frame, LLMTextFrame) and frame.text:
            self._assistant_buffer.append(frame.text)
        elif isinstance(frame, LLMFullResponseEndFrame):
            full_text = "".join(self._assistant_buffer).strip()
            self._assistant_buffer.clear()
            if full_text:
                await self.push_frame(
                    OutputTransportMessageUrgentFrame(
                        message={
                            "type": "transcript",
                            "role": "assistant",
                            "text": full_text,
                            "final": True,
                        }
                    )
                )
        elif isinstance(frame, ErrorFrame):
            logger.error(f"Pipecat pipeline error: {frame.error} (fatal={frame.fatal})")
            await self.push_frame(
                OutputTransportMessageUrgentFrame(
                    message={
                        "type": "error",
                        "message": frame.error,
                        "fatal": frame.fatal,
                    }
                )
            )

        await self.push_frame(frame, direction)
