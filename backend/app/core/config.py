import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `backend/.env`."""

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Voice AI Doctor Appointment Assistant"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    database_url: str = "sqlite+aiosqlite:///./data/appointments.db"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_stt_model: str = "scribe_v2_realtime"
    elevenlabs_tts_model: str = "eleven_turbo_v2_5"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in text.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
