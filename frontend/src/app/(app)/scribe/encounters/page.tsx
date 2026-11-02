"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { CodesPanel } from "@/components/scribe/CodesPanel";
import { DocumentsPanel } from "@/components/scribe/DocumentsPanel";
import { Icons } from "@/components/icons";
import { NotePanel } from "@/components/scribe/NotePanel";
import { PatientForm } from "@/components/scribe/PatientForm";
import { TasksPanel } from "@/components/scribe/TasksPanel";
import { TranscriptPanel } from "@/components/scribe/TranscriptPanel";
import { Avatar, Card, EmptyState, SourceTag, Spinner, StatusPill } from "@/components/ui";
import {
  api,
  type DocumentType,
  type EncounterDetail,
  type EncounterSummary,
  type Finding,
  type Note,
  type NoteTemplate,
  type Patient,
} from "@/lib/api";
import { formatDateTime, initials, isToday } from "@/lib/format";

export default function EncountersPage() {
  return (
    <>
      <Suspense>
        <Encounters />
      </Suspense>
    </>
  );
}

type ListTab = "all" | "drafts" | "signed";

function Encounters() {
  const router = useRouter();
  const params = useSearchParams();
  const selectedId = params.get("id");
  const [rows, setRows] = useState<EncounterSummary[] | null>(null);
  const [listTab, setListTab] = useState<ListTab>("all");
  const [range, setRange] = useState<"today" | "all">("all");
  const urlQuery = params.get("q") ?? "";
  const [q, setQ] = useState(urlQuery);
  const [seenUrlQuery, setSeenUrlQuery] = useState(urlQuery);
  if (urlQuery !== seenUrlQuery) {
    setSeenUrlQuery(urlQuery);
    setQ(urlQuery);
  }

  const loadList = useCallback(() => {
    api
      .encounters()
      .then(setRows)
      .catch(() => setRows([]));
  }, []);
  useEffect(loadList, [loadList]);

  const inRange = (rows ?? []).filter((r) => range === "all" || isToday(r.created_at));
  const counts = {
    all: inRange.length,
    drafts: inRange.filter((r) => r.status !== "signed").length,
    signed: inRange.filter((r) => r.status === "signed").length,
  };
  const visible = useMemo(() => {
    const term = q.trim().toLowerCase();
    return inRange.filter(
      (r) =>
        (listTab === "all" || (listTab === "signed" ? r.status === "signed" : r.status !== "signed")) &&
        (!term || r.patient.name.toLowerCase().includes(term) || r.patient.mrn.toLowerCase().includes(term)),
    );
  }, [inRange, listTab, q]);

  function select(id: string) {
    router.replace(`/scribe/encounters?id=${id}`);
  }

  return (
    <main className="grid h-full min-h-0 gap-5 p-4 sm:p-6 lg:grid-cols-[320px_1fr]">
      {/* List */}
      <Card className="flex min-h-[420px] flex-col overflow-hidden lg:min-h-0">
        <div className="border-b border-slate-100 px-4 pb-0 pt-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">Encounters</p>
            <select
              value={range}
              onChange={(e) => setRange(e.target.value as "today" | "all")}
              className="rounded-lg border border-brand-200 bg-brand-50 px-2 py-1 text-xs font-semibold text-brand-800"
            >
              <option value="all">All dates</option>
              <option value="today">Today</option>
            </select>
          </div>
          <div className="relative mb-3">
            <Icons.Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search by name or MRN…"
              className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-600"
            />
          </div>
          <div className="flex">
            {(["all", "drafts", "signed"] as ListTab[]).map((t) => (
              <button
                key={t}
                onClick={() => setListTab(t)}
                className={`flex-1 border-b-2 pb-2.5 text-sm font-medium capitalize ${listTab === t ? "border-brand-700 text-brand-800" : "border-transparent text-slate-500 hover:text-slate-800"}`}
              >
                {t} <span className="text-xs text-slate-400">{counts[t]}</span>
              </button>
            ))}
          </div>
        </div>
        <ul className="min-h-0 flex-1 overflow-y-auto">
          {rows === null && (
            <li className="flex justify-center py-10">
              <Spinner />
            </li>
          )}
          {visible.map((r) => (
            <li key={r.id}>
              <button
                onClick={() => select(r.id)}
                className={`flex w-full items-center gap-3 border-l-[3px] px-4 py-3 text-left transition-colors ${
                  r.id === selectedId ? "border-amber-400 bg-brand-50/70" : "border-transparent hover:bg-slate-50"
                }`}
              >
                <Avatar text={initials(r.patient.name)} size="sm" tone={r.id === selectedId ? "amber" : "brand"} />
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold text-slate-900">{r.patient.name || "Unnamed patient"}</span>
                    <StatusPill status={r.status} />
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {[r.patient.mrn && `MRN ${r.patient.mrn}`, r.patient.sex, formatDateTime(r.created_at)]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
              </button>
            </li>
          ))}
          {rows !== null && visible.length === 0 && (
            <li className="px-4 py-10 text-center text-sm text-slate-500">No encounters here.</li>
          )}
        </ul>
      </Card>

      {/* Detail */}
      {selectedId ? (
        <Detail key={selectedId} id={selectedId} initialTab={params.get("tab")} onChanged={loadList} />
      ) : (
        <Card className="flex">
          <EmptyState icon={<Icons.File />} title="Select an encounter">
            Choose a patient on the left to review the transcript, edit and sign the note, and write letters.
          </EmptyState>
        </Card>
      )}
    </main>
  );
}

type Tab = "note" | "transcript" | "codes" | "tasks" | "documents";

function Detail({ id, initialTab, onChanged }: { id: string; initialTab: string | null; onChanged: () => void }) {
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
      const d = await api.encounter(id);
      setDetail(d);
      setNote(d.final_note ?? d.draft_note);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open the encounter");
    }
  }, [id]);

  useEffect(() => {
    load();
    Promise.all([api.templates(), api.documentTypes()])
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
      const d = await api.encounter(id).catch(() => null);
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
    await api.setPatient(id, patient);
    setEditingPatient(false);
    await load();
    onChanged();
  }

  async function startDraft(templateId: string) {
    try {
      await api.startDraft(id, templateId, detail!.clinician_speaker);
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
      setFindings((await api.reviewNote(id, note)).findings);
    } catch {
      setFindings(null);
    } finally {
      setReviewing(false);
    }
  }

  async function approve(): Promise<boolean> {
    if (!note) return false;
    try {
      await api.approveNote(id, note);
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
        <div className="flex gap-1 overflow-x-auto border-b border-slate-100 px-4">
          <TabBtn active={tab === "note"} onClick={() => setTab("note")} icon={<Icons.File className="h-4 w-4" />}>
            Note
          </TabBtn>
          <TabBtn
            active={tab === "transcript"}
            onClick={() => setTab("transcript")}
            icon={<Icons.Headphones className="h-4 w-4" />}
          >
            Transcript
          </TabBtn>
          <TabBtn active={tab === "codes"} onClick={() => setTab("codes")} icon={<Icons.Tag className="h-4 w-4" />}>
            Clinical Codes
          </TabBtn>
          <TabBtn active={tab === "tasks"} onClick={() => setTab("tasks")} icon={<Icons.ListCheck className="h-4 w-4" />}>
            Task List
            {openTasks > 0 && (
              <span className="rounded-full bg-amber-400 px-1.5 text-[10px] font-bold text-brand-950">{openTasks}</span>
            )}
          </TabBtn>
          <TabBtn
            active={tab === "documents"}
            onClick={() => setTab("documents")}
            disabled={!signed}
            title={signed ? undefined : "Sign the note first"}
            icon={<Icons.Book className="h-4 w-4" />}
          >
            Letters & summaries
          </TabBtn>
        </div>

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

function NoteTab({
  detail,
  note,
  templates,
  onStartDraft,
  onChange,
  onApprove,
  highlighted,
  onSelect,
  findings,
  reviewing,
  onReview,
  onDismissFindings,
}: {
  detail: EncounterDetail;
  note: Note | null;
  templates: NoteTemplate[];
  onStartDraft: (templateId: string) => void;
  onChange: (n: Note) => void;
  onApprove: () => Promise<boolean>;
  highlighted: Set<number>;
  onSelect: (ids: number[]) => void;
  findings: Finding[] | null;
  reviewing: boolean;
  onReview: () => void;
  onDismissFindings: () => void;
}) {
  const [templateId, setTemplateId] = useState(detail.template_id ?? "cardiology-clinic");

  if (detail.status === "drafting") {
    return (
      <EmptyState icon={<Spinner className="h-5 w-5" />} title="Drafting the note…">
        This usually takes under a minute. You can leave this page; the Board shows when it&apos;s ready.
      </EmptyState>
    );
  }

  if (!note || detail.status === "pending" || detail.status === "failed") {
    return (
      <EmptyState
        icon={detail.status === "failed" ? <Icons.Alert /> : <Icons.Sparkles />}
        title={detail.status === "failed" ? "The draft failed" : "No note yet"}
      >
        {detail.status === "failed" && detail.error && <p className="mb-3 text-rose-700">{detail.error}</p>}
        <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
          <select
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          >
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => onStartDraft(templateId)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
          >
            <Icons.Sparkles className="h-4 w-4 text-amber-300" />
            {detail.status === "failed" ? "Try again" : "Generate note"}
          </button>
        </div>
      </EmptyState>
    );
  }

  // Note beside the transcript so clicking a line shows where it came from
  return (
    <div className="grid min-h-0 flex-1 gap-5 xl:grid-cols-[1.4fr_1fr]">
      <div className="flex min-h-[480px] flex-col">
        <NotePanel
          note={note}
          approved={detail.status === "signed"}
          onChange={onChange}
          onApprove={onApprove}
          onSelect={onSelect}
          findings={findings}
          reviewing={reviewing}
          onReview={onReview}
          onDismissFindings={onDismissFindings}
        />
      </div>
      <div className="hidden min-h-0 flex-col rounded-xl border border-slate-100 bg-slate-50/60 p-4 xl:flex">
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-500">Source transcript</p>
        <TranscriptPanel transcript={detail.transcript} clinicianSpeaker={detail.clinician_speaker} highlighted={highlighted} />
      </div>
    </div>
  );
}

function PatientEditor({ initial, onSave }: { initial: Patient; onSave: (p: Patient) => Promise<void> }) {
  const [value, setValue] = useState(initial);
  const [saving, setSaving] = useState(false);
  return (
    <div className="mt-4 border-t border-slate-100 pt-4">
      <PatientForm value={value} onChange={setValue} />
      <button
        disabled={saving || !value.name.trim()}
        onClick={async () => {
          setSaving(true);
          await onSave(value).finally(() => setSaving(false));
        }}
        className="mt-3 rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save details"}
      </button>
    </div>
  );
}

function TabBtn({
  active,
  disabled,
  title,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  disabled?: boolean;
  title?: string;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`flex shrink-0 items-center gap-2 whitespace-nowrap border-b-2 px-3 py-3.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        active ? "border-brand-700 text-brand-800" : "border-transparent text-slate-500 hover:text-slate-800"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}

function CopyButton({ text, label }: { text: string; label: string }) {
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
