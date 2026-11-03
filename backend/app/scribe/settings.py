"""Scribe settings (environment variables / backend/.env). See .env.example for documentation."""

from pydantic_settings import BaseSettings


class ScribeSettings(BaseSettings):
    # Scribe transcripts, notes and patient details are erased after this many days; metrics are kept
    retention_days: int = 7

    # Speech to text
    transcriber: str = "deepgram"
    deepgram_api_key: str | None = None
    deepgram_model: str = "nova-3-medical"

    # Note drafting, safety review, codes, tasks and letters
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
