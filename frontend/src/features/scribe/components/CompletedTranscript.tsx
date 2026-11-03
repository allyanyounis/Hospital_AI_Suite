import { formatDuration as formatTime } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Avatar, Card, Spinner } from "@/shared/ui/ui";
import type { Encounter, NoteTemplate, Patient } from "../types";
import { PatientForm } from "./PatientForm";

export function CompletedTranscript({
  encounter,
  source,
  clinicianSpeaker,
  onSwapSpeakers,
  patient,
  onPatientChange,
  templates,
  templateId,
  onTemplateChange,
  generating,
  notesReady,
  onGenerate,
  onBack,
}: {
  encounter: Encounter;
  source: string;
  clinicianSpeaker: number;
  onSwapSpeakers: () => void;
  patient: Patient;
  onPatientChange: (p: Patient) => void;
  templates: NoteTemplate[];
  templateId: string;
  onTemplateChange: (id: string) => void;
  generating: boolean;
  notesReady: boolean;
  onGenerate: () => void;
  onBack: () => void;
}) {
  const { transcript } = encounter;
  const speakers = new Set(transcript.segments.map((s) => s.speaker));
  const duration = transcript.duration ?? transcript.segments.at(-1)?.end ?? 0;
  const sourceLabel = source === "live" ? "Live session" : source === "sample" ? "Sample consultation" : "Uploaded audio";

  return (
    <>
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={onBack}
          title="Start a new session"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
        >
          <Icons.ArrowLeft />
        </button>
        <Icons.CheckCircle className="h-5 w-5 text-brand-700" />
        <h2 className="text-2xl font-semibold text-slate-900">Completed Transcript</h2>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <Card className="flex min-h-[460px] flex-col overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                <Icons.Mic />
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">Transcript</p>
                <p className="text-xs text-slate-500">
                  {transcript.segments.length} segments · {speakers.size} speaker{speakers.size === 1 ? "" : "s"}
                </p>
              </div>
            </div>
            {speakers.size > 1 && (
              <button
                onClick={onSwapSpeakers}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                <Icons.Refresh className="h-3.5 w-3.5" />
                Swap clinician / patient
              </button>
            )}
          </div>

          <ol className="max-h-[520px] min-h-0 flex-1 divide-y divide-slate-100 overflow-y-auto">
            {transcript.segments.map((s) => {
              const isClinician = s.speaker === clinicianSpeaker;
              return (
                <li key={s.id} className="flex gap-3 px-5 py-4">
                  <Avatar text={isClinician ? "CL" : "PT"} tone={isClinician ? "brand" : "amber"} />
                  <div className="min-w-0 flex-1">
                    <p className="mb-1 flex items-baseline gap-2 text-sm">
                      <span className="font-semibold text-slate-900">
                        {isClinician ? "Clinician" : patient.name.trim() || "Patient"}
                      </span>
                      <span className="text-xs tabular-nums text-slate-400">{formatTime(s.start)}</span>
                    </p>
                    <p className="text-sm leading-relaxed text-slate-700">{s.text}</p>
                  </div>
                </li>
              );
            })}
          </ol>

          <div className="flex items-center gap-2 border-t border-emerald-100 bg-emerald-50/70 px-5 py-3 text-sm font-semibold text-emerald-800">
            <Icons.CheckCircle />
            Session complete · {formatTime(duration)} recorded
          </div>
          <div className="flex items-center justify-between px-5 py-2.5 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-600" />
              {sourceLabel} · {transcript.provider}
            </span>
            <span className="font-mono">Session {encounter.id.slice(0, 10)}</span>
          </div>
        </Card>

        <Card className="h-fit p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Patient & visit</h3>
          <PatientForm value={patient} onChange={onPatientChange} compact />
          <label className="mt-3 block text-xs font-semibold text-slate-600">
            Note template
            <select
              value={templateId}
              onChange={(e) => onTemplateChange(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800 outline-none focus:border-brand-600"
            >
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
        </Card>
      </div>

      <button
        onClick={onGenerate}
        disabled={generating || !notesReady}
        title={notesReady ? undefined : "The note model is not configured in backend/.env"}
        className="mt-5 flex w-full items-center justify-center gap-2.5 rounded-2xl bg-gradient-to-r from-brand-700 to-brand-800 py-4 text-base font-semibold text-white shadow-md transition hover:from-brand-800 hover:to-brand-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {generating ? (
          <Spinner className="h-5 w-5 border-white/30 border-t-white" />
        ) : (
          <Icons.Sparkles className="h-5 w-5 text-amber-300" />
        )}
        {generating ? "Starting…" : "Generate Note"}
      </button>
    </>
  );
}
