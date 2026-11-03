"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useNow } from "@/shared/hooks";
import { formatDateTime, initials, isToday } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Avatar, Card, EmptyState, PageHeader, Spinner } from "@/shared/ui/ui";
import { scribeApi } from "../api";
import { Chip, CountPill } from "../components/BoardChips";
import { PipelineBar, SourceTag } from "../components/status";
import type { EncounterSummary, NoteTemplate, PipelineStatus } from "../types";

export function BoardView() {
  return (
    <>
      <Suspense>
        <Board />
      </Suspense>
    </>
  );
}

const STATUS_FILTERS: { key: "all" | PipelineStatus; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pending", label: "Awaiting note" },
  { key: "drafting", label: "In progress" },
  { key: "ready", label: "To review" },
  { key: "signed", label: "Signed" },
  { key: "failed", label: "Failed" },
];
const SOURCE_FILTERS = [
  { key: "all", label: "All sources", icon: null },
  { key: "live", label: "Live", icon: Icons.Radio },
  { key: "recording", label: "Upload", icon: Icons.Upload },
  { key: "sample", label: "Sample", icon: Icons.Book },
];

function Board() {
  const highlight = useSearchParams().get("highlight");
  const [rows, setRows] = useState<EncounterSummary[] | null>(null);
  const [templates, setTemplates] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"all" | PipelineStatus>("all");
  const [source, setSource] = useState("all");
  const [date, setDate] = useState<"any" | "today" | "week">("any");
  const [q, setQ] = useState("");

  const load = useCallback(() => {
    scribeApi
      .encounters()
      .then((r) => {
        setRows(r);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load the board"));
  }, []);

  useEffect(() => {
    load();
    scribeApi
      .templates()
      .then((t: NoteTemplate[]) => setTemplates(Object.fromEntries(t.map((x) => [x.id, x.name]))))
      .catch(() => {});
  }, [load]);

  // Keep polling while any note is being drafted
  const drafting = rows?.some((r) => r.status === "drafting") ?? false;
  useEffect(() => {
    if (!drafting) return;
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
  }, [drafting, load]);

  const now = useNow();
  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    const weekAgo = now.getTime() - 7 * 86400_000;
    return (rows ?? []).filter(
      (r) =>
        (status === "all" || r.status === status) &&
        (source === "all" || r.source === source) &&
        (date === "any" || (date === "today" ? isToday(r.created_at) : new Date(r.created_at).getTime() >= weekAgo)) &&
        (!term || r.patient.name.toLowerCase().includes(term) || r.patient.mrn.toLowerCase().includes(term)),
    );
  }, [rows, status, source, date, q, now]);

  const count = (s: PipelineStatus) => rows?.filter((r) => r.status === s).length ?? 0;

  async function retry(r: EncounterSummary) {
    try {
      await scribeApi.startDraft(r.id, r.template_id ?? "soap", r.clinician_speaker);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not restart the draft");
    }
  }

  return (
    <main className="px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Pulse className="h-6 w-6" />}
        title="Board"
        subtitle="Live and uploaded sessions running through the AI pipeline. Open a note to review, edit and sign once it's ready."
        aside={
          <div className="flex flex-wrap gap-2 text-sm">
            <CountPill
              icon={<Icons.Clock />}
              tone="border-slate-200 bg-white text-slate-600"
              n={count("pending")}
              label="awaiting"
            />
            <CountPill
              icon={<Icons.Refresh />}
              tone="border-amber-200 bg-amber-50 text-amber-700"
              n={count("drafting")}
              label="in progress"
            />
            <CountPill
              icon={<Icons.CheckCircle />}
              tone="border-emerald-200 bg-emerald-50 text-emerald-700"
              n={count("ready")}
              label="ready"
            />
          </div>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Icons.Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by patient or MRN…"
            className="w-64 rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-600"
          />
        </div>
        <select
          value={date}
          onChange={(e) => setDate(e.target.value as typeof date)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
        >
          <option value="any">Any date</option>
          <option value="today">Today</option>
          <option value="week">Last 7 days</option>
        </select>
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-1.5">
        {STATUS_FILTERS.map((f) => (
          <Chip key={f.key} active={status === f.key} onClick={() => setStatus(f.key)}>
            {f.label}
          </Chip>
        ))}
        <span className="mx-2 h-6 w-px bg-slate-200" />
        {SOURCE_FILTERS.map(({ key, label, icon: Icon }) => (
          <Chip key={key} active={source === key} onClick={() => setSource(key)} subtle>
            {Icon && <Icon className="h-3.5 w-3.5" />}
            {label}
          </Chip>
        ))}
      </div>

      {error && <p className="mb-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">{error}</p>}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3">Patient</th>
                <th className="px-4 py-3">MRN</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Template</th>
                <th className="px-4 py-3">Date & time</th>
                <th className="px-4 py-3">Pipeline</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows === null && (
                <tr>
                  <td colSpan={7} className="py-16 text-center text-slate-500">
                    <Spinner /> <span className="ml-2">Loading…</span>
                  </td>
                </tr>
              )}
              {filtered.map((r) => (
                <tr key={r.id} className={`transition-colors hover:bg-brand-50/40 ${r.id === highlight ? "bg-amber-50/60" : ""}`}>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <Avatar text={initials(r.patient.name)} size="sm" />
                      <div>
                        <p className="font-semibold text-slate-900">
                          {r.patient.name || <span className="italic text-slate-400">Unnamed patient</span>}
                        </p>
                        <SourceTag source={r.source} />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-xs text-slate-600">{r.patient.mrn || "—"}</td>
                  <td className="px-4 py-3.5">
                    {r.patient.visit_type ? (
                      <span className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700">
                        {r.patient.visit_type}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-slate-700">
                    {r.template_id ? (
                      (templates[r.template_id] ?? r.template_id)
                    ) : (
                      <span className="text-slate-400">Not chosen</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3.5 text-slate-600">{formatDateTime(r.created_at)}</td>
                  <td className="px-4 py-3.5">
                    <PipelineBar status={r.status} error={r.error} />
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center justify-end gap-2">
                      {r.status === "failed" && !r.purged && (
                        <button
                          onClick={() => retry(r)}
                          className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                        >
                          Retry
                        </button>
                      )}
                      {r.purged ? (
                        <span className="text-xs text-slate-400">Erased (retention)</span>
                      ) : (
                        <>
                          <Link
                            href={`/scribe/encounters?id=${r.id}&tab=transcript`}
                            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                          >
                            <Icons.File className="h-3.5 w-3.5" />
                            Transcript
                          </Link>
                          <Link
                            href={`/scribe/encounters?id=${r.id}`}
                            title="Open note"
                            className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-white hover:bg-brand-800"
                          >
                            <Icons.Eye />
                          </Link>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows !== null && filtered.length === 0 && (
          <EmptyState icon={<Icons.Pulse />} title={rows.length ? "No sessions match these filters" : "No sessions yet"}>
            {rows.length ? (
              "Try clearing a filter."
            ) : (
              <Link href="/scribe/session" className="font-semibold text-brand-700 hover:underline">
                Start a live session →
              </Link>
            )}
          </EmptyState>
        )}
      </Card>
    </main>
  );
}
