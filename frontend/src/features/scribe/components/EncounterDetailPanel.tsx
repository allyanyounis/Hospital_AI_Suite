import { useCallback, useEffect, useState } from "react";
import { formatDateTime, initials } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Avatar, Card, EmptyState, Spinner, Tabs } from "@/shared/ui/ui";
import { scribeApi } from "../api";
import type { DocumentType, EncounterDetail, Finding, Note, NoteTemplate, Patient } from "../types";
import { CodesPanel } from "./CodesPanel";
import { DocumentsPanel } from "./DocumentsPanel";
import { NoteTab } from "./EncounterNoteTab";
import { PatientEditor } from "./PatientEditor";
import { TasksPanel } from "./TasksPanel";
import { TranscriptPanel } from "./TranscriptPanel";
import { SourceTag, StatusPill } from "./status";

export type Tab = "note" | "transcript" | "codes" | "tasks" | "documents";

export function EncounterDetailPanel({
  id,
  initialTab,
  onChanged,
}: {
  id: string;
  initialTab: string | null;
  onChanged: () => void;
}) {
  const [detail, setDetail] = useState<EncounterDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>(initialTab === "transcript" ? "transcript" : "note");
  const [note, setNote] = useState<Note | null>(null);
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [highlighted, setHighlighted] = useState<Set<number>>(new Set());
  const [editingPatient, setEditingPatient] = useState(false);
  const [templates, setTemplates] = useState<NoteTemplate[]>([]);
  const [docTypes, setDocTypes] = useState<DocumentType[]>([]);

  const load = useCallback(async () => {
    try {
      const d = await scribeApi.encounter(id);
      setDetail(d);
      setNote(d.final_note ?? d.draft_note);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open the encounter");
    }
  }, [id]);

  useEffect(() => {
    load();
    Promise.all([scribeApi.templates(), scribeApi.documentTypes()])
      .then(([t, d]) => {
        setTemplates(t);
        setDocTypes(d);
      })
      .catch(() => {});
  }, [load]);

  // While the note is drafting, poll until it lands
  useEffect(() => {
    if (detail?.status !== "drafting") return;
    const t = setInterval(async () => {
      const d = await scribeApi.encounter(id).catch(() => null);
      if (d && d.status !== "drafting") {
        setDetail(d);
        setNote(d.final_note ?? d.draft_note);
        onChanged();
      }
    }, 2500);
    return () => clearInterval(t);
  }, [detail?.status, id, onChanged]);

  if (error) {
    return (
      <Card className="flex">
        <EmptyState icon={<Icons.Alert />} title="Can't open this encounter">
          {error}
        </EmptyState>
      </Card>
    );
  }
  if (!detail) {
    return (
      <Card className="flex items-center justify-center">
        <Spinner />
      </Card>
    );
  }

  const signed = detail.status === "signed";
  const p = detail.patient;
  const segments = detail.transcript.segments;
  const speakerCount = new Set(segments.map((s) => s.speaker)).size;
  const openTasks = detail.tasks?.tasks.filter((t) => !t.done).length ?? 0;
  const words = segments.reduce((n, s) => n + s.text.split(/\s+/).filter(Boolean).length, 0);

  async function savePatient(patient: Patient) {
    await scribeApi.setPatient(id, patient);
    setEditingPatient(false);
    await load();
    onChanged();
  }

  async function startDraft(templateId: string) {
    try {
      await scribeApi.startDraft(id, templateId, detail!.clinician_speaker);
      await load();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the draft");
    }
  }

  async function review() {
    if (!note) return;
    setReviewing(true);
    try {
      setFindings((await scribeApi.reviewNote(id, note)).findings);
    } catch {
      setFindings(null);
    } finally {
      setReviewing(false);
    }
  }

  async function approve(): Promise<boolean> {
    if (!note) return false;
    try {
      await scribeApi.approveNote(id, note);
      await load();
      onChanged();
      return true;
    } catch {
      return false;
    }
  }

  return (
    <div className="flex min-h-0 flex-col gap-4">
      {/* Patient header */}
      <Card className="px-5 py-4">
        <div className="flex flex-wrap items-center gap-4">
          <Avatar text={initials(p.name)} tone="amber" />
          <div className="min-w-0 flex-1">
            <p className="flex flex-wrap items-center gap-2">
              <span className="text-xl font-semibold text-slate-900">{p.name || "Unnamed patient"}</span>
              <StatusPill status={detail.status} />
              <SourceTag source={detail.source} />
            </p>
            <p className="text-sm text-slate-500">
              {[p.mrn && `MRN: ${p.mrn}`, p.sex, p.dob && `DOB ${p.dob}`, p.visit_type, formatDateTime(detail.created_at)]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </div>
          <button
            onClick={() => setEditingPatient((v) => !v)}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Icons.Pencil className="h-3.5 w-3.5" />
            {editingPatient ? "Cancel" : "Edit details"}
          </button>
        </div>
        {editingPatient && <PatientEditor initial={p} onSave={savePatient} />}
      </Card>

      {/* Tabs */}
      <Card className="flex min-h-[560px] flex-1 flex-col overflow-hidden">
        <Tabs<Tab>
          value={tab}
          onChange={setTab}
          tabs={[
            { id: "note", label: "Note", icon: <Icons.File className="h-4 w-4" /> },
            { id: "transcript", label: "Transcript", icon: <Icons.Headphones className="h-4 w-4" /> },
            { id: "codes", label: "Clinical Codes", icon: <Icons.Tag className="h-4 w-4" /> },
            { id: "tasks", label: "Task List", icon: <Icons.ListCheck className="h-4 w-4" />, count: openTasks },
            {
              id: "documents",
              label: "Letters & summaries",
              icon: <Icons.Book className="h-4 w-4" />,
              disabled: !signed,
              title: signed ? undefined : "Sign the note first",
            },
          ]}
        />

        <div className="flex min-h-0 flex-1 flex-col p-5">
          {tab === "transcript" && (
            <>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <h3 className="flex items-baseline gap-3 text-lg font-semibold text-slate-900">
                  Full transcript
                  <span className="text-sm font-normal text-slate-500">
                    {segments.length} segments · {speakerCount} speaker{speakerCount === 1 ? "" : "s"} · {words} words
                  </span>
                </h3>
                <CopyButton text={segments.map((s) => s.text).join("\n")} label="Copy all" />
              </div>
              <TranscriptPanel
                transcript={detail.transcript}
                clinicianSpeaker={detail.clinician_speaker}
                highlighted={highlighted}
              />
            </>
          )}

          {tab === "codes" && (
            <CodesPanel
              encounterId={id}
              initial={detail.codes}
              hasNote={Boolean(note) && detail.status !== "drafting"}
              signed={signed}
              onChange={(codes) => setDetail((d) => (d ? { ...d, codes } : d))}
            />
          )}

          {tab === "tasks" && (
            <TasksPanel
              encounterId={id}
              initial={detail.tasks}
              hasNote={Boolean(note) && detail.status !== "drafting"}
              signed={signed}
              onChange={(tasks) => setDetail((d) => (d ? { ...d, tasks } : d))}
            />
          )}

          {tab === "documents" && signed && <DocumentsPanel encounterId={id} types={docTypes} onError={setError} />}

          {tab === "note" && (
            <NoteTab
              detail={detail}
              note={note}
              templates={templates}
              onStartDraft={startDraft}
              onChange={(n) => {
                setNote(n);
                setFindings(null); // findings no longer match the edited note
              }}
              onApprove={approve}
              highlighted={highlighted}
              onSelect={(ids) => setHighlighted(new Set(ids))}
              findings={findings}
              reviewing={reviewing}
              onReview={review}
              onDismissFindings={() => setFindings(null)}
            />
          )}
        </div>
      </Card>
    </div>
  );
}

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
    >
      <Icons.Copy className="h-3.5 w-3.5" />
      {copied ? "Copied ✓" : label}
    </button>
  );
}
