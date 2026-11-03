"use client";

import { ResponsiveContainer } from "recharts";
import { useMounted } from "@/shared/hooks";
import { Card } from "@/shared/ui/ui";
import type { PairedDiff } from "../../insightsTypes";

/** A titled card section of the insights page. */
export function Panel({
  title,
  note,
  className = "",
  children,
}: {
  title: string;
  note?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className={`p-5 ${className}`}>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      {note && <p className="mt-0.5 text-xs text-slate-500">{note}</p>}
      <div className="mt-4">{children}</div>
    </Card>
  );
}

/** Recharts measures its container synchronously, so the chart renders only after mount. */
export function ChartBox({ height = 240, children }: { height?: number; children: React.ReactElement }) {
  const mounted = useMounted();
  return (
    <div className="w-full" style={{ height }}>
      {mounted && (
        <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 1, height }}>
          {children}
        </ResponsiveContainer>
      )}
    </div>
  );
}

/** A paired difference as a big signed number: green when it moves the right way. */
export function Callout({
  diff,
  unit,
  noun,
  lowerBetter = true,
}: {
  diff: PairedDiff | undefined;
  unit: string;
  noun: string;
  lowerBetter?: boolean;
}) {
  if (!diff) return null;
  const less = diff.mean < 0;
  const good = diff.mean === 0 ? null : less === lowerBetter;
  const tone = good === null ? "text-slate-700" : good ? "text-emerald-700" : "text-rose-700";
  return (
    <Card className="p-4">
      <p className={`text-2xl font-bold tabular-nums ${tone}`}>
        {Math.abs(diff.mean).toFixed(1)}
        {unit}
      </p>
      <p className="text-xs text-slate-600">
        {less ? "less" : "more"} {noun}
      </p>
      {diff.low != null && diff.high != null && (
        <p className="mt-1 text-[11px] text-slate-400">
          Paired difference {diff.low} to {diff.high}
        </p>
      )}
    </Card>
  );
}

/** Plain table styling shared by the insight tables. */
export function DataTable({
  head,
  left = [0],
  children,
}: {
  head: React.ReactNode[];
  /** Columns aligned left (the rest are numbers, aligned right) */
  left?: number[];
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            {head.map((h, i) => (
              <th key={i} className={`px-3 py-2 ${left.includes(i) ? "" : "text-right"}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-slate-700">{children}</tbody>
      </table>
    </div>
  );
}

export function Num({ children, strong = false, className = "" }: { children: React.ReactNode; strong?: boolean; className?: string }) {
  return (
    <td className={`px-3 py-2 text-right tabular-nums ${strong ? "font-semibold text-brand-800" : ""} ${className}`}>{children}</td>
  );
}
