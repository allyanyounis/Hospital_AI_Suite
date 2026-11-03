/** AI medical scribe. */

import { http } from "./client";

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

const enc = (id: string) => `/api/encounters/${id}`;

export const scribeApi = {
  // Reference data
  templates: () => http.get<NoteTemplate[]>("/api/templates"),
  documentTypes: () => http.get<DocumentType[]>("/api/document-types"),
  samples: () => http.get<Sample[]>("/api/samples"),

  // Encounters
  encounters: () => http.get<EncounterSummary[]>("/api/encounters"),
  encounter: (id: string) => http.get<EncounterDetail>(enc(id)),
  startFromSample: (sampleId: string) => http.post<Encounter>("/api/encounters/sample", { sample_id: sampleId }),
  startFromRecording: (audio: Blob) => {
    const form = new FormData();
    form.append("audio", audio, `recording.${audio.type.includes("mp4") ? "mp4" : "webm"}`);
    return http.upload<Encounter>("/api/encounters/recording", form);
  },
  setPatient: (id: string, patient: Patient) => http.put<{ ok: boolean }>(`${enc(id)}/patient`, patient),
  startDraft: (id: string, templateId: string, clinicianSpeaker: number) =>
    http.post<{ status: string }>(`${enc(id)}/note/start`, { template_id: templateId, clinician_speaker: clinicianSpeaker }),
  reviewNote: (id: string, note: Note) => http.post<{ findings: Finding[] }>(`${enc(id)}/review`, { note }),
  approveNote: (id: string, note: Note) => http.post(`${enc(id)}/approve`, { note }),
  document: (id: string, typeId: string) => http.post<GeneratedDocument>(`${enc(id)}/documents`, { type_id: typeId }),
  generateCodes: (id: string) => http.post<SavedCodes>(`${enc(id)}/codes`),
  saveCodes: (id: string, codes: SavedCodes) => http.put<SavedCodes>(`${enc(id)}/codes`, codes),
  generateTasks: (id: string) => http.post<SavedTasks>(`${enc(id)}/tasks`),
  saveTasks: (id: string, tasks: SavedTasks) => http.put<SavedTasks>(`${enc(id)}/tasks`, tasks),

  // Pilot metrics
  metrics: (all: boolean) => http.get<Metrics>(all ? "/api/metrics/all" : "/api/metrics"),
};
