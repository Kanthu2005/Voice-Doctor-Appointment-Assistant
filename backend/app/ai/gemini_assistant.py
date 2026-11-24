"""Google Gemini conversation orchestrator with multi-step function calling."""

from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import build_system_prompt
from app.ai.tools import GEMINI_TOOLS, execute_tool_call
from app.core.config import Settings, get_settings

_PLACEHOLDER_PREFIX = "your_"


@dataclass(slots=True)
class ExecutedToolCall:
    """Record of one tool invocation executed during an assistant turn."""

    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


@dataclass(slots=True)
class AssistantTurnResult:
    """Result returned by `GeminiAppointmentAssistant.process_turn`."""

    reply_text: str
    tool_calls: list[ExecutedToolCall] = field(default_factory=list)
    history: list[types.Content] = field(default_factory=list)


class GeminiConfigurationError(RuntimeError):
    """Raised when GEMINI_API_KEY is missing or unconfigured."""


class GeminiAppointmentAssistant:
    """Stateful/turn-based Gemini assistant wired to SQLite appointment tools."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
        max_tool_rounds: int = 6,
    ) -> None:
        self.settings = settings or get_settings()
        self.max_tool_rounds = max_tool_rounds

        if client is not None:
            self._client = client
        else:
            api_key = (self.settings.gemini_api_key or "").strip()
            if not api_key or api_key.startswith(_PLACEHOLDER_PREFIX):
                raise GeminiConfigurationError(
                    "GEMINI_API_KEY is not configured. Set a valid key in backend/.env."
                )
            self._client = genai.Client(api_key=api_key)

    async def process_turn(
        self,
        db: AsyncSession,
        user_message: str,
        history: list[types.Content] | None = None,
    ) -> AssistantTurnResult:
        """Process one user message, executing any Gemini tool calls against SQLite."""
        contents: list[types.Content] = list(history or [])
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )

        config = types.GenerateContentConfig(
            system_instruction=build_system_prompt(),
            tools=[GEMINI_TOOLS],
            temperature=0.2,
        )

        executed_calls: list[ExecutedToolCall] = []

        for _ in range(self.max_tool_rounds):
            response = await self._client.aio.models.generate_content(
                model=self.settings.gemini_model,
                contents=contents,
                config=config,
            )

            candidate_content = (
                response.candidates[0].content
                if getattr(response, "candidates", None) and response.candidates[0].content
                else None
            )
            if candidate_content is not None:
                contents.append(candidate_content)

            function_calls = list(getattr(response, "function_calls", None) or [])
            if not function_calls:
                reply_text = (getattr(response, "text", None) or "").strip()
                return AssistantTurnResult(
                    reply_text=reply_text,
                    tool_calls=executed_calls,
                    history=contents,
                )

            response_parts: list[types.Part] = []
            for call in function_calls:
                args = dict(call.args or {})
                result = await execute_tool_call(db, call.name, args)
                executed_calls.append(
                    ExecutedToolCall(name=call.name, arguments=args, result=result)
                )
                response_parts.append(
                    types.Part.from_function_response(name=call.name, response=result)
                )

            contents.append(types.Content(role="user", parts=response_parts))

        raise RuntimeError(
            f"Gemini exceeded maximum tool-calling rounds ({self.max_tool_rounds}) in a single turn."
        )
