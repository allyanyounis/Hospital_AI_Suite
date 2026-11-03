"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { CHART } from "@/shared/lib/theme";
import { Segmented } from "@/shared/ui/ui";
import type { DurationModel, Experiment, ExperimentSummary, MetricKey, MlPlanning, Policy, Spread } from "../../insightsTypes";
import { POLICIES } from "../../insightsTypes";
import {
  DISRUPTION_NAMES,
  LOWER_BETTER,
  METRIC_LABELS,
  METRIC_ORDER,
  ML_NAMES,
  pairedText,
  POLICY_COLORS,
  POLICY_NAMES,
  SOLVER_NAMES,
  thousands,
  WEIGHT_LABELS,
} from "./labels";
import { Callout, ChartBox, DataTable, Num, Panel } from "./parts";

type View = "replan" | "ml" | "rules";

const axisTick = { fill: CHART.axis, fontSize: 12 };
const tooltipStyle = { borderRadius: 8, border: "1px solid #f1f5f9", fontSize: 12 };

/** The precomputed replanning experiment: four policies over the same simulated days, the ML duration model, and the rules. */
export function ExperimentPanel({ summary }: { summary: ExperimentSummary }) {
  const [view, setView] = useState<View>("replan");
  const e = summary.experiment;
  return (
    <div className="space-y-5">
      <Segmented<View>
        label="Experiment"
        value={view}
        onChange={setView}
        options={[
          { value: "replan", label: "Recovering after a disruption" },
          { value: "ml", label: "Planning with ML lengths" },
          { value: "rules", label: "Rules & definitions" },
        ]}
      />
      {view === "replan" && <Replanning e={e} />}
      {view === "ml" && <MlView model={summary.duration_model} ml={e.ml_planning} />}
      {view === "rules" && <Rules e={e} />}
    </div>
  );
}

/** Per metric, the key of the lowest mean (for metrics where lower is better). */
function leader<K extends string>(keys: K[], cell: (k: K) => Spread | undefined, metric: MetricKey): K | null {
  if (!LOWER_BETTER.has(metric)) return null;
  let best: K | null = null;
  for (const k of keys) {
    const v = cell(k)?.mean;
    if (v != null && (best === null || v < (cell(best)?.mean ?? Infinity))) best = k;
  }
  return best;
}

function SpreadCell({ cell, lead }: { cell: Spread | undefined; lead: boolean }) {
  return (
    <Num strong={lead}>
      {cell ? (
        <>
          {cell.mean}
          <span className="block text-[10px] font-normal text-slate-400">
            {cell.p10}–{cell.p90}
          </span>
        </>
      ) : (
        "—"
      )}
    </Num>
  );
}

