import { http } from "@/shared/api/http";
import type { Page } from "@/shared/api/pagination";
import type {
  ClinicalSummary,
  HistoryEntry,
  LabResult,
  LabTest,
  Report,
  ReportKind,
  ReportListItem,
  SeriesPoint,
  VitalSigns,
} from "./types";

const base = (patientId: number) => `/api/clinical/patients/${patientId}`;

function query(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v != null && v !== "") q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const clinicalApi = {
  labTests: () => http.get<LabTest[]>("/api/clinical/lab-tests"),
  summary: (patientId: number) => http.get<ClinicalSummary>(`${base(patientId)}/summary`),
  labs: (patientId: number, test: string, cursor: string | null) =>
    http.get<Page<LabResult>>(`${base(patientId)}/labs${query({ test, cursor, limit: 50 })}`),
  series: (patientId: number, test: string) =>
    http.get<SeriesPoint[]>(`${base(patientId)}/labs/series${query({ test })}`),
  vitals: (patientId: number, cursor: string | null) =>
    http.get<Page<VitalSigns>>(`${base(patientId)}/vitals${query({ cursor, limit: 50 })}`),
  reports: (patientId: number, kind: ReportKind | "", cursor: string | null) =>
    http.get<Page<ReportListItem>>(`${base(patientId)}/reports${query({ kind, cursor })}`),
  report: (reportId: number) => http.get<Report>(`/api/clinical/reports/${reportId}`),
  history: (patientId: number) => http.get<HistoryEntry[]>(`${base(patientId)}/history`),
};

/** React Query keys; all start with "clinical" so live theatre updates refresh them. */
export const clinicalKeys = {
  all: ["clinical"] as const,
  labTests: () => ["clinical", "lab-tests"] as const,
  summary: (patientId: number) => ["clinical", patientId, "summary"] as const,
  labs: (patientId: number, test: string) => ["clinical", patientId, "labs", test] as const,
  series: (patientId: number, test: string) => ["clinical", patientId, "series", test] as const,
  vitals: (patientId: number) => ["clinical", patientId, "vitals"] as const,
  reports: (patientId: number, kind: string) => ["clinical", patientId, "reports", kind] as const,
  report: (reportId: number) => ["clinical", "report", reportId] as const,
  history: (patientId: number) => ["clinical", patientId, "history"] as const,
};
