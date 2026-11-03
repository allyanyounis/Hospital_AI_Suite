"""Clinical codes and task lists, derived from the note (the signed note when there is one, else the draft).

Both are suggestions for the clinician: codes must be verified before billing, tasks are a checklist they own.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

from .base import GeneratedNote, NoteGenerator, note_to_text

# ICD-10-CM shape: letter, digit, alphanumeric, optional dot + up to 4 alphanumerics (e.g. I21.4, R07.9, Z95.5)
ICD10_PATTERN = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$")


class ClinicalCode(BaseModel):
    code: str
    description: str
    kind: Literal["primary", "secondary", "symptom", "history"]
    confidence: Literal["high", "medium", "low"]
    # Short quote from the note that justifies the code
    evidence: str


class ClinicalCodes(BaseModel):
    codes: list[ClinicalCode]


class CareTask(BaseModel):
    title: str
    detail: str = ""
    category: Literal["test", "medication", "referral", "follow_up", "patient_advice", "admin"]
    owner: Literal["clinician", "nurse", "patient", "admin"]
    # Timing exactly as the note states it ("in 2 weeks", "today"); empty when not stated
    due: str = ""
    done: bool = False


class TaskList(BaseModel):
    tasks: list[CareTask]


class SavedCodes(BaseModel):
    codes: list[ClinicalCode] = Field(default_factory=list)
    source: Literal["draft", "signed"]
    generated_at: str


class SavedTasks(BaseModel):
    tasks: list[CareTask] = Field(default_factory=list)
    source: Literal["draft", "signed"]
    generated_at: str


CODES_PROMPT = """You are a clinical coding assistant. From a clinical note, suggest ICD-10-CM codes for the \
encounter, for a human coder to verify.

Rules:
- Code only what the note documents. Never code a diagnosis the note does not state; when the note gives only a \
symptom or a suspected / "rule out" diagnosis, code the symptom (outpatient rules), not the suspected condition.
- One "primary" code: the main reason for the encounter. Then "secondary" codes for other documented active \
conditions, "symptom" codes for documented symptoms not explained by a coded diagnosis, and "history" codes \
(Z codes) for relevant history or status such as previous MI or stents.
- Use the most specific valid ICD-10-CM code the documentation supports, with its official short description.
- confidence: high when the documentation clearly supports that exact code, medium when a more specific code \
might apply with more detail, low when the documentation is thin.
- evidence: a short quote (max ~15 words) copied from the note that supports the code.
- Return an empty list if nothing codeable is documented."""

TASKS_PROMPT = """You turn a clinical note into a follow-up task list for the care team and patient.

Rules:
- Only include actions the note states or directly implies from its plan: tests to order or chase, medicines to \
start / stop / change, referrals, follow-up appointments, advice the patient must act on, and admin (letters, \
forms, fit notes). Never invent an action the note does not support.
- Copy medicine names, doses and frequencies exactly as written; never calculate or change a dose.
- title: a short imperative, e.g. "Order high-sensitivity troponin". detail: one line of specifics from the note.
- owner: who does it (clinician, nurse, patient, admin). due: timing exactly as stated in the note, else empty.
- Return an empty list if the note contains no actions."""


async def suggest_codes(generator: NoteGenerator, note: GeneratedNote) -> list[ClinicalCode]:
    result = await generator.complete(CODES_PROMPT, f"Clinical note:\n{note_to_text(note)}", ClinicalCodes)
    seen: set[str] = set()
    codes = []
    for c in result.codes:
        c.code = c.code.strip().upper()
        # Drop anything that isn't shaped like an ICD-10-CM code, and duplicates
        if ICD10_PATTERN.match(c.code) and c.code not in seen:
            seen.add(c.code)
            codes.append(c)
    order = {"primary": 0, "secondary": 1, "symptom": 2, "history": 3}
    codes.sort(key=lambda c: order[c.kind])
    # Exactly one primary: demote extras, promote the first if the model gave none
    primaries = [c for c in codes if c.kind == "primary"]
    for c in primaries[1:]:
        c.kind = "secondary"
    if codes and not primaries:
        codes[0].kind = "primary"
    return codes


async def suggest_tasks(generator: NoteGenerator, note: GeneratedNote) -> list[CareTask]:
    result = await generator.complete(TASKS_PROMPT, f"Clinical note:\n{note_to_text(note)}", TaskList)
    tasks = [t for t in result.tasks if t.title.strip()]
    for t in tasks:
        t.done = False
    return tasks