function Replanning({ e }: { e: Experiment }) {
  const vsRule = e.paired.recovery_minus_cpsat;
  const vsOne = e.paired.recovery_minus_heuristic;
  const policyBars = (key: MetricKey) => POLICIES.map((p) => ({ policy: p, name: POLICY_NAMES[p], value: e.metrics[p][key]?.mean ?? 0 }));
  const byKind = Object.entries(e.by_disruption).map(([kind, row]) => ({
    kind: DISRUPTION_NAMES[kind] ?? kind,
    ...Object.fromEntries(POLICIES.map((p) => [p, row[p]?.overtime_min ?? 0])),
  }));
  const metrics = METRIC_ORDER.filter((k) => e.metrics.baseline[k]);
  const recovery = e.solver_status.recovery ?? {};

  return (
    <>
      <p className="max-w-3xl text-sm text-slate-600">
        After something goes wrong, replan the cases that have not started. The comparison is what a coordinator does by
        hand: keep the order, give an emergency the next free turn and let later cases slide. {e.seeds} simulated days,
        the same cases and the same disruption, handled four ways. The replan sees only an estimate of when a running case
        will end.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Callout diff={vsRule.weighted_cost} unit="" noun="weighted cost than the manual rule" />
        <Callout diff={vsRule.overtime_min} unit=" min" noun="overtime than the manual rule" />
        <Callout diff={vsRule.deferred_min} unit=" min" noun="surgery deferred off today" />
        <Callout diff={vsRule.urgent_waiting_min} unit=" min" noun="Urgent and Immediate waiting" />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <PolicyBars title="Overtime, minutes past 16:00" note="Lower is a shorter day." data={policyBars("overtime_min")} />
        <PolicyBars title="Cases moved off today" note="Lower keeps more of the booked list." data={policyBars("cancellations")} />
      </div>

      <Panel title="Overtime by what went wrong" note="Each group is the same disruption on the days it occurred. Replan is the dark bar.">
        <ChartBox height={280}>
          <BarChart data={byKind} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
            <XAxis dataKey="kind" axisLine={false} tickLine={false} tick={axisTick} />
            <YAxis axisLine={false} tickLine={false} tick={axisTick} />
            <Tooltip cursor={{ fill: CHART.primarySoft, opacity: 0.5 }} contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {POLICIES.map((p) => (
              <Bar key={p} dataKey={p} name={POLICY_NAMES[p]} fill={POLICY_COLORS[p]} radius={[3, 3, 0, 0]} maxBarSize={22} />
            ))}
          </BarChart>
        </ChartBox>
        <p className="mt-3 text-xs text-slate-500">
          Read overtime next to surgery deferred: overtime that falls only because more surgery leaves the day is work moved,
          not time saved. The weighted cost puts both on one scale. Against the one-elective rule the replan&apos;s weighted
          cost differs by {pairedText(vsOne.weighted_cost)}. {e.duration_note}
        </p>
      </Panel>

      <Panel title="Every metric" note="Mean, and 10th–90th percentile across the days. Bold is the lowest where lower is better.">
        <DataTable head={["", ...POLICIES.map((p) => POLICY_NAMES[p])]}>
          {metrics.map((k) => {
            const lead = leader(POLICIES, (p) => e.metrics[p][k], k);
            return (
              <tr key={k}>
                <td className="px-3 py-2 text-slate-700">{METRIC_LABELS[k]}</td>
                {POLICIES.map((p) => (
                  <SpreadCell key={p} cell={e.metrics[p][k]} lead={p === lead} />
                ))}
              </tr>
            );
          })}
        </DataTable>
        <p className="mt-3 text-xs text-slate-500">
          Replan solves on these {e.seeds} days: {recovery["cp-sat"] ?? 0} optimal, {recovery["cp-sat-feasible"] ?? 0}{" "}
          feasible but not proven optimal, {recovery.greedy ?? 0} fallback.
        </p>
      </Panel>

      <Panel title="Same day, two policies" note="Mean difference on the same seed, with a 95% interval inside this simulation.">
        <DataTable head={["", "Replan minus solver + manual rule", "Replan minus one-elective rule"]}>
          {METRIC_ORDER.filter((k) => vsRule[k]).map((k) => (
            <tr key={k}>
              <td className="px-3 py-2 text-slate-700">{METRIC_LABELS[k]}</td>
              <Num>{pairedText(vsRule[k])}</Num>
              <Num>{pairedText(vsOne[k])}</Num>
            </tr>
          ))}
        </DataTable>
      </Panel>
    </>
  );
}

function PolicyBars({
  title,
  note,
  data,
}: {
  title: string;
  note: string;
  data: { policy: Policy; name: string; value: number }[];
}) {
  return (
    <Panel title={title} note={note}>
      <ChartBox height={200}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={CHART.grid} />
          <XAxis type="number" axisLine={false} tickLine={false} tick={axisTick} />
          <YAxis type="category" dataKey="name" width={140} axisLine={false} tickLine={false} tick={axisTick} />
          <Tooltip cursor={{ fill: CHART.primarySoft, opacity: 0.5 }} contentStyle={tooltipStyle} />
          <Bar dataKey="value" name="Mean" radius={4} maxBarSize={22} label={{ position: "right", fill: CHART.axis, fontSize: 12 }}>
            {data.map((d) => (
              <Cell key={d.policy} fill={POLICY_COLORS[d.policy]} />
            ))}
          </Bar>
        </BarChart>
      </ChartBox>
    </Panel>
  );
}

