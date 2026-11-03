/**
 * Research insights contracts (/api/theatre/insights): the risk model audit, the CP-SAT replanning experiment and
 * one seeded day. Shapes are the JSON files in backend/app/modules/theatre/data/ and experiment/run.py's one_day.
 * Times of day are minutes after midnight.
 */

// --- Model audit ------------------------------------------------------------------------------------------------

export type RiskFeature = {
  name: string;
  label: string;
  unit: string;
  median: number;
  mean: number;
  sd: number;
  /** Logistic coefficient per standard deviation */
  coef: number;
};

/** Predicted against observed outcome rate for a group of held-out cases */
export type CalibrationGroup = { cases: number; auc: number; predicted_pct: number; observed_pct: number };

export type RiskModel = {
  outcome: string;
  source: string;
  intercept: number;
  features: RiskFeature[];
  cases: number;
  train_cases: number;
  test_cases: number;
  base_rate_pct: number;
  auc: number;
  auc_asa_only: number;
  /** Held-out cases in fifths of predicted risk */
  fifths: { predicted_pct: number; observed_pct: number; cases: number }[];
  emergency: CalibrationGroup;
  departments: Record<string, CalibrationGroup>;
  duration_check: {
    cases: number;
    operations: number;
    mae_operation_min: number;
    mae_with_patient_min: number;
    over_30_pct: number;
    over_mean_pct: number;
    /** Share of cases running past the 90th-percentile finish (intended: 10%) */
    over_p90_pct: number;
  };
  anesthesia: {
    median_total_min: number;
    median_surgery_min: number;
    median_before_incision_min: number;
    median_after_closure_min: number;
  };
};

export type SimulationPeriod = {
  booked: number;
  done: number;
  cancelled: number;
  overtime_min: number;
  cancel_pct: number;
};

/** Five simulated years of the theatre suite */
export type SimulationSummary = {
  evidence_label: string;
  duration_label: string;
  seed: number;
  start: string;
  end: string;
  weekdays: number;
  rooms: number;
  procedures_available: number;
  procedures_used: number;
  booked: number;
  done: number;
  cancelled: number;
  cancel_pct: number;
  overtime_min: number;
  overtime_hours: number;
  median_day_overtime_min: number;
  p90_day_overtime_min: number;
  max_day_overtime_min: number;
  days_without_overtime_pct: number;
  in_room_min: number;
  staffed_min: number;
  staffed_share_pct: number;
  benchmark_usd_per_min: number;
  benchmark_overtime_usd: number;
  reasons: { id: string; label: string; count: number }[];
  years: (SimulationPeriod & { year: number; in_room_min: number; staffed_share_pct: number })[];
  quarters: (SimulationPeriod & { label: string })[];
  specialties: (SimulationPeriod & { specialty: string; closed_days: number })[];
  assumptions: string[];
  cleaning_min: Record<string, number>;
};

export type ModelAudit = { model: RiskModel; simulation: SimulationSummary };

// --- Replanning experiment --------------------------------------------------------------------------------------

/** The four ways of handling a disrupted day */
export type Policy = "baseline" | "heuristic" | "cpsat" | "recovery";
export const POLICIES: Policy[] = ["baseline", "heuristic", "cpsat", "recovery"];

export type MetricKey =
  | "overtime_min"
  | "waiting_min"
  | "urgent_waiting_min"
  | "cancellations"
  | "deferred_min"
  | "performed_min"
  | "idle_min"
  | "pacu_queue_min"
  | "changes"
  | "violations"
  | "executed_violations"
  | "weighted_cost"
  | "finish_error_min"
  | "late_start_min";

/** Mean with the 10th–90th percentile over the seeds */
export type Spread = { mean: number; p10: number; p50: number; p90: number };
/** Mean paired difference on the same seeds, with a 95% interval when there is one */
export type PairedDiff = { mean: number; n?: number; low?: number; high?: number };

export type DayMetrics = Partial<Record<MetricKey, number>>;

/** How many solves ended in each status ("cp-sat", "cp-sat-feasible", "greedy", "shift_only") */
export type SolverStatus = Record<string, number>;

export type Disruption = { type: string; at: number };

export type PlanRow = {
  case_id: string;
  title: string;
  specialty: string;
  urgency: "Elective" | "Expedited" | "Urgent" | "Immediate";
  planned_min: number;
  /** null when deferred */
  room_id: string | null;
  start_min: number | null;
  end_min: number | null;
  status: "scheduled" | "deferred";
  surgeon_id: string | null;
};

