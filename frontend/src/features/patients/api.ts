import { http } from "@/shared/api/http";
import type { PatientInput, PatientRecord } from "./types";

export const patientsApi = {
  /** Up to 50 matches on name, MRN or phone; newest first when `q` is empty */
  search: (q = "") => http.get<PatientRecord[]>(`/api/patients${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ""}`),
  get: (id: number) => http.get<PatientRecord>(`/api/patients/${id}`),
  register: (patient: PatientInput) => http.post<PatientRecord>("/api/patients", patient),
  update: (id: number, change: Partial<PatientInput>) => http.patch<PatientRecord>(`/api/patients/${id}`, change),
};
