"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useSession } from "@/components/shell/SessionProvider";
import { Icons } from "@/components/icons";
import { PatientForm } from "@/components/scribe/PatientForm";
import { Recorder, type RecorderState } from "@/components/scribe/Recorder";
import { Avatar, Card, Spinner, Stepper } from "@/components/ui";
import { api, EMPTY_PATIENT, type Encounter, type NoteTemplate, type Patient, type Sample } from "@/lib/api";
import { formatDuration as formatTime } from "@/lib/format";

export default function SessionPage() {
  return (
    <>
      <Suspense>
        <LiveSession />
      </Suspense>
    </>
  );
}

function LiveSession() {
  const { config } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const preloadedId = params.get("encounter");

  const [templates, setTemplates] = useState<NoteTemplate[]>([]);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [templateId, setTemplateId] = useState("cardiology-clinic");
  const [patient, setPatient] = useState<Patient>(EMPTY_PATIENT);
  const [recState, setRecState] = useState<RecorderState>("idle");
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [source, setSource] = useState<string>("live");
  const [clinicianSpeaker, setClinicianSpeaker] = useState(0);
  const [busy, setBusy] = useState<null | "transcribing" | "generating" | "loading">(preloadedId ? "loading" : null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.templates(), api.samples()])
      .then(([t, s]) => {
        setTemplates(t);
        setSamples(s);
      })
      .catch(() => setError("Could not load templates"));
  }, []);

  // Arriving from the dashboard with an uploaded or sample encounter: jump straight to step 3
  useEffect(() => {
    if (!preloadedId) return;
    api
      .encounter(preloadedId)
      .then((d) => {
        setEncounter({ id: d.id, transcript: d.transcript });
        setSource(d.source);
        setPatient(d.patient);
        setClinicianSpeaker(d.clinician_speaker);
        if (d.template_id) setTemplateId(d.template_id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not open the encounter"))
      .finally(() => setBusy(null));
  }, [preloadedId]);

  async function handleRecorded(pending: Promise<Encounter>) {
    setBusy("transcribing");
    setError(null);
    try {
      const e = await pending;
      setEncounter(e);
      setSource(e.transcript.provider.includes("live") ? "live" : "recording");
      setClinicianSpeaker(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transcription failed");
    } finally {
      setBusy(null);
    }
  }

  async function loadSample(id: string) {
    setBusy("transcribing");
    setError(null);
    try {
      setEncounter(await api.startFromSample(id));
      setSource("sample");
      setClinicianSpeaker(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the sample");
    } finally {
      setBusy(null);
    }
  }

  async function generateNote() {
    if (!encounter) return;
    if (!patient.name.trim()) {
      setError("Enter the patient's name before generating the note.");
      return;
    }
    setBusy("generating");
    setError(null);
    try {
      await api.setPatient(encounter.id, patient);
      await api.startDraft(encounter.id, templateId, clinicianSpeaker);
      router.push(`/scribe/board?highlight=${encounter.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the note");
      setBusy(null);
    }
  }

  function startOver() {
    if (encounter && !confirm("Leave this transcript? It stays saved under Encounters.")) return;
    setEncounter(null);
    setPatient(EMPTY_PATIENT);
    setError(null);
    router.replace("/scribe/session");
  }

  const step = encounter ? 3 : recState !== "idle" ? 2 : 1;

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
      <Stepper step={step} />
      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <Icons.Alert />
          {error}
        </div>
      )}

      {busy === "loading" ? (
        <Card className="flex h-96 items-center justify-center gap-3 text-sm text-slate-500">
          <Spinner /> Opening encounter…
        </Card>
      ) : encounter ? (
        <CompletedTranscript
          encounter={encounter}
          source={source}
          clinicianSpeaker={clinicianSpeaker}
          onSwapSpeakers={() => {
            const other = encounter.transcript.segments.find((s) => s.speaker !== clinicianSpeaker)?.speaker;
            if (other !== undefined) setClinicianSpeaker(other);
          }}
          patient={patient}
          onPatientChange={setPatient}
          templates={templates}
          templateId={templateId}
          onTemplateChange={setTemplateId}
          generating={busy === "generating"}
          notesReady={config.notes_ready}
          onGenerate={generateNote}
          onBack={startOver}
        />
      ) : (
        <>
          {busy === "transcribing" && (
            <Card className="flex h-96 flex-col items-center justify-center gap-3 text-sm text-slate-500">
              <Spinner className="h-6 w-6" />
              Finalising the transcript…
            </Card>
          )}
          {/* The Recorder keeps the same tree position across steps so the microphone stream survives */}
          <div className={busy === "transcribing" ? "hidden" : ""}>
            {recState === "idle" && (
              <Card className="mb-5 p-6">
                <h2 className="mb-1 text-lg font-semibold text-slate-900">Patient & visit</h2>
                <p className="mb-5 text-sm text-slate-500">
                  Fill in now or after the recording. The name is required before the note is generated.
                </p>
                <PatientForm value={patient} onChange={setPatient} />
                <label className="mt-4 block max-w-sm text-xs font-semibold text-slate-600">
                  Note template
                  <select
                    value={templateId}
                    onChange={(e) => setTemplateId(e.target.value)}
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
            )}
            <Card className={recState !== "idle" ? "flex h-[640px] flex-col p-6" : "p-6"}>
              {recState === "idle" && (
                <div className="mb-4">
                  <h2 className="text-lg font-semibold text-slate-900">Capture the consultation</h2>
                  <p className="text-sm text-slate-500">
                    Record live with real-time transcription, or try a sample consultation.
                  </p>
                </div>
              )}
              <div className={recState !== "idle" ? "flex min-h-0 flex-1 flex-col" : "flex flex-wrap items-center gap-3"}>
                <Recorder
                  disabled={busy !== null || !config.transcriber_ready}
                  onComplete={handleRecorded}
                  onStateChange={setRecState}
                />
                {recState === "idle" && (
                  <>
                    <span className="text-xs text-slate-400">or</span>
                    <select
                      value=""
                      onChange={(e) => e.target.value && loadSample(e.target.value)}
                      disabled={busy !== null}
                      className="min-w-0 max-w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700"
                    >
                      <option value="">Load a sample consultation…</option>
                      {samples.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.title}
                        </option>
                      ))}
                    </select>
                  </>
                )}
              </div>
            </Card>
          </div>
        </>
      )}
    </main>
  );
}

function CompletedTranscript({
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