export type PlanChange = {
  case_id: string;
  title: string;
  kind: "deferred" | "moved" | "shifted" | "added";
  reason: string;
  from_room: string | null;
  to_room: string | null;
  from_start: number | null;
  to_start: number | null;
  /** Why the simplest fix was not possible */
  blocked?: string;
};

/** One simulated day: the plan before the disruption, the replan, and both days as played */
export type ExperimentDay = {
  seed: number;
  disruption: Disruption;
  events?: Disruption[];
  provenance: Record<string, string>;
  weights: Record<string, number>;
  rooms: { id: string; specialty: string }[];
  recovery_beds: number;
  original: PlanRow[];
  revised: PlanRow[];
  changes: PlanChange[];
  recovery: DayMetrics;
  no_replan: DayMetrics;
  solver: string;
  fallback: boolean;
  note?: string;
};

type PolicyBlock = {
  label: string;
  n: number;
  metrics: Record<Policy, Partial<Record<MetricKey, { mean: number }>>>;
  paired: Record<string, Partial<Record<MetricKey, PairedDiff>>>;
  fallbacks: Record<Policy, number>;
  solver_status: Record<Policy, SolverStatus>;
  by_disruption: Record<string, Record<Policy, DayMetrics>>;
  weights: Record<string, number>;
};

export type MlBasis = "historical" | "ml" | "historical_stochastic" | "ml_stochastic";

export type DurationModel = {
  target: string;
  source: string;
  features: string;
  split: string;
  cases: { train: number; calibration: number; test: number };
  model: string;
  point: Record<
    "historical_mean" | "ml_median" | "ml_mean",
    { mae_min: number; median_abs_min: number; p90_abs_min: number; within_30_pct: number; bias_min: number }
  >;
  range: { target_pct: number } & Record<"historical" | "ml_raw" | "ml", { coverage_pct: number; width_min: number }>;
  departments: Record<string, { cases: number; historical_mae_min: number; ml_mae_min: number }>;
  drivers: { feature: string; importance: number }[];
  conformal_widen_log: number;
};

export type MlPlanning = {
  seeds: number;
  bases: MlBasis[];
  metrics: Record<MlBasis, Partial<Record<MetricKey, Spread>>>;
  paired: { left: MlBasis; right: MlBasis; label: string; diff: Partial<Record<MetricKey, PairedDiff>> }[];
  frontier: {
    basis: MlBasis;
    profile: string;
    overtime_min: number;
    deferred_min: number;
    performed_min: number;
    idle_min: number;
    weighted_cost: number;
  }[];
  frontier_note: string;
  solver_status: Record<MlBasis, SolverStatus>;
  provenance: Record<string, string>;
  duration_model: DurationModel;
  note: string;
};

export type Experiment = {
  seeds: number;
  seed_file: string;
  time_limit_s: number;
  policies: Policy[];
  label: string;
  metrics: Record<Policy, Partial<Record<MetricKey, Spread>>>;
  paired: Record<"recovery_minus_cpsat" | "recovery_minus_heuristic", Partial<Record<MetricKey, PairedDiff>>>;
  /** Mean metrics per disruption kind ("overrun", "emergency", "room_outage", "pacu") */
  by_disruption: Record<string, Record<Policy, DayMetrics>>;
  fallbacks: Record<Policy, number>;
  solver_status: Record<Policy, SolverStatus>;
  provenance: Record<string, string>;
  weights: Record<string, number>;
  /** The published example day */
  example: ExperimentDay;
  contract: { hard: string[]; soft: string[]; not_modelled: string[] };
  duration_note: string;
  definitions: Partial<Record<MetricKey | "recovery", string>>;
  extensions?: {
    n: number;
    note: string;
    sensitivity: (PolicyBlock & { profile: string })[];
    timing: PolicyBlock[];
    combined: PolicyBlock;
    stress: PolicyBlock;
  };
  ml_planning?: MlPlanning;
};

export type ExperimentSummary = { experiment: Experiment; duration_model: DurationModel };

export type ExperimentInput = {
  seed: number;
  disruption: "" | "overrun" | "emergency" | "room_outage" | "pacu";
  second: boolean;
  when: "early" | "midday" | "late";
  profile: "balanced" | "protect_electives" | "avoid_overtime";
  stress: boolean;
};

export type ExperimentRun = ExperimentDay & { profile: ExperimentInput["profile"]; duration_stress: boolean };
