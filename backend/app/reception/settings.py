"""Receptionist settings (environment variables / backend/.env). See .env.example for documentation."""

from pydantic_settings import BaseSettings


class ReceptionSettings(BaseSettings):
    # How many days ahead the voice agent may book
    booking_window_days: int = 10
    # Optional shared secret VAPI sends in the x-vapi-secret header; when set, webhooks without it are rejected
    vapi_secret: str | None = None
