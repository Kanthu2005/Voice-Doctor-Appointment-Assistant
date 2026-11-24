"""Google Gemini AI appointment assistant and function-calling tools."""

from app.ai.gemini_assistant import (
    AssistantTurnResult,
    ExecutedToolCall,
    GeminiAppointmentAssistant,
    GeminiConfigurationError,
)
from app.ai.prompts import ASSISTANT_SYSTEM_PROMPT, build_system_prompt
from app.ai.tools import (
    GEMINI_TOOLS,
    book_appointment,
    cancel_appointment,
    check_doctor_availability,
    execute_tool_call,
)

__all__ = [
    "ASSISTANT_SYSTEM_PROMPT",
    "AssistantTurnResult",
    "ExecutedToolCall",
    "GEMINI_TOOLS",
    "GeminiAppointmentAssistant",
    "GeminiConfigurationError",
    "book_appointment",
    "build_system_prompt",
    "cancel_appointment",
    "check_doctor_availability",
    "execute_tool_call",
]
