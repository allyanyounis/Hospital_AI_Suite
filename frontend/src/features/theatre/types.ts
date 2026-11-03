/**
 * Operating theatre data contracts (FastAPI /api/theatre). Planner responses are the backend planner's
 * dictionaries as they are (backend/app/modules/theatre/engine/planner.py). Times of day are minutes after
 * midnight (480 = 08:00); dates are "YYYY-MM-DD".
 */

export type Urgency = "immediate" | "urgent" | "expedited" | "elective";
export const URGENCIES: Urgency[] = ["immediate", "urgent", "expedited", "elective"];

/** NCEPOD categories with their target time to theatre */
export const URGENCY_INFO: Record<Urgency, { label: string; target: string }> = {
  immediate: { label: "Immediate", target: "within 1 hour" },
  urgent: { label: "Urgent", target: "within 6 hours" },
  expedited: { label: "Expedited", target: "within 3 days" },
  elective: { label: "Elective", target: "first free slot" },
};

export type PhaseKey = "induction" | "lead_in" | "incision" | "lead_out" | "emergence";
export type Phase = { key: PhaseKey; label: string; start: number; end: number };

/** "done" finished, "in" in theatre now, "wait" not started */
export type CaseState = "done" | "in" | "wait";

/** One case on a theatre's list for the day */
export type BoardCase = {
  id: number;
  seq: number;
  patient_id: number;
  name: string;
  age: number;
  sex: string;
  asa: number;
  allergies: string;
  procedure: string;
  code: string;
  urgency: Urgency;
  deferred: boolean;
  surgeon_id: number | null;
  surgeon: string | null;
  /** Why the surgeon's hours don't cover the case, or null */
  rota: string | null;
  /** Start on the original plan (planned durations) */
  booked: number;
  start: number;
  end: number;
  planned_min: number;
  variance: number;
  /** 90th-percentile finish */
  latest: number;
  overrun: number;
  phases: Phase[];
  state: CaseState;
  /** Phase label now, for the case in theatre */
  phase: string | null;
  /** Chance of starting more than 30 min after `booked` (waiting cases) */
  late_pct: number;
  delay_min?: number;
  /** In theatre only */
  remain_min?: number;
  extra_min?: number;
  overrun_pct?: number;
  finish_p90?: number;
  risk: number;
  risk_model: string;
  risk_high: boolean;
};

export type Forecast = { over_pct: number; expected_over: number; finish_p90: number };

/** Where a case taken off a list should go */
export type Move = {
  case: number;
  name: string;
  procedure: string;
  date: string;
  slot_start: number;
  slot_end: number;
  room: number;
  surgeon_id: number | null;
  surgeon: string | null;
  same_surgeon: boolean;
  /** The surgeon's hours that day */
  hours: [number, number] | null;
  minutes: number;
  /** How the duration was estimated */
  source: string;
  /** "Safe" chance of overtime, % */
  threshold: number;
  dest: { over_pct: number; expected_over: number };
  /** A sooner day that is less safe */
  alt: { day: string; start: number; over_pct: number; expected_over: number } | null;
  /** A quieter later day */
  later: { day: string; over_pct: number } | null;
  /** This room's chance of overtime after the move */
  over_pct: number;
};

/** A room's move tip: the Move plus the room's forecast after it */
export type Suggestion = Omit<Move, "over_pct"> & { booked: number; after: Forecast };

export type Room = {
  id: number;
  code: string;
  name: string;
  specialty: string;
  cleaning: number;
  cases: BoardCase[];
  finish: number;
  overtime: number;
  forecast: Forecast;
  suggestion: Suggestion | null;
  /** A weaker tip shown when there is no suggestion */
  nudge: Suggestion | null;
};

export type Slot = {
  day: string;
  room: number;
  start: number;
  /** Today: minutes from now, the urgency target and whether it is met */
  wait?: number;
  target?: number;
  /** Later day: target in days */
  target_days?: number | null;
  met: boolean;
};

/** Where a waiting Immediate/Urgent case would go now (nothing changed yet) */
export type Proposal = {
  case: number;
  name: string;
  age: number;
  asa: number;
  urgency: Urgency;
  procedure: string;
  planned_min: number;
  slot: Pick<Slot, "day" | "room" | "start" | "wait" | "met">;
  pushed: { case: number; name: string; from: number; to: number; urgency: Urgency }[];
  move: Move | null;
  before_over: number;
  after_over: number;
};

export type Board = {
  today: string;
  day: string;
  /** The clock the day is played at */
  now: number;
  open: number;
  close: number;
  rooms: Room[];
  /** Today only */
  proposals?: Proposal[];
  waiting: number;
  urgent_waiting: number;
  later: number;
};

