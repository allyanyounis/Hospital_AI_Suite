/** Data contracts shared with the FastAPI backend. */

// --- Session -----------------------------------------------------------------------------------------------------

export type User = { username: string; display_name: string; role: "clinician" | "admin" };

export type AppConfig = {
  environment_banner: string;
  retention_days: number;
  clinic_timezone: string;
  transcriber: string;
  transcriber_ready: boolean;
  note_model: string;
  notes_ready: boolean;
};

// --- Clinic schedule (shared by both modules) --------------------------------------------------------------------

export type BreakPeriod = { start: string; end: string }; // "HH:MM"
export type DaySchedule = { enabled: boolean; start: string; end: string; breaks: BreakPeriod[] };
export type ClinicScheduleInput = { days: DaySchedule[]; slot_minutes: number; holidays: string[] };
export type ClinicSchedule = ClinicScheduleInput & { is_default: boolean; updated_at: string | null };

// --- AI receptionist ---------------------------------------------------------------------------------------------

export type Appointment = {
  id: number;
  patient_name: string;
  reason: string | null;
  start_time: string;
  canceled: boolean;
  created_at: string;
  /** "AI: ..." / "User: ..." lines; null if not booked by a voice call */
  transcript: string | null;
};

export type LiveEvent = "appointment_booked" | "appointment_canceled" | "transcript_saved" | "schedule_updated";

// --- AI scribe ---------------------------------------------------------------------------------------------------

export type Segment = { id: number; speaker: number; start: number; end: number; text: string };
export type Transcript = { segments: Segment[]; provider: string; duration: number | null };
export type Encounter = { id: string; transcript: Transcript };
export type Sample = { id: string; title: string };

export type NoteTemplate = {
  id: string;
  name: string;
  description: string;
  sections: { heading: string; guidance: string }[];
};

export type NoteStatement = { text: string; source_segment_ids: number[] };
export type NoteSection = { heading: string; statements: NoteStatement[] };
export type Note = { sections: NoteSection[] };

export type Finding = {
  category: "unsupported" | "missing" | "inconsistency" | "safety";
  severity: "high" | "medium" | "low";
  message: string;
  section: string;
  source_segment_ids: number[];
};

export type DocumentType = { id: string; name: string; description: string };
export type GeneratedDocument = { title: string; paragraphs: string[] };

export type Patient = { name: string; mrn: string; sex: string; dob: string; visit_type: string };
export const EMPTY_PATIENT: Patient = { name: "", mrn: "", sex: "", dob: "", visit_type: "" };

/** pending = transcript only · drafting = note being written · ready = to review · signed = approved */
export type PipelineStatus = "pending" | "drafting" | "ready" | "failed" | "signed";

export type EncounterSummary = {
  id: string;
  created_at: string;
  source: "live" | "recording" | "sample" | string;
  audio_seconds: number | null;
  template_id: string | null;
  clinician_speaker: number;
  status: PipelineStatus;
  error: string | null;
  approved_at: string | null;
  purged: boolean;
  patient: Patient;
};

export type ClinicalCode = {
  code: string;
  description: string;
  kind: "primary" | "secondary" | "symptom" | "history";
  confidence: "high" | "medium" | "low";
  evidence: string;
};
export type SavedCodes = { codes: ClinicalCode[]; source: "draft" | "signed"; generated_at: string };

export type TaskCategory = "test" | "medication" | "referral" | "follow_up" | "patient_advice" | "admin";
export type CareTask = {
  title: string;
  detail: string;
  category: TaskCategory;
  owner: "clinician" | "nurse" | "patient" | "admin";
  due: string;
  done: boolean;
};
export type SavedTasks = { tasks: CareTask[]; source: "draft" | "signed"; generated_at: string };

export type EncounterDetail = EncounterSummary & {
  transcript: Transcript;
  draft_note: Note | null;
  final_note: Note | null;
  codes: SavedCodes | null;
  tasks: SavedTasks | null;
};

export type Metrics = {
  scope: "me" | "all";
  days: number;
  baseline_minutes_per_note: number;
  workday: string;
  encounters: number;
  notes_approved: number;
  median_draft_seconds: number | null;
  median_review_minutes: number | null;
  lines_kept_pct: number | null;
  est_minutes_saved: number;
  after_hours_approvals: number;
  reviews_run: number;
  documents_generated: number;
  by_day: { date: string; approved: number }[];
  by_clinician?: { username: string; name: string; notes_approved: number }[];
};

export type LiveMessage =
  | { type: "ready" }
  | { type: "interim"; text: string; speaker: number | null }
  | { type: "segment"; segment: Segment }
  | { type: "encounter"; encounter: Encounter }
  | { type: "empty" }
  | { type: "error"; message: string };
