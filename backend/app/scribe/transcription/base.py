from typing import Protocol

from pydantic import BaseModel


class Segment(BaseModel):
    id: int
    speaker: int  # provider speaker index; the UI maps indices to Clinician / Patient
    start: float  # seconds
    end: float
    text: str


class Transcript(BaseModel):
    segments: list[Segment]
    provider: str
    duration: float | None = None


class TranscriptionError(Exception):
    pass


class Transcriber(Protocol):
    """Every speech-to-text provider implements this and returns the standard Transcript."""

    name: str

    async def transcribe(self, audio: bytes, mimetype: str) -> Transcript: ...
