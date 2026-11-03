"""All settings, read from environment variables or backend/.env. See .env.example for documentation.

Shared settings live here; each module declares its own in <module>/settings.py and they are combined into one
`Settings` object, so every value is still read with get_settings().<name>.
"""

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

from .reception.settings import ReceptionSettings
from .scribe.settings import ScribeSettings

DEV_SESSION_SECRET = "dev-only-change-me"


class CoreSettings(BaseSettings):
    # --- Database -----------------------------------------------------------------------------------------------
    database_url: str = "postgresql+psycopg://hospital_ai:hospital_ai@localhost:5432/hospital_ai"

    # --- Sign-in & governance -----------------------------------------------------------------------------------
    session_secret: str = DEV_SESSION_SECRET
    session_hours: int = 12
    secure_cookies: bool = False  # true when served over HTTPS
    environment_banner: str = "Pilot environment · synthetic data only"
    cors_origins: list[str] = ["http://localhost:3004", "http://localhost:3000"]

    # --- Clinic -------------------------------------------------------------------------------------------------
    clinic_timezone: str = "Asia/Karachi"

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.clinic_timezone)


class Settings(CoreSettings, ScribeSettings, ReceptionSettings):
    """Every setting of the suite. A new module adds its settings class to this list."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