function MlView({ model, ml }: { model: DurationModel; ml: MlPlanning | undefined }) {
  const p = model.point;
  const r = model.range;
  const accuracy: [string, string | number, string | number][] = [
    ["Average error (min)", p.historical_mean.mae_min, p.ml_median.mae_min],
    ["Median error (min)", p.historical_mean.median_abs_min, p.ml_median.median_abs_min],
    ["Within 30 minutes", `${p.historical_mean.within_30_pct}%`, `${p.ml_median.within_30_pct}%`],
    ["1-in-10 worst error (min)", p.historical_mean.p90_abs_min, p.ml_median.p90_abs_min],
    [`P10–P90 range holds the case (target ${r.target_pct}%)`, `${r.historical.coverage_pct}%`, `${r.ml.coverage_pct}%`],
    ["Width of that range (min)", r.historical.width_min, r.ml.width_min],
  ];
  const drivers = [...model.drivers].sort((a, b) => b.importance - a.importance);

  return (
    <>
      <p className="max-w-3xl text-sm text-slate-600">
        A gradient-boosted model predicts each operation&apos;s length and its likely range from what is known before the
        day. The solver can then plan across sampled versions of the day drawn from that range instead of trusting one
        number per case.
      </p>
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Is the prediction better?" note={`On ${thousands(model.cases.test)} held-out VitalDB patients.`}>
          <DataTable head={["", "Historical mean", "ML"]}>
            {accuracy.map(([label, hist, mlv]) => (
              <tr key={label}>
                <td className="px-3 py-2 text-slate-700">{label}</td>
                <Num>{hist}</Num>
                <Num strong>{mlv}</Num>
              </tr>
            ))}
          </DataTable>
        </Panel>
        <Panel title="What moves the prediction most" note="Relative importance of each input.">
          <ChartBox height={260}>
            <BarChart data={drivers} layout="vertical" margin={{ top: 0, right: 16, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={CHART.grid} />
              <XAxis type="number" axisLine={false} tickLine={false} tick={axisTick} />
              <YAxis type="category" dataKey="feature" width={120} axisLine={false} tickLine={false} tick={axisTick} />
              <Tooltip cursor={{ fill: CHART.primarySoft, opacity: 0.5 }} contentStyle={tooltipStyle} />
              <Bar dataKey="importance" name="Importance" fill={CHART.primary} radius={4} maxBarSize={18} />
            </BarChart>
          </ChartBox>
        </Panel>
      </div>

      <Panel title="Error by department">
        <DataTable head={["Department", "Test cases", "Historical mean error (min)", "ML error (min)"]}>
          {Object.entries(model.departments).map(([name, d]) => (
            <tr key={name}>
              <td className="px-3 py-2 font-medium text-slate-900">{name}</td>
              <Num>{thousands(d.cases)}</Num>
              <Num>{d.historical_mae_min}</Num>
              <Num strong={d.ml_mae_min < d.historical_mae_min}>{d.ml_mae_min}</Num>
            </tr>
          ))}
        </DataTable>
      </Panel>

      {ml && (
        <Panel
          title={`Planning with each estimate, ${ml.seeds} days`}
          note="Mean, and 10th–90th percentile. Every day is a list of real VitalDB patients the model never trained on, played with their actual minutes."
        >
          <DataTable head={["", ...ml.bases.map((b) => ML_NAMES[b])]}>
            {METRIC_ORDER.filter((k) => ml.metrics[ml.bases[0]]?.[k]).map((k) => {
              const lead = leader(ml.bases, (b) => ml.metrics[b][k], k);
              return (
                <tr key={k}>
                  <td className="px-3 py-2 text-slate-700">{METRIC_LABELS[k]}</td>
                  {ml.bases.map((b) => (
                    <SpreadCell key={b} cell={ml.metrics[b][k]} lead={b === lead} />
                  ))}
                </tr>
              );
            })}
          </DataTable>
          <p className="mt-3 text-xs text-slate-400">{ml.note}</p>
        </Panel>
      )}
      <p className="text-xs text-slate-400">
        {model.target} {model.split} {model.model} {model.source}
      </p>
    </>
  );
}

function Rules({ e }: { e: Experiment }) {
  const definitions = METRIC_ORDER.filter((k) => e.definitions[k]);
  return (
    <>
      <Panel title="What each number counts">
        <dl className="divide-y divide-slate-100 text-sm">
          {definitions.map((k) => (
            <div key={k} className="grid gap-1 py-2 sm:grid-cols-[16rem_1fr]">
              <dt className="font-medium text-slate-900">{METRIC_LABELS[k]}</dt>
              <dd className="text-slate-600">{e.definitions[k]}</dd>
            </div>
          ))}
        </dl>
        {e.definitions.recovery && <p className="mt-3 text-xs text-slate-500">Replan: {e.definitions.recovery}</p>}
      </Panel>
      <div className="grid gap-5 lg:grid-cols-3">
        <Panel title="Hard rules" note="A plan that breaks one is rejected.">
          <RuleList items={e.contract.hard} />
        </Panel>
        <Panel title="Soft costs" note="The default weights.">
          <dl className="mb-3 space-y-1 text-xs">
            {Object.entries(e.weights).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3">
                <dt className="text-slate-600">{WEIGHT_LABELS[k] ?? k}</dt>
                <dd className="font-semibold tabular-nums text-slate-900">{v}</dd>
              </div>
            ))}
          </dl>
          <RuleList items={e.contract.soft} />
        </Panel>
        <Panel title="Not modelled">
          <RuleList items={e.contract.not_modelled} />
        </Panel>
      </div>
      <Panel title="Solver outcomes" note={`Time limit ${e.time_limit_s} s per solve.`}>
        <DataTable head={["Policy", ...Object.keys(SOLVER_NAMES).map((k) => SOLVER_NAMES[k])]}>
          {POLICIES.map((p) => (
            <tr key={p}>
              <td className="px-3 py-2 font-medium text-slate-900">{POLICY_NAMES[p]}</td>
              {Object.keys(SOLVER_NAMES).map((k) => (
                <Num key={k}>{e.solver_status[p]?.[k] ?? 0}</Num>
              ))}
            </tr>
          ))}
        </DataTable>
      </Panel>
    </>
  );
}

function RuleList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-600">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}
