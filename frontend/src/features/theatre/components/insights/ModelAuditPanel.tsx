"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { CHART } from "@/shared/lib/theme";
import { Icons } from "@/shared/ui/icons";
import { Badge, Segmented, StatCard } from "@/shared/ui/ui";
import type { ModelAudit, RiskModel, SimulationSummary } from "../../insightsTypes";
import { span } from "../../lib/time";
import { thousands } from "./labels";
import { ChartBox, DataTable, Num, Panel } from "./parts";

type View = "risk" | "durations" | "simulation";

const axisTick = { fill: CHART.axis, fontSize: 12 };
const tooltipStyle = { borderRadius: 8, border: "1px solid #f1f5f9", fontSize: 12 };

/** The risk score and duration checks against held-out VitalDB patients, and five simulated years of the suite. */
export function ModelAuditPanel({ audit }: { audit: ModelAudit }) {
  const [view, setView] = useState<View>("risk");
  return (
    <div className="space-y-5">
      <Segmented<View>
        label="Model check"
        value={view}
        onChange={setView}
        options={[
          { value: "risk", label: "Risk score" },
          { value: "durations", label: "Operation lengths" },
          { value: "simulation", label: "Five simulated years" },
        ]}
      />
      {view === "risk" && <RiskCheck model={audit.model} />}
      {view === "durations" && <DurationCheck model={audit.model} />}
      {view === "simulation" && <Simulation sim={audit.simulation} />}
    </div>
  );
}

