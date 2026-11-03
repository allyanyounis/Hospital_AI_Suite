import { http } from "@/shared/api/http";
import type { Page } from "@/shared/api/pagination";
import type { ExperimentInput, ExperimentRun, ExperimentSummary, ModelAudit } from "./insightsTypes";
import type {
  ActionInput,
  Board,
  CaseAction,
  CaseDetail,
  CaseInput,
  Calendar,
  IntakeInput,
  IntakePreview,
  LeaveConflict,
  OffListCase,
  PatientCase,
  Procedure,
  RosterDay,
  Slot,
  Surgeon,
  Theatre,
  Urgency,
} from "./types";

const BASE = "/api/theatre";

function query(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v != null && v !== "") q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** `at` is the admin demo clock (minutes after midnight) or null for real time. */
export const theatreApi = {
  board: (day: string | null, at: number | null) => http.get<Board>(`${BASE}/board${query({ day, at })}`),
  waiting: (urgency: Urgency | "", cursor: string | null) =>
    http.get<Page<OffListCase>>(`${BASE}/waiting${query({ urgency, cursor })}`),
  deferred: (cursor: string | null) => http.get<Page<OffListCase>>(`${BASE}/deferred${query({ cursor })}`),
  calendar: (start: string | null, procedure: string, surgeonId: number | null) =>
    http.get<Calendar>(`${BASE}/calendar${query({ start, procedure, surgeon_id: surgeonId })}`),
  caseDetail: (id: number, at: number | null) => http.get<CaseDetail>(`${BASE}/cases/${id}${query({ at })}`),
  patientCases: (patientId: number) => http.get<PatientCase[]>(`${BASE}/patients/${patientId}/cases`),
  theatres: () => http.get<Theatre[]>(`${BASE}/theatres`),
  procedures: () => http.get<Procedure[]>(`${BASE}/procedures`),
  surgeons: () => http.get<Surgeon[]>(`${BASE}/surgeons`),

  book: (input: CaseInput) => http.post<{ case: number }>(`${BASE}/cases`, input),
  act: (id: number, action: CaseAction, input: ActionInput = {}, at: number | null = null) =>
    http.post<{ ok: true }>(`${BASE}/cases/${id}/${action}${query({ at })}`, input),
  intakePreview: (input: IntakeInput, at: number | null) =>
    http.post<IntakePreview>(`${BASE}/intake/preview${query({ at })}`, input),
  intakeConfirm: (input: IntakeInput, at: number | null) =>
    http.post<{ case: number; slot: Slot }>(`${BASE}/intake/confirm${query({ at })}`, input),

  saveRoster: (staffId: number, days: RosterDay[]) => http.put<{ ok: true }>(`${BASE}/surgeons/${staffId}/roster`, { days }),
  addLeave: (input: { staff_id: number; starts_on: string; ends_on: string; reason: string }) =>
    http.post<{ id: number; conflicts: LeaveConflict[] }>(`${BASE}/leave`, input),
  deleteLeave: (id: number) => http.delete<{ ok: true }>(`${BASE}/leave/${id}`),

  modelAudit: () => http.get<ModelAudit>(`${BASE}/insights/model-audit`),
  experiment: () => http.get<ExperimentSummary>(`${BASE}/insights/experiment`),
  runExperiment: (input: ExperimentInput) => http.post<ExperimentRun>(`${BASE}/insights/experiment/run`, input),
};

/** React Query keys; all start with "theatre" so the live `theatre_updated` event refreshes them. */
export const theatreKeys = {
  all: ["theatre"] as const,
  board: (day: string | null, at: number | null) => ["theatre", "board", day, at] as const,
  waiting: (urgency: string) => ["theatre", "waiting", urgency] as const,
  deferred: () => ["theatre", "deferred"] as const,
  calendar: (start: string | null, procedure: string, surgeonId: number | null) =>
    ["theatre", "calendar", start, procedure, surgeonId] as const,
  case: (id: number, at: number | null) => ["theatre", "case", id, at] as const,
  patientCases: (patientId: number) => ["theatre", "patient", patientId] as const,
  theatres: () => ["theatre", "theatres"] as const,
  procedures: () => ["theatre", "procedures"] as const,
  surgeons: () => ["theatre", "surgeons"] as const,
  modelAudit: () => ["theatre", "insights", "model-audit"] as const,
  experiment: () => ["theatre", "insights", "experiment"] as const,
};
