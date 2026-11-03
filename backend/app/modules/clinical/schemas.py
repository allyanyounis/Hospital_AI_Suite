"""Response bodies of the clinical data API."""

from datetime import date, datetime

from pydantic import BaseModel


class LabTestOut(BaseModel):
    id: int
    code: str
    name: str
    unit: str
    ref_low: float
    ref_high: float
    category: str

    @classmethod
    def of(cls, t) -> "LabTestOut":
        return cls(
            id=t.id, code=t.code, name=t.name, unit=t.unit, ref_low=t.ref_low, ref_high=t.ref_high, category=t.category
        )


class LabResultOut(BaseModel):
    id: int
    test: str  # code
    name: str
    unit: str
    value: float
    flag: str
    collected_at: datetime

    @classmethod
    def of(cls, r) -> "LabResultOut":
        return cls(
            id=r.id,
            test=r.test.code,
            name=r.test.name,
            unit=r.test.unit,
            value=r.value,
            flag=r.flag,
            collected_at=r.collected_at,
        )


class LabLatest(BaseModel):
    """The newest result of one test, with the one before it for the trend."""

    test: str
    name: str
    unit: str
    category: str
    ref_low: float
    ref_high: float
    value: float
    flag: str
    collected_at: datetime
    previous: float | None = None
    previous_at: datetime | None = None
    trend: str = ""  # "up", "down", "same" or "" without a previous result


class SeriesPoint(BaseModel):
    at: datetime
    value: float


class VitalSignsOut(BaseModel):
    id: int
    recorded_at: datetime
    heart_rate: int | None
    systolic_bp: int | None
    diastolic_bp: int | None
    spo2: int | None
    temperature_c: float | None
    resp_rate: int | None
    flags: dict[str, str]  # measurement -> "low" | "high", only for those out of range

    @classmethod
    def of(cls, v, flags: dict[str, str]) -> "VitalSignsOut":
        return cls(
            id=v.id,
            recorded_at=v.recorded_at,
            heart_rate=v.heart_rate,
            systolic_bp=v.systolic_bp,
            diastolic_bp=v.diastolic_bp,
            spo2=v.spo2,
            temperature_c=v.temperature_c,
            resp_rate=v.resp_rate,
            flags=flags,
        )


class VitalRange(BaseModel):
    key: str
    label: str
    unit: str
    low: float
    high: float


class ReportListItem(BaseModel):
    id: int
    kind: str
    title: str
    reported_on: date
    author: str
    excerpt: str

    @classmethod
    def of(cls, r) -> "ReportListItem":
        excerpt = r.body if len(r.body) <= 140 else r.body[:137].rstrip() + "…"
        return cls(
            id=r.id, kind=r.kind, title=r.title, reported_on=r.reported_on, author=r.author or "", excerpt=excerpt
        )


class ReportOut(ReportListItem):
    patient_id: int
    body: str

    @classmethod
    def of(cls, r) -> "ReportOut":
        base = ReportListItem.of(r).model_dump()
        return cls(**base, patient_id=r.patient_id, body=r.body)


class HistoryOut(BaseModel):
    id: int
    kind: str
    noted_on: date
    text: str

    @classmethod
    def of(cls, h) -> "HistoryOut":
        return cls(id=h.id, kind=h.kind, noted_on=h.noted_on, text=h.text)


class AllergyOut(BaseModel):
    id: int
    substance: str
    reaction: str
    severity: str

    @classmethod
    def of(cls, a) -> "AllergyOut":
        return cls(id=a.id, substance=a.substance, reaction=a.reaction or "", severity=a.severity)


class ClinicalSummary(BaseModel):
    """Everything the chart's overview needs in one call."""

    patient_id: int
    labs: list[LabLatest]
    out_of_range: int  # latest lab results outside their reference range
    vitals: VitalSignsOut | None
    previous_vitals: VitalSignsOut | None
    vital_ranges: list[VitalRange]
    allergies: list[AllergyOut]
    report_counts: dict[str, int]  # kind -> number of reports
    history_count: int
