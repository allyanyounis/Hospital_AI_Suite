"""Pre-sign-off safety check: compares the clinician's edited note with the transcript and flags what needs a look."""

from typing import Literal

from pydantic import BaseModel

from ..transcription import Transcript
from .base import GeneratedNote, NoteGenerator, format_transcript


class ReviewFinding(BaseModel):
    category: Literal["unsupported", "missing", "inconsistency", "safety"]
    severity: Literal["high", "medium", "low"]
    # Written for the clinician: what to check, in one or two sentences
    message: str
    # Note section heading the finding is about, or "" if it is about the note as a whole
    section: str
    source_segment_ids: list[int]


class NoteReview(BaseModel):
    findings: list[ReviewFinding]


REVIEW_PROMPT = """You are a clinical documentation safety reviewer. A clinician is about to sign a note that was \
drafted by AI from a consultation transcript and then edited by the clinician. Compare the note with the transcript \
and report only issues the clinician should check before signing.

Categories:
- unsupported: the note states something the transcript does not support (including lines the clinician added \
that contradict the transcript). Lines marked [clinician-added] are allowed to contain information from outside \
the recording; flag them only if they contradict the transcript.
- missing: something clinically important was said in the transcript but is absent from the note (cite the \
segments), or information that this kind of note normally must contain was never discussed, such as allergies \
before a new prescription, dose/frequency/duration of a new medicine, follow-up or return precautions (cite no \
segments and phrase it as a question for the clinician, e.g. "Allergies were not discussed; confirm before \
prescribing.").
- inconsistency: numbers, units, doses, laterality, timings or names in the note differ from the transcript.
- safety: a clinically risky combination visible in the record, e.g. a prescribed drug the patient reports an \
allergy to, or a dose that looks wrong for the stated weight or age. In cardiology pay particular attention to: \
antiplatelet or anticoagulant agent, dose, combination or duration differing from the transcript (an \
anticoagulant plus an antiplatelet that the clinician said to stop must not appear as continued); a medicine \
recorded as stopped or started the wrong way round; contrast allergy before angiography; potassium or renal \
function and MRA/ACE inhibitor/ARNI changes; ejection fraction, troponin, BP or heart-rate values that differ from \
what was said.

Rules:
- Never suggest adding information that was not said; ask the clinician instead.
- Severity: high = could harm the patient if signed as is; medium = clinically relevant gap or error; low = minor.
- Set section to the note heading the issue belongs to, or "" for the note as a whole.
- Report at most 8 findings, most severe first. If the note is accurate and complete, return an empty list. \
Do not report style or wording preferences."""


def _format_note(note: GeneratedNote) -> str:
    lines = []
    for section in note.sections:
        lines.append(f"## {section.heading}")
        for st in section.statements:
            source = (
                f"[segments {', '.join(map(str, st.source_segment_ids))}]"
                if st.source_segment_ids
                else "[clinician-added]"
            )
            lines.append(f"- {st.text} {source}")
        if not section.statements:
            lines.append("- (empty)")
    return "\n".join(lines)


async def review_note(
    generator: NoteGenerator, transcript: Transcript, note: GeneratedNote, clinician_speaker: int, effort: str
) -> NoteReview:
    user = (
        f"Transcript (segment id in brackets):\n{format_transcript(transcript, clinician_speaker)}\n\n"
        f"Note to review:\n{_format_note(note)}"
    )
    review = await generator.complete(REVIEW_PROMPT, user, NoteReview, effort=effort)
    valid = {s.id for s in transcript.segments}
    for f in review.findings:
        f.source_segment_ids = [i for i in f.source_segment_ids if i in valid]
    order = {"high": 0, "medium": 1, "low": 2}
    review.findings.sort(key=lambda f: order[f.severity])
    return review
