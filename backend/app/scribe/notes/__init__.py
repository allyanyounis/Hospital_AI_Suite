from ..settings import ScribeSettings
from .base import GeneratedNote, NoteGenerationError, NoteGenerator, draft_note, note_to_text
from .claude import ClaudeNoteGenerator
from .documents import DOCUMENT_TYPES, DocumentType, GeneratedDocument, write_document
from .extras import (
    CareTask,
    ClinicalCode,
    ClinicalCodes,
    SavedCodes,
    SavedTasks,
    TaskList,
    suggest_codes,
    suggest_tasks,
)
from .groq import GroqNoteGenerator
from .ollama import OllamaNoteGenerator
from .review import NoteReview, review_note
from .templates import TEMPLATES, NoteTemplate

__all__ = [
    "CareTask",
    "ClinicalCode",
    "ClinicalCodes",
    "SavedCodes",
    "SavedTasks",
    "TaskList",
    "suggest_codes",
    "suggest_tasks",
    "DOCUMENT_TYPES",
    "DocumentType",
    "GeneratedDocument",
    "GeneratedNote",
    "NoteGenerationError",
    "NoteGenerator",
    "NoteReview",
    "TEMPLATES",
    "NoteTemplate",
    "draft_note",
    "get_note_generator",
    "note_to_text",
    "review_note",
    "write_document",
]


def get_note_generator(settings: ScribeSettings) -> NoteGenerator:
    """Pick the adapter from the NOTE_PROVIDER setting. Adding a provider = one adapter + one branch here."""
    if settings.note_provider == "ollama":
        return OllamaNoteGenerator(settings.ollama_url, settings.ollama_model)
    if settings.note_provider == "claude":
        if not settings.anthropic_api_key:
            raise NoteGenerationError("ANTHROPIC_API_KEY is not set in backend/.env")
        return ClaudeNoteGenerator(settings.anthropic_api_key, settings.note_model, settings.note_effort)
    if settings.note_provider == "groq":
        if not settings.groq_api_key:
            raise NoteGenerationError("GROQ_API_KEY is not set in backend/.env")
        return GroqNoteGenerator(settings.groq_api_key, settings.groq_model, settings.note_effort)
    raise NoteGenerationError(f"Unknown note provider '{settings.note_provider}'")
