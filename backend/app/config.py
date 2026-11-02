"""All settings, read from environment variables or backend/.env. See .env.example for documentation."""

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SESSION_SECRET = "dev-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database -----------------------------------------------------------------------------------------------
    database_url: str = "postgresql+psycopg://hospital_ai:hospital_ai@localhost:5432/hospital_ai"

    # --- Sign-in & governance -----------------------------------------------------------------------------------
    session_secret: str = DEV_SESSION_SECRET
    session_hours: int = 12
    secure_cookies: bool = False  # true when served over HTTPS
    environment_banner: str = "Pilot environment · synthetic data only"
    cors_origins: list[str] = ["http://localhost:3004", "http://localhost:3000"]
    # Scribe transcripts, notes and patient details are erased after this many days; metrics are kept
    retention_days: int = 7

    # --- Clinic -------------------------------------------------------------------------------------------------
    clinic_timezone: str = "Asia/Karachi"
    booking_window_days: int = 10
    # Optional shared secret VAPI sends in the x-vapi-secret header; when set, webhooks without it are rejected
    vapi_secret: str | None = None

    # --- AI medical scribe --------------------------------------------------------------------------------------
    transcriber: str = "deepgram"
    deepgram_api_key: str | None = None
    deepgram_model: str = "nova-3-medical"

    note_provider: str = "claude"  # "claude" or "ollama" (local, no key)
    anthropic_api_key: str | None = None
    note_model: str = "claude-opus-5-5"
    note_effort: str = "low"  # keeps drafting fast mid-clinic; the safety review runs deeper
    review_effort: str = "medium"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:14b"

    # Pilot metrics assumption, shown on the dashboard so it can be challenged
    baseline_minutes_per_note: float = 16.0

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.clinic_timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
