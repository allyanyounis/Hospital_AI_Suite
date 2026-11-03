"""All settings, read from environment variables or backend/.env (environment wins). See .env.example."""

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SESSION_SECRET = "dev-only-change-me"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"  # backend/.env, wherever the process is started from


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # --- Database -----------------------------------------------------------------------------------------------
    database_url: str = "postgresql+psycopg://hospital_ai:hospital_ai@127.0.0.1:5432/hospital_ai"

    # --- Sign-in & governance -----------------------------------------------------------------------------------
    session_secret: str = DEV_SESSION_SECRET
    session_hours: int = 12
    secure_cookies: bool = False  # true when served over HTTPS
    environment_banner: str = "Pilot environment · synthetic data only"
    cors_origins: list[str] = ["http://localhost:3004", "http://localhost:3000"]
    # Scribe transcripts, notes and patient details are erased after this many days; metrics are kept
    retention_days: int = 7

    # --- Hospital -----------------------------------------------------------------------------------------------
    hospital_name: str = "Hospital AI Suite"
    # HOSPITAL_TIMEZONE; the earlier CLINIC_TIMEZONE is still read
    hospital_timezone: str = Field(
        "Asia/Karachi", validation_alias=AliasChoices("hospital_timezone", "clinic_timezone")
    )
    booking_window_days: int = 10
    # Optional shared secret VAPI sends in the x-vapi-secret header; when set, webhooks without it are rejected
    vapi_secret: str | None = None

    # --- AI medical scribe --------------------------------------------------------------------------------------
    transcriber: str = "deepgram"
    deepgram_api_key: str | None = None
    deepgram_model: str = "nova-3-medical"

    note_provider: str = "claude"  # "claude", "groq" or "ollama" (local, no key)
    anthropic_api_key: str | None = None
    note_model: str = "claude-opus-5-5"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    note_effort: str = "low"  # keeps drafting fast mid-clinic; the safety review runs deeper
    review_effort: str = "medium"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:14b"

    # Pilot metrics assumption, shown on the dashboard so it can be challenged
    baseline_minutes_per_note: float = 16.0

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.hospital_timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
