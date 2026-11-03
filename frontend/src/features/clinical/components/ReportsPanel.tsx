"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { cursorPagination, flattenPages } from "@/shared/api/pagination";
import { Icons } from "@/shared/ui/icons";
import { Drawer } from "@/shared/ui/overlays";
import { Badge, Card, EmptyState, Spinner } from "@/shared/ui/ui";
import { VirtualList } from "@/shared/ui/virtual";
import { clinicalApi, clinicalKeys } from "../api";
import type { ReportKind, ReportListItem } from "../types";
import { REPORT_LABEL } from "../types";
import { shortDate } from "./format";

/** Imaging, ECG, pathology and review reports: filter by kind, open one to read it in a drawer. */
export function ReportsPanel({
  patientId,
  counts,
}: {
  patientId: number;
  counts: Partial<Record<ReportKind, number>>;
}) {
  const [kind, setKind] = useState<ReportKind | "">("");
  const [open, setOpen] = useState<number | null>(null);
  const q = useInfiniteQuery({
    queryKey: clinicalKeys.reports(patientId, kind),
    queryFn: ({ pageParam }) => clinicalApi.reports(patientId, kind, pageParam),
    ...cursorPagination<ReportListItem>(),
  });
  const rows = flattenPages(q.data);
  const kinds = Object.keys(counts) as ReportKind[];
  const total = kinds.reduce((n, k) => n + (counts[k] ?? 0), 0);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Report kind">
        {[["", `All · ${total}`] as const, ...kinds.map((k) => [k, `${REPORT_LABEL[k]} · ${counts[k]}`] as const)].map(
          ([value, label]) => (
            <button
              key={value || "all"}
              onClick={() => setKind(value)}
              className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                kind === value
                  ? "border-brand-300 bg-brand-50 text-brand-800"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {label}
            </button>
          ),
        )}
      </div>
      <Card className="overflow-hidden">
        <VirtualList
          items={rows}
          height={440}
          estimateSize={76}
          getKey={(r) => r.id}
          loading={q.isPending || q.isFetchingNextPage}
          onEndReached={() => q.hasNextPage && q.fetchNextPage()}
          empty={<EmptyState icon={<Icons.File className="h-6 w-6" />} title="No reports" />}
          renderRow={(r) => (
            <button
              onClick={() => setOpen(r.id)}
              className="flex h-full w-full flex-col justify-center gap-0.5 border-b border-slate-100 px-4 text-left hover:bg-brand-50/40"
            >
              <span className="flex items-center gap-2">
                <Badge tone="brand">{REPORT_LABEL[r.kind] ?? r.kind}</Badge>
                <span className="truncate text-sm font-semibold text-slate-900">{r.title}</span>
                <span className="ml-auto shrink-0 text-xs text-slate-400">{shortDate(r.reported_on)}</span>
              </span>
              <span className="truncate text-xs text-slate-500">{r.excerpt}</span>
            </button>
          )}
        />
      </Card>
      {open != null && <ReportDrawer reportId={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function ReportDrawer({ reportId, onClose }: { reportId: number; onClose: () => void }) {
  const q = useQuery({ queryKey: clinicalKeys.report(reportId), queryFn: () => clinicalApi.report(reportId) });
  const r = q.data;
  return (
    <Drawer
      title={r?.title ?? "Report"}
      subtitle={r ? `${REPORT_LABEL[r.kind] ?? r.kind} · ${shortDate(r.reported_on)}${r.author ? ` · ${r.author}` : ""}` : undefined}
      onClose={onClose}
    >
      {q.isPending ? (
        <div className="flex justify-center py-10">
          <Spinner className="h-5 w-5" />
        </div>
      ) : q.isError ? (
        <p className="text-sm text-rose-700">{q.error.message}</p>
      ) : (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{r?.body}</p>
      )}
    </Drawer>
  );
}
