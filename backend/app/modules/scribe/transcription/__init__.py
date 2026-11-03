from app.core.config import Settings

from .base import Segment, Transcriber, Transcript, TranscriptionError
from .deepgram import DeepgramTranscriber

__all__ = ["Segment", "Transcript", "Transcriber", "TranscriptionError", "get_transcriber"]


def get_transcriber(settings: Settings) -> Transcriber:
    """Pick the adapter from the TRANSCRIBER setting. Adding a provider = one adapter + one branch here."""
    if settings.transcriber == "deepgram":
        if not settings.deepgram_api_key:
            raise TranscriptionError("DEEPGRAM_API_KEY is not set in backend/.env")
        return DeepgramTranscriber(settings.deepgram_api_key, settings.deepgram_model)
    raise TranscriptionError(f"Unknown transcriber '{settings.transcriber}'")
