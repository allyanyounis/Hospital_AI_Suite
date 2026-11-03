"""An in-memory picture of the theatre lists: rooms, operations, surgeons, patients and every open case.

The planner reads and changes a snapshot, never the database. The service loads one, lets the planner work on it,
and writes back only the cases that changed; a preview works on a copy that is thrown away.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date

PHASES = (
    ("induction", "Anaesthesia induction"),
    ("lead_in", "Positioning and prep"),
    ("incision", "Surgery"),
    ("lead_out", "Closing up"),
    ("emergence", "Anaesthesia emergence"),
)


@dataclass(frozen=True)
class Room:
    id: int
    code: str
    name: str
    specialty: str
    cleaning: int


@dataclass(frozen=True)
class Proc:
    code: str
    title: str
    specialty: str
    phases: tuple[int, int, int, int, int]  # minutes, in PHASES order
    variance: float
    risk_model: str
    euro_weight: int | None
    aorta: bool
    source: str

    @property
    def minutes(self) -> int:
        return sum(self.phases)


@dataclass
class Leave:
    id: int
    starts_on: date
    ends_on: date
    reason: str


@dataclass
class Surgeon:
    id: int
    name: str
    specialty: str
    active: bool
    days: dict[int, tuple[int, int]] = field(default_factory=dict)  # weekday -> (start, end) minutes
    leave: list[Leave] = field(default_factory=list)


@dataclass
class Person:
    id: int
    name: str
    sex: str  # "F", "M" or ""
    age: int
    allergies: str
    labs: dict[str, float] = field(default_factory=dict)  # lab test code -> newest value


@dataclass
class Case:
    id: int  # negative until saved
    patient_id: int
    code: str
    room_id: int
    day: date | None  # None: on the waiting list
    seq: int
    urgency: str
    overrun: int = 0
    surgeon_id: int | None = None
    deferred: bool = False
    asa: int = 2
    weight_kg: float | None = None
    height_cm: float | None = None
    cardiac: dict | None = None  # EuroSCORE II inputs

    STORED = ("room_id", "day", "seq", "urgency", "overrun", "surgeon_id", "deferred")

    def stored(self) -> tuple:
        return tuple(getattr(self, name) for name in self.STORED)


@dataclass
class Snapshot:
    today: date
    rooms: list[Room]  # in board order
    procs: dict[str, Proc]
    surgeons: dict[int, Surgeon]
    patients: dict[int, Person]
    cases: dict[int, Case]
    canceled: set[int] = field(default_factory=set)
    new_patients: dict[int, dict] = field(default_factory=dict)  # temp id -> full_name, sex, age, allergies
    new_history: list[tuple[int, str, date, str]] = field(default_factory=list)  # (patient, kind, day, text)
    _next_id: int = -1

    def temp_id(self) -> int:
        self._next_id -= 1
        return self._next_id

    def room(self, room_id: int) -> Room:
        return next(r for r in self.rooms if r.id == room_id)

    def copy(self) -> Snapshot:
        return copy.deepcopy(self)
