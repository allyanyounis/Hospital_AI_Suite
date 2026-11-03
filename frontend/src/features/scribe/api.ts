import { http } from "@/shared/api/http";
import type {
  DocumentType,
  Encounter,
  EncounterDetail,
  EncounterSummary,
  Finding,
  GeneratedDocument,
  Metrics,
  Note,
  NoteTemplate,
  Patient,
  Sample,
  SavedCodes,
  SavedTasks,
} from "./types";

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
