"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useSession } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";
import { Card, Spinner } from "@/shared/ui/ui";
import { scribeApi } from "../api";
import { CompletedTranscript } from "../components/CompletedTranscript";
import { PatientForm } from "../components/PatientForm";
import { Recorder, type RecorderState } from "../components/Recorder";
import { Stepper } from "../components/Stepper";
import { EMPTY_PATIENT, type Encounter, type NoteTemplate, type Patient, type Sample } from "../types";

export function SessionView() {
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
    Promise.all([scribeApi.templates(), scribeApi.samples()])
      .then(([t, s]) => {
        setTemplates(t);
        setSamples(s);
      })
      .catch(() => setError("Could not load templates"));
  }, []);

  // Arriving from the dashboard with an uploaded or sample encounter: jump straight to step 3
  useEffect(() => {
    if (!preloadedId) return;
    scribeApi
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
      setEncounter(await scribeApi.startFromSample(id));
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
      await scribeApi.setPatient(encounter.id, patient);
      await scribeApi.startDraft(encounter.id, templateId, clinicianSpeaker);
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