function RiskCheck({ model: m }: { model: RiskModel }) {
  const fifths = m.fifths.map((f, i) => ({ ...f, label: `${["1st", "2nd", "3rd", "4th", "5th"][i] ?? `${i + 1}th`} fifth` }));
  const coefs = [...m.features].sort((a, b) => Math.abs(b.coef) - Math.abs(a.coef));
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<Icons.Gauge />}
          label="Discrimination (AUC)"
          value={m.auc}
          note={`ASA grade alone: ${m.auc_asa_only}`}
        />
        <StatCard
          icon={<Icons.Users />}
          label="Held-out patients"
          value={thousands(m.test_cases)}
          note={`Trained on ${thousands(m.train_cases)}`}
        />
        <StatCard icon={<Icons.Activity />} label="Outcome rate" value={`${m.base_rate_pct}%`} note={m.outcome} />
        <StatCard
          icon={<Icons.Siren />}
          label="Emergencies: predicted / seen"
          value={`${m.emergency.predicted_pct}% / ${m.emergency.observed_pct}%`}
          note={`${m.emergency.cases} cases, AUC ${m.emergency.auc}`}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          title="Calibration: predicted against seen"
          note={`${thousands(m.test_cases)} held-out patients in fifths of predicted risk. Bars of equal height mean the percentages can be taken at face value.`}
        >
          <ChartBox height={260}>
            <BarChart data={fifths} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
              <XAxis dataKey="label" axisLine={false} tickLine={false} tick={axisTick} />
              <YAxis unit="%" axisLine={false} tickLine={false} tick={axisTick} />
              <Tooltip cursor={{ fill: CHART.primarySoft, opacity: 0.5 }} contentStyle={tooltipStyle} formatter={(v) => `${v}%`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="predicted_pct" name="Predicted" fill={CHART.primary} radius={[4, 4, 0, 0]} maxBarSize={32} />
              <Bar dataKey="observed_pct" name="Seen" fill={CHART.accent} radius={[4, 4, 0, 0]} maxBarSize={32} />
            </BarChart>
          </ChartBox>
        </Panel>

        <Panel
          title="What moves the score"
          note="Logistic coefficients per standard deviation. Red raises the risk, grey lowers it."
        >
          <ChartBox height={260}>
            <BarChart data={coefs} layout="vertical" margin={{ top: 0, right: 16, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={CHART.grid} />
              <XAxis type="number" axisLine={false} tickLine={false} tick={axisTick} />
              <YAxis type="category" dataKey="label" width={96} axisLine={false} tickLine={false} tick={axisTick} />
              <Tooltip
                cursor={{ fill: CHART.primarySoft, opacity: 0.5 }}
                contentStyle={tooltipStyle}
                formatter={(v) => Number(v).toFixed(3)}
              />
              <Bar dataKey="coef" name="Coefficient" radius={4} maxBarSize={18}>
                {coefs.map((f) => (
                  <Cell key={f.name} fill={f.coef >= 0 ? CHART.risk : CHART.axis} />
                ))}
              </Bar>
            </BarChart>
          </ChartBox>
        </Panel>
      </div>

      <Panel title="By department" note="Where the score holds and where it does not.">
        <DataTable head={["Department", "Cases", "AUC", "Predicted", "Seen"]}>
          {Object.entries(m.departments).map(([name, d]) => (
            <tr key={name}>
              <td className="px-3 py-2 font-medium text-slate-900">{name}</td>
              <Num>{thousands(d.cases)}</Num>
              <Num>{d.auc}</Num>
              <Num>{d.predicted_pct}%</Num>
              <Num className={Math.abs(d.predicted_pct - d.observed_pct) > 10 ? "text-rose-700" : ""}>{d.observed_pct}%</Num>
            </tr>
          ))}
        </DataTable>
        <div className="mt-4 space-y-2 text-sm text-slate-600">
          <p>
            The score predicts <b className="text-slate-800">{m.outcome.toLowerCase()}</b> from pre-operative facts only:
            age, ASA grade, emergency status and the latest haemoglobin, platelets, albumin and creatinine. It is shown on
            the case and is not an input to the scheduler. Heart operations use EuroSCORE II instead, because VitalDB
            under-predicts thoracic surgery.
          </p>
          <p className="text-xs text-slate-400">{m.source}</p>
        </div>
      </Panel>
    </>
  );
}

function DurationCheck({ model: m }: { model: RiskModel }) {
  const d = m.duration_check;
  const a = m.anesthesia;
  const phases = [
    { label: "Before incision", minutes: a.median_before_incision_min, color: CHART.phases.anaes },
    { label: "Surgery", minutes: a.median_surgery_min, color: CHART.phases.surgery },
    { label: "After closure", minutes: a.median_after_closure_min, color: CHART.phases.prep },
  ];
  const total = phases.reduce((n, p) => n + p.minutes, 0);
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<Icons.Clock />}
          label="Ran past the 1-in-10 finish"
          value={`${d.over_p90_pct}%`}
          note="Intended: 10%"
          accent={Math.abs(d.over_p90_pct - 10) > 3}
        />
        <StatCard icon={<Icons.Activity />} label="Average error per case" value={`${d.mae_operation_min} min`} />
        <StatCard icon={<Icons.TrendUp />} label="Over 30 min longer than planned" value={`${d.over_30_pct}%`} />
        <StatCard
          icon={<Icons.Users />}
          label="Checked cases"
          value={thousands(d.cases)}
          note={`${d.operations} kinds of operation`}
        />
      </div>
      <Panel
        title="Room time per operation"
        note={`VitalDB medians: ${span(a.median_total_min)} under anaesthesia, of which ${span(a.median_surgery_min)} is surgery.`}
      >
        <div className="flex h-8 w-full overflow-hidden rounded-lg">
          {phases.map((p) => (
            <div
              key={p.label}
              title={`${p.label}: ${p.minutes} min`}
              style={{ width: `${(p.minutes / total) * 100}%`, background: p.color }}
            />
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-600">
          {phases.map((p) => (
            <span key={p.label} className="flex items-center gap-1.5">
              <i className="h-2.5 w-2.5 rounded-sm" style={{ background: p.color }} />
              {p.label} {span(p.minutes)}
            </span>
          ))}
        </div>
        <p className="mt-4 text-sm text-slate-600">
          Each case is planned as anaesthesia time (induction, preparation, surgery, closing, emergence), not only the
          surgery. Each case also shows a latest finish it runs past only one time in ten; in real VitalDB cases the
          planner had not seen, {d.over_p90_pct}% ran past it. Average error is {d.mae_operation_min} min per case from
          the operation alone and {d.mae_with_patient_min} min with the patient&apos;s facts.
        </p>
      </Panel>
    </>
  );
}

function Simulation({ sim }: { sim: SimulationSummary }) {
  const reasons = [...sim.reasons].sort((a, b) => b.count - a.count);
  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Badge tone="warn">{sim.evidence_label}</Badge>
        <Badge tone="info">{sim.duration_label}</Badge>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<Icons.Calendar />}
          label="Cases booked"
          value={thousands(sim.booked)}
          note={`${thousands(sim.weekdays)} weekdays, ${sim.rooms} rooms`}
        />
        <StatCard icon={<Icons.Alert />} label="Cancelled on the day" value={`${sim.cancel_pct}%`} note={`${thousands(sim.cancelled)} cases`} />
        <StatCard
          icon={<Icons.Clock />}
          label="Overtime"
          value={`${thousands(sim.overtime_hours)} h`}
          note={`1 day in 10 over ${sim.p90_day_overtime_min} min`}
        />
        <StatCard
          icon={<Icons.Gauge />}
          label="Staffed time in use"
          value={`${sim.staffed_share_pct}%`}
          note={`${sim.days_without_overtime_pct}% of days end on time`}
        />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Why cases were cancelled">
          <ChartBox height={240}>
            <BarChart data={reasons} layout="vertical" margin={{ top: 0, right: 16, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={CHART.grid} />
              <XAxis type="number" axisLine={false} tickLine={false} tick={axisTick} />
              <YAxis type="category" dataKey="label" width={190} axisLine={false} tickLine={false} tick={axisTick} />
              <Tooltip cursor={{ fill: CHART.primarySoft, opacity: 0.5 }} contentStyle={tooltipStyle} />
              <Bar dataKey="count" name="Cases" fill={CHART.primary} radius={4} maxBarSize={18} />
            </BarChart>
          </ChartBox>
        </Panel>
        <Panel title="Overtime by quarter" note="Minutes past 16:00, all rooms.">
          <ChartBox height={240}>
            <BarChart data={sim.quarters} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
              <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ ...axisTick, fontSize: 10 }} interval={3} />
              <YAxis axisLine={false} tickLine={false} tick={axisTick} />
              <Tooltip cursor={{ fill: CHART.primarySoft, opacity: 0.5 }} contentStyle={tooltipStyle} />
              <Bar dataKey="overtime_min" name="Overtime (min)" fill={CHART.accent} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ChartBox>
        </Panel>
      </div>
      <Panel title="By specialty">
        <DataTable head={["Specialty", "Booked", "Done", "Cancelled", "Overtime (min)", "Closed days"]}>
          {sim.specialties.map((s) => (
            <tr key={s.specialty}>
              <td className="px-3 py-2 font-medium text-slate-900">{s.specialty}</td>
              <Num>{thousands(s.booked)}</Num>
              <Num>{thousands(s.done)}</Num>
              <Num>
                {thousands(s.cancelled)} <span className="text-xs text-slate-400">({s.cancel_pct}%)</span>
              </Num>
              <Num>{thousands(s.overtime_min)}</Num>
              <Num>{s.closed_days}</Num>
            </tr>
          ))}
        </DataTable>
      </Panel>
      <Panel title="Assumptions">
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-600">
          {sim.assumptions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </Panel>
    </>
  );
}
