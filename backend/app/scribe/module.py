from ..config import get_settings
from ..module import Module
from . import live_router, router
from .notes import NoteGenerationError, get_note_generator
from .notes.ollama import OllamaNoteGenerator
from .repository import purge_expired_content, recover_interrupted_drafts


def _purge_expired() -> None:
    purge_expired_content(get_settings().retention_days)


async def _public_config() -> dict:
    """Which speech-to-text and note model are configured, so the UI can show what's ready."""
    settings = get_settings()
    try:
        generator = get_note_generator(settings)
        if isinstance(generator, OllamaNoteGenerator):
            note_model, notes_ready = f"{generator.model} (local)", await generator.is_ready()
        else:
            note_model, notes_ready = generator.model, True
    except NoteGenerationError:
        note_model, notes_ready = settings.note_model, False
    return {
        "retention_days": settings.retention_days,
        "transcriber": settings.transcriber,
        "transcriber_ready": bool(settings.deepgram_api_key),
        "note_model": note_model,
        "notes_ready": notes_ready,
    }


module = Module(
    name="scribe",
    routers=[router.router, live_router.router],
    on_startup=[recover_interrupted_drafts, _purge_expired],
    public_config=_public_config,
)
