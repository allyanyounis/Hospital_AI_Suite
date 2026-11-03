"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { cursorPagination, flattenPages } from "@/shared/api/pagination";
import { Sparkline } from "@/shared/ui/Sparkline";
import { Card, EmptyState } from "@/shared/ui/ui";
import { VirtualTable } from "@/shared/ui/virtual";
import { clinicalApi, clinicalKeys } from "../api";
import type { VitalKey, VitalRange, VitalSigns } from "../types";
import { flagText, shortDateTime, vitalValue } from "./format";

const TRENDS: VitalKey[] = ["heart_rate", "systolic_bp", "spo2", "temperature_c", "resp_rate"];

/** Trend lines over the loaded sets, then every set of observations (newest first, virtualised, paged). */
export function VitalsPanel({ patientId, ranges }: { patientId: number; ranges: VitalRange[] }) {
  const q = useInfiniteQuery({
    queryKey: clinicalKeys.vitals(patientId),
    queryFn: ({ pageParam }) => clinicalApi.vitals(patientId, pageParam),
    ...cursorPagination<VitalSigns>(),
  });
  const rows = flattenPages(q.data);
  const oldestFirst = [...rows].reverse();
  const range = (key: VitalKey) => ranges.find((r) => r.key === key);

  return (
    <div className="space-y-4">
      {rows.length > 1 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {TRENDS.map((key) => (
            <Card key={key} className="px-3 py-2">
              <p className="truncate text-xs font-semibold text-slate-500">
                {range(key)?.label} <span className="font-normal text-slate-400">{range(key)?.unit}</span>
              </p>
              <Sparkline values={oldestFirst.map((v) => v[key])} low={range(key)?.low} high={range(key)?.high} height={36} />
            </Card>
          ))}
        </div>
      )}
      <Card className="overflow-hidden">
        <VirtualTable
          items={rows}
          height={420}
          estimateSize={40}
          getKey={(v) => v.id}
          loading={q.isPending || q.isFetchingNextPage}
          onEndReached={() => q.hasNextPage && q.fetchNextPage()}
          empty={<EmptyState title="No vitals recorded" />}
          columns={[
            { key: "at", header: "Recorded", width: "minmax(9rem,1.4fr)", render: (v) => shortDateTime(v.recorded_at) },
            ...(["heart_rate", "systolic_bp", "spo2", "temperature_c", "resp_rate"] as VitalKey[]).map((key) => ({
              key,
              header: key === "systolic_bp" ? "BP" : (range(key)?.label ?? key),
              width: "minmax(5rem,1fr)",
              className: "tabular-nums",
              render: (v: VitalSigns) => (
                <span className={flagText(v.flags[key] ?? (key === "systolic_bp" ? v.flags.diastolic_bp : undefined))}>
                  {vitalValue(v, key)}
                </span>
              ),
            })),
          ]}
        />
      </Card>
    </div>
  );
}