/** A case on the waiting list or moved to a later day */
export type OffListCase = {
  id: number;
  patient_id: number;
  name: string;
  code: string;
  procedure: string;
  specialty: string;
  minutes: number;
  theatre_id: number;
  day: string | null;
  urgency: Urgency;
  surgeon_id: number | null;
  surgeon: string | null;
  listed_at: string;
};

export type RiskFactor = { label: string; value: number | string; unit: string; push: number };
export type Risk = { pct: number; factors: RiskFactor[]; model: string; outcome: string; average: number };

export type Cardiac = {
  lvef?: number | null;
  nyha?: number | null;
  pa_systolic?: number | null;
  ccs4?: boolean;
  iddm?: boolean;
  recent_mi?: boolean;
  redo?: boolean;
  lung?: boolean;
  arteriopathy?: boolean;
  poor_mobility?: boolean;
  dialysis?: boolean;
  endocarditis?: boolean;
  critical?: boolean;
};

export type CaseDetail = {
  id: number;
  patient: { id: number; name: string; age: number; sex: string; allergies: string; labs: Record<string, number> };
  procedure: { code: string; title: string; specialty: string; minutes: number; source: string; risk_model: string };
  phases: { key: PhaseKey; label: string; minutes: number }[];
  room: { id: number; code: string };
  day: string | null;
  seq: number;
  urgency: Urgency;
  deferred: boolean;
  overrun: number;
  surgeon_id: number | null;
  surgeon: string | null;
  preop: { asa: number; weight_kg: number | null; height_cm: number | null; cardiac: Cardiac | null };
  /** The case's row on its list, when listed */
  timing: BoardCase | null;
  risk: Risk;
  today: string;
};

export type PatientCase = {
  id: number;
  procedure: string;
  code: string;
  theatre: string | null;
  day: string | null;
  urgency: Urgency;
  deferred: boolean;
  canceled: boolean;
};

export type Fit =
  | { day: string; room: number; start: number; end: number; surgeon_id: number; surgeon: string }
  | { day: string; room: number | null; reason: string };

export type CalendarCell = {
  room: number;
  code: string;
  cases: number;
  free: number;
  used_pct: number;
  /** "Name 08:00–16:00" per rostered surgeon of the room's specialty */
  staff: string[];
  /** Only with a procedure, for rooms of its specialty */
  fit?: Fit;
};

export type Calendar = {
  today: string;
  start: string;
  days: { day: string; past: boolean; rooms: CalendarCell[] }[];
};

export type RosterDay = { weekday: number; start: number; end: number };
export type Leave = { id: number; starts_on: string; ends_on: string; reason: string };

export type Surgeon = {
  id: number;
  name: string;
  specialty: string;
  active: boolean;
  days: RosterDay[];
  /** Current and future leave */
  leave: Leave[];
  /** Listed cases from today on */
  booked: number;
};

export type LeaveConflict = {
  case: number;
  day: string;
  name: string;
  procedure: string;
  cover: { id: number; name: string } | null;
  later: { day: string; start: number; surgeon_id: number | null } | null;
};

export type Theatre = { id: number; code: string; name: string; specialty: string; cleaning_minutes: number };
export type Procedure = { code: string; title: string; specialty: string; minutes: number; risk_model: string };

export type CaseAction =
  | "earlier"
  | "later"
  | "book"
  | "schedule"
  | "unschedule"
  | "defer"
  | "cancel"
  | "overrun"
  | "surgeon"
  | "urgency";

export type ActionInput = { day?: string; surgeon_id?: number; minutes?: number; urgency?: Urgency };

export type NewPatientInput = { name: string; age: number; sex: string; allergies: string };

export type CaseInput = {
  procedure_code: string;
  urgency: Urgency;
  day?: string | null;
  surgeon_id?: number | null;
  patient_id?: number;
  patient?: NewPatientInput;
  asa: number;
  weight_kg?: number | null;
  height_cm?: number | null;
  cardiac?: Cardiac | null;
};

export type IntakeInput = Partial<Omit<CaseInput, "day">> & {
  case_id?: number;
  moves?: { case: number; date: string; surgeon_id?: number | null }[];
};

export type IntakeOutlook = { over_pct: number; expected_over: number; finish: number };

export type IntakePreview = {
  case: number;
  name: string;
  procedure: string;
  urgency: Urgency;
  slot: Slot;
  /** Today's room before the case, when it goes in today */
  before: IntakeOutlook | null;
  after: IntakeOutlook;
  with_moves: IntakeOutlook;
  moves: Move[];
};
