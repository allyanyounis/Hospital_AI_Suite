"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { formatDateTime, initials, isToday } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Avatar, Card, EmptyState, Spinner } from "@/shared/ui/ui";
import { scribeApi } from "../api";
import { EncounterDetailPanel } from "../components/EncounterDetailPanel";
import { StatusPill } from "../components/status";
import type { EncounterSummary } from "../types";

export function EncountersView() {
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
    scribeApi
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
        <EncounterDetailPanel key={selectedId} id={selectedId} initialTab={params.get("tab")} onChanged={loadList} />
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
