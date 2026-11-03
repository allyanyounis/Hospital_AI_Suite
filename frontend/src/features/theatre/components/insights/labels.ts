import { CHART } from "@/shared/lib/theme";
import type { MetricKey, MlBasis, PairedDiff, Policy } from "../../insightsTypes";

export const POLICY_NAMES: Record<Policy, string> = {
  baseline: "Packed list",
  heuristic: "Move one elective",
  cpsat: "Solver + manual rule",
  recovery: "Replan",
};

export const POLICY_COLORS: Record<Policy, string> = {
  baseline: CHART.track,
  heuristic: CHART.phases.anaes,
  cpsat: CHART.accent,
  recovery: CHART.primary,
};

export const ML_NAMES: Record<MlBasis, string> = {
  historical: "Historical mean",
  ml: "ML estimate",
  historical_stochastic: "Historical, sampled days",
  ml_stochastic: "ML, sampled days",
};

export const METRIC_LABELS: Record<MetricKey, string> = {
  weighted_cost: "Weighted cost",
  urgent_waiting_min: "Urgent and Immediate waiting (min)",
  overtime_min: "Overtime (min)",
  deferred_min: "Surgery deferred off today (min)",
  performed_min: "Surgery done today (min)",
  waiting_min: "Waiting from ready (min)",
  cancellations: "Cases deferred off today",
  idle_min: "Idle (min)",
  pacu_queue_min: "Recovery queue (bed-min)",
  changes: "Schedule changes",
  violations: "Plan violations after the disruption",
  executed_violations: "Executed-timeline violations",
  finish_error_min: "Room finish vs published (min off)",
  late_start_min: "Case start after published time (min)",
};

export const METRIC_ORDER: MetricKey[] = [
  "weighted_cost",
  "urgent_waiting_min",
  "overtime_min",
  "deferred_min",
  "performed_min",
  "waiting_min",
  "cancellations",
  "idle_min",
  "pacu_queue_min",
  "changes",
  "violations",
  "executed_violations",
  "finish_error_min",
  "late_start_min",
];

/** Metrics where less is better (performed surgery and schedule changes are not) */
export const LOWER_BETTER = new Set<MetricKey>([
  "overtime_min",
  "waiting_min",
  "urgent_waiting_min",
  "cancellations",
  "deferred_min",
  "idle_min",
  "pacu_queue_min",
  "violations",
  "executed_violations",
  "weighted_cost",
  "finish_error_min",
  "late_start_min",
]);

export const DISRUPTION_NAMES: Record<string, string> = {
  overrun: "60-minute overrun",
  emergency: "Emergency arrival",
  room_outage: "OR 1 closed",
  pacu: "Recovery beds cut to 2",
  overrun_then_emergency: "Overrun, then emergency",
};

export const SOLVER_NAMES: Record<string, string> = {
  "cp-sat": "Optimal",
  "cp-sat-feasible": "Feasible, not proven optimal",
  greedy: "Fallback",
  shift_only: "Shift only",
};

export const WEIGHT_LABELS: Record<string, string> = {
  overtime_per_min: "Overtime, per minute",
  idle_per_min: "Idle, per minute",
  wait_elective_per_min: "Elective waiting, per minute",
  wait_expedited_per_min: "Expedited waiting, per minute",
  wait_urgent_per_min: "Urgent waiting, per minute",
  wait_immediate_per_min: "Immediate waiting, per minute",
  cancel_elective: "Defer an elective off today",
  cancel_expedited: "Defer an expedited case off today",
  change: "Move a case off its previous room",
  urgent_late_per_min: "Urgent start after 14:00, per minute",
  immediate_late_per_min: "Immediate start over 60 min after arrival, per minute",
};

const signed = (n: number) => `${n > 0 ? "+" : ""}${n}`;

/** "-69.3 (-90.9 to -47.7)" */
export function pairedText(d: PairedDiff | undefined): string {
  if (!d) return "—";
  return d.low == null || d.high == null ? signed(d.mean) : `${signed(d.mean)} (${d.low} to ${d.high})`;
}

export const thousands = (n: number) => n.toLocaleString("en-US");
