"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Badge, type BadgeTone } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../api";
import { useDemoClock } from "../lib/demoClock";
import type { ActionInput, CaseAction, Urgency } from "../types";
import { URGENCY_INFO } from "../types";

const URGENCY_TONE: Record<Urgency, BadgeTone> = { immediate: "bad", urgent: "warn", expedited: "info", elective: "neutral" };

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  return (
    <Badge tone={URGENCY_TONE[urgency]} title={`Target: ${URGENCY_INFO[urgency].target}`}>
      {URGENCY_INFO[urgency].label}
    </Badge>
  );
}

/** Predicted risk with the model's population average as context; high = at least 1.5× the average. */
export function RiskPill({ pct, high, model }: { pct: number; high: boolean; model?: string }) {
  return (
    <span
      title={model ? `${model} predicted risk` : "Predicted risk"}
      className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-semibold tabular-nums ${
        high ? "bg-rose-50 text-rose-700" : "bg-slate-100 text-slate-600"
      }`}
    >
      {pct}%
    </span>
  );
}

/** Overtime chance as a coloured percentage: green under 25, amber to 50, red above. */
export function OverPct({ pct, className = "" }: { pct: number; className?: string }) {
  const tone = pct > 50 ? "text-rose-700" : pct > 25 ? "text-amber-700" : "text-emerald-700";
  return <span className={`font-semibold tabular-nums ${tone} ${className}`}>{pct}%</span>;
}

/**
 * One action on a case (earlier, later, defer, book …). Applies the admin demo clock, then refetches every theatre
 * query; the live event refreshes other screens.
 */
export function useCaseAction() {
  const qc = useQueryClient();
  const at = useDemoClock();
  return useMutation({
    mutationFn: ({ id, action, input }: { id: number; action: CaseAction; input?: ActionInput }) =>
      theatreApi.act(id, action, input, at),
    onSettled: () => qc.invalidateQueries({ queryKey: theatreKeys.all }),
  });
}
