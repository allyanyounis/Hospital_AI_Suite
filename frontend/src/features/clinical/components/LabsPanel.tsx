"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useMounted } from "@/shared/hooks";
import { cursorPagination, flattenPages } from "@/shared/api/pagination";
import { CHART } from "@/shared/lib/theme";
import { Badge, Card, EmptyState, Spinner } from "@/shared/ui/ui";
import { VirtualTable } from "@/shared/ui/virtual";
import { clinicalApi, clinicalKeys } from "../api";
import type { LabLatest, LabResult } from "../types";
import { FLAG_TONE, flagText, formatNumber, shortDateTime } from "./format";

/** One test at a time: its trend against the reference range, then every result (virtualised, paged). */
export function LabsPanel({
  patientId,
  latest,
  test,
  onTest,
}: {
  patientId: number;
  latest: LabLatest[];
  test: string;
  onTest: (code: string) => void;
}) {
  const selected = latest.find((l) => l.test === test) ?? latest[0];
  if (!selected)
    return (
      <Card>
        <EmptyState title="No lab results yet" />
      </Card>
    );

  return (
    <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
      <nav aria-label="Lab tests" className="flex gap-1 overflow-x-auto lg:flex-col">
        {latest.map((l) => (
          <button
            key={l.test}
            onClick={() => onTest(l.test)}
            className={`flex shrink-0 items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm ${
              l.test === selected.test ? "bg-brand-50 font-semibold text-brand-800" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <span className="truncate">{l.name}</span>
            <span className={`tabular-nums text-xs ${flagText(l.flag)}`}>{formatNumber(l.value, 2)}</span>
          </button>
        ))}
      </nav>
      <div className="min-w-0 space-y-4">
        <TrendCard patientId={patientId} lab={selected} />
        <ResultsTable patientId={patientId} test={selected.test} />
      </div>
    </div>
  );
}

function TrendCard({ patientId, lab }: { patientId: number; lab: LabLatest }) {
  const mounted = useMounted();
  const series = useQuery({
    queryKey: clinicalKeys.series(patientId, lab.test),
    queryFn: () => clinicalApi.series(patientId, lab.test),
  });
  const data = (series.data ?? []).map((p) => ({ t: new Date(p.at).getTime(), value: p.value }));

  return (
    <Card className="p-4">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-slate-900">
          {lab.name} <span className="font-normal text-slate-400">({lab.unit})</span>
        </p>
        <p className="text-xs text-slate-500">
          Reference {lab.ref_low}–{lab.ref_high}
        </p>
      </div>
      <div className="h-48">
        {series.isPending ? (
          <div className="flex h-full items-center justify-center">
            <Spinner className="h-5 w-5" />
          </div>
        ) : (
          mounted && (
            <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 1, height: 192 }}>
              <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
                <CartesianGrid stroke={CHART.grid} vertical={false} />
                <ReferenceArea y1={lab.ref_low} y2={lab.ref_high} fill={CHART.band} fillOpacity={0.6} ifOverflow="extendDomain" />
                <XAxis
                  dataKey="t"
                  type="number"
                  scale="time"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(t: number) => new Date(t).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  tick={{ fontSize: 11, fill: CHART.axis }}
                />
                <YAxis tick={{ fontSize: 11, fill: CHART.axis }} domain={["auto", "auto"]} />
                <Tooltip
                  labelFormatter={(t) => shortDateTime(new Date(Number(t)).toISOString())}
                  formatter={(v) => [`${v} ${lab.unit}`, lab.name]}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={CHART.primary}
                  strokeWidth={2}
                  dot={{ r: 2.5 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )
        )}
      </div>
    </Card>
  );
}

function ResultsTable({ patientId, test }: { patientId: number; test: string }) {
  const q = useInfiniteQuery({
    queryKey: clinicalKeys.labs(patientId, test),
    queryFn: ({ pageParam }) => clinicalApi.labs(patientId, test, pageParam),
    ...cursorPagination<LabResult>(),
  });
  const rows = flattenPages(q.data);

  return (
    <Card className="overflow-hidden">
      <VirtualTable
        items={rows}
        height={320}
        estimateSize={40}
        getKey={(r) => r.id}
        loading={q.isPending || q.isFetchingNextPage}
        onEndReached={() => q.hasNextPage && q.fetchNextPage()}
        empty={<EmptyState title="No results" />}
        columns={[
          { key: "at", header: "Collected", width: "minmax(9rem,1fr)", render: (r) => shortDateTime(r.collected_at) },
          {
            key: "value",
            header: "Value",
            width: "8rem",
            className: "tabular-nums",
            render: (r) => (
              <span className={flagText(r.flag)}>
                {formatNumber(r.value, 2)} <span className="text-xs font-normal text-slate-400">{r.unit}</span>
              </span>
            ),
          },
          {
            key: "flag",
            header: "Flag",
            width: "6rem",
            render: (r) => (r.flag === "normal" ? <span className="text-xs text-slate-300">In range</span> : <Badge tone={FLAG_TONE[r.flag]}>{r.flag}</Badge>),
          },
        ]}
      />
    </Card>
  );
}
