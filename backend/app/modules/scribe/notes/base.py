import re
from typing import Protocol, TypeVar

from pydantic import BaseModel

from ..transcription import Transcript
from .templates import NoteTemplate


class NoteStatement(BaseModel):
    text: str
    # Transcript segment ids that support this statement; drives click-to-source in the UI
    source_segment_ids: list[int]


class NoteSection(BaseModel):
    heading: str
    statements: list[NoteStatement]


class GeneratedNote(BaseModel):
    sections: list[NoteSection]


class NoteGenerationError(Exception):
    pass


T = TypeVar("T", bound=BaseModel)


class NoteGenerator(Protocol):
    """Every LLM provider implements one structured call; drafting, review and documents are built on it."""

    name: str
    model: str

    async def complete(self, system: str, user: str, schema: type[T], effort: str | None = None) -> T: ...


SYSTEM_PROMPT = """You are a clinical documentation assistant. You turn a transcript of a clinician-patient \
consultation into a draft clinical note that a clinician will review, edit and sign.

Rules:
- Use only information stated in the transcript. Never add findings, diagnoses, doses or plans that were not said.
- Every statement must cite the transcript segment ids that support it in source_segment_ids. If you cannot \
cite a segment, leave the statement out.
- Write in concise clinical style (standard abbreviations are fine). One clinical fact or closely related group \
of facts per statement.
- Produce exactly the sections of the template, in order, with the headings given. If nothing in the transcript \
belongs in a section, return it with an empty statements list.
- Attribute correctly: symptoms and history come from the patient; examination findings, assessment and plan \
come from the clinician. Ignore small talk.
- Record a negative ("no X") only when the patient explicitly denies X. If the clinician asks about several \
symptoms and the patient answers only some, record what they confirmed and denied; leave the rest out.
- Include every positive symptom the patient mentions, even if it was not asked about.
- Put the citation only in source_segment_ids, never in the statement text. Do not start statements with \
labels like "Plan:" (the section heading already says it)."""


def format_transcript(transcript: Transcript, clinician_speaker: int) -> str:
    return "\n".join(
        f"[{s.id}] {'Clinician' if s.speaker == clinician_speaker else 'Patient/companion'}: {s.text}"
        for s in transcript.segments
    )


def build_user_prompt(transcript: Transcript, template: NoteTemplate, clinician_speaker: int) -> str:
    sections = "\n".join(f"- {s.heading}: {s.guidance}" for s in template.sections)
    return (
        f"Template: {template.name}\nSections:\n{sections}\n\n"
        f"Transcript (segment id in brackets):\n{format_transcript(transcript, clinician_speaker)}"
    )


# Smaller local models sometimes echo the citation into the text, e.g. "... (source_segment_ids: [3])"
_LEAKED_CITATION = re.compile(r"\s*\(?\s*source_segment_ids\s*:?\s*\[[\d,\s]*\]\s*\)?", re.IGNORECASE)


def clean_note(note: GeneratedNote, transcript: Transcript) -> GeneratedNote:
    """Enforce the citation rule in code: every statement must link to a real transcript segment."""
    valid = {s.id for s in transcript.segments}
    for section in note.sections:
        kept = []
        for st in section.statements:
            st.source_segment_ids = [i for i in st.source_segment_ids if i in valid]
            st.text = _LEAKED_CITATION.sub("", st.text).strip()
            if st.source_segment_ids and st.text:
                kept.append(st)
        section.statements = kept
    return note


async def draft_note(
    generator: NoteGenerator, transcript: Transcript, template: NoteTemplate, clinician_speaker: int
) -> GeneratedNote:
    note = await generator.complete(
        SYSTEM_PROMPT, build_user_prompt(transcript, template, clinician_speaker), GeneratedNote
    )
    return clean_note(note, transcript)


def note_to_text(note: GeneratedNote) -> str:
    return "\n\n".join(
        f"{s.heading.upper()}\n" + ("\n".join(f"- {st.text}" for st in s.statements) or "- Not discussed")
        for s in note.sections
    )
