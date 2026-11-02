"""Follow-on documents written from the clinician-approved note (the approved note is the source of truth)."""

from pydantic import BaseModel

from .base import GeneratedNote, NoteGenerator, note_to_text


class DocumentType(BaseModel):
    id: str
    name: str
    description: str
    instructions: str


class GeneratedDocument(BaseModel):
    title: str
    paragraphs: list[str]


DOCUMENT_TYPES: dict[str, DocumentType] = {
    d.id: d
    for d in [
        DocumentType(
            id="patient_summary",
            name="Patient visit summary",
            description="Plain-language summary the patient takes home.",
            instructions="Write to the patient as 'you', at roughly a 12-year-old's reading level, with no jargon or "
            "abbreviations (explain any medical word you must use). Cover: why they came, what was found, what it "
            "probably is, what happens next (tests, medicines with how to take them, referrals, follow-up), and "
            "when to seek help urgently. Short paragraphs; start each with a plain heading followed by a colon.",
        ),
        DocumentType(
            id="referral_letter",
            name="Referral letter",
            description="Letter to a specialist service requesting review.",
            instructions="Formal clinician-to-clinician referral letter. Address it to the specialty named in the "
            "plan (or [Specialty] if none is named). Include: reason for referral and the question being asked, "
            "relevant history, examination and results, current medications and allergies, what has been done so "
            "far, and urgency. Concise clinical style.",
        ),
        DocumentType(
            id="gp_letter",
            name="GP / discharge letter",
            description="Summary for the patient's family doctor after the visit.",
            instructions="Letter to the patient's GP summarising the encounter: presentation, key findings, "
            "diagnosis or impression, treatment given, medication changes, follow-up actions requested of the GP, "
            "and advice given to the patient. Concise clinical style.",
        ),
    ]
}

DOCUMENT_PROMPT = """You write clinical correspondence from a clinician-approved note. Use only facts in the note: \
never add diagnoses, results, doses or plans. Never calculate, convert or round a dose (e.g. mg/kg into mg): copy \
medicine names, doses, frequencies and durations exactly as the note states them, explaining in plain words only \
what the note says. Where a letter needs a detail that is not in the note (names, \
dates of birth, addresses, hospital numbers, the sender's details), write a placeholder in square brackets such as \
[Patient name] for the clinician to fill in. Return a short title and the document body as paragraphs; put \
salutation and sign-off in their own paragraphs."""


async def write_document(generator: NoteGenerator, doc_type: DocumentType, note: GeneratedNote) -> GeneratedDocument:
    user = f"Document: {doc_type.name}\nInstructions: {doc_type.instructions}\n\nApproved note:\n{note_to_text(note)}"
    return await generator.complete(DOCUMENT_PROMPT, user, GeneratedDocument)
