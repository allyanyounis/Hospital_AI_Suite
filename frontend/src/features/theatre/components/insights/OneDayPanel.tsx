"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Badge, Card, Notice, Spinner, Toggle } from "@/shared/ui/ui";
import { theatreApi } from "../../api";
import type { ExperimentDay, ExperimentInput, ExperimentRun, MetricKey, PlanChange } from "../../insightsTypes";
import { hm } from "../../lib/time";
import { DISRUPTION_NAMES, LOWER_BETTER, METRIC_LABELS, METRIC_ORDER, SOLVER_NAMES } from "./labels";
import { DataTable, Panel } from "./parts";
import { PlanLanes, PlanLegend } from "./PlanLanes";

const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";

const KIND: Record<PlanChange["kind"], { label: string; tone: "bad" | "ok" | "warn" | "info" }> = {
  deferred: { label: "Deferred", tone: "bad" },
  moved: { label: "Moved room", tone: "warn" },
  shifted: { label: "Start moved", tone: "info" },
  added: { label: "Added", tone: "ok" },
};

/** Metrics compared on the day: without replanning against with it */
const DAY_METRICS: MetricKey[] = METRIC_ORDER.filter((k) => k !== "finish_error_min" && k !== "late_start_min");

/**
 * Replan one seeded, simulated day with CP-SAT (a few seconds) and compare it with leaving the list as it was.
 * Shows the published example until the user runs a day. Never touches the real theatre lists.
 */
export function OneDayPanel({ example }: { example: ExperimentDay }) {
  const [seed, setSeed] = useState(String(example.seed));
  const [form, setForm] = useState<Omit<ExperimentInput, "seed">>({
    disruption: "",
    second: false,
    when: "midday",
    profile: "balanced",
    stress: false,
  });
  const run = useMutation({ mutationFn: (input: ExperimentInput) => theatreApi.runExperiment(input) });
  const seedOk = /^\d+$/.test(seed.trim());
  const day: ExperimentDay | ExperimentRun = run.data ?? example;

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <form
          className="grid items-end gap-3 sm:grid-cols-2 xl:grid-cols-[8rem_1fr_7rem_1fr_auto]"
          onSubmit={(e) => {
            e.preventDefault();
            if (seedOk) run.mutate({ ...form, seed: Number(seed) });
          }}
        >
          <label className={labelClass}>
            Seed
            <input inputMode="numeric" value={seed} onChange={(e) => setSeed(e.target.value)} className={field} />
          </label>
          <label className={labelClass}>
            Disruption
            <select
              value={form.disruption}
              onChange={(e) => setForm({ ...form, disruption: e.target.value as ExperimentInput["disruption"] })}
              className={field}
            >
              <option value="">Whatever this seed rotates to</option>
              <option value="overrun">60-minute overrun</option>
              <option value="emergency">Emergency arrival</option>
              <option value="room_outage">OR 1 closed</option>
              <option value="pacu">Recovery beds cut to 2</option>
            </select>
          </label>
          <label className={labelClass}>
            When
            <select
              value={form.when}
              onChange={(e) => setForm({ ...form, when: e.target.value as ExperimentInput["when"] })}
              className={field}
            >
              <option value="early">09:00</option>
              <option value="midday">10:30</option>
              <option value="late">14:00</option>
            </select>
          </label>
          <label className={labelClass}>
            Weights
            <select
              value={form.profile}
              onChange={(e) => setForm({ ...form, profile: e.target.value as ExperimentInput["profile"] })}
              className={field}
            >
              <option value="balanced">Balanced</option>
              <option value="protect_electives">Protect electives</option>
              <option value="avoid_overtime">Avoid overtime</option>
            </select>
          </label>
          <button
            disabled={run.isPending || !seedOk}
            className="flex items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:opacity-50"
          >
            {run.isPending ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Sparkles />}
            {run.isPending ? "Solving…" : "Run this day"}
          </button>
          <div className="flex flex-wrap gap-6 sm:col-span-2 xl:col-span-5">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <Toggle checked={form.second} onChange={(v) => setForm({ ...form, second: v })} label="Second emergency" />
              Then an emergency 90 minutes later
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <Toggle checked={form.stress} onChange={(v) => setForm({ ...form, stress: v })} label="Stress durations" />
              Every case 25% longer than planned
            </label>
          </div>
        </form>
        {!seedOk && <p className="mt-2 text-xs text-rose-700">The seed is a whole number.</p>}
        <p className="mt-3 text-xs text-slate-500">
          A simulated day: running it does not book, move or cancel anything on the theatre board.
        </p>
      </Card>

      {run.isError && <Notice tone="error">{run.error.message}</Notice>}
      {run.isPending ? (
        <Card className="flex flex-col items-center gap-3 py-16 text-sm text-slate-500">
          <Spinner className="h-6 w-6" />
          Replanning the day with CP-SAT…
        </Card>
      ) : (
        <DayResult day={day} published={!run.data} />
      )}
    </div>
  );
}

function DayResult({ day, published }: { day: ExperimentDay | ExperimentRun; published: boolean }) {
  const events = day.events?.length ? day.events : [day.disruption];
  const when = events.map((ev) => `${DISRUPTION_NAMES[ev.type] ?? ev.type} at ${hm(ev.at)}`).join(", then ");
  const changed = new Set(day.changes.map((c) => c.case_id));
  const blocked = day.changes.find((c) => c.blocked)?.blocked;

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
        <Badge tone={published ? "neutral" : "brand"}>{published ? "Published example" : "Your run"}</Badge>
        <span>
          Seed <b className="tabular-nums text-slate-900">{day.seed}</b> · {when}
        </span>
        <Badge tone={day.fallback ? "warn" : "ok"}>Solver: {SOLVER_NAMES[day.solver] ?? day.solver}</Badge>
      </div>
      {day.note && <p className="text-xs text-slate-500">{day.note}</p>}

      <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {DAY_METRICS.filter((k) => day.no_replan[k] != null && day.recovery[k] != null).map((k) => {
          const before = day.no_replan[k] ?? 0;
          const after = day.recovery[k] ?? 0;
          const tone =
            !LOWER_BETTER.has(k) || before === after
              ? "text-slate-700"
              : after < before
                ? "text-emerald-700"
                : "text-rose-700";
          return (
            <Card key={k} className="p-3">
              <p className="truncate text-[11px] text-slate-500" title={METRIC_LABELS[k]}>
                {METRIC_LABELS[k]}
              </p>
              <p className={`text-sm font-bold tabular-nums ${tone}`}>
                {before} <span className="font-normal text-slate-400">→</span> {after}
              </p>
            </Card>
          );
        })}
      </div>
      <p className="text-xs text-slate-500">Left: the list left as it was. Right: after replanning.</p>

      <div className="grid gap-5 2xl:grid-cols-2">
        <Panel title="Original plan">
          <PlanLanes rows={day.original} rooms={day.rooms} changed={new Set()} />
        </Panel>
        <Panel title="After replanning">
          <PlanLanes rows={day.revised} rooms={day.rooms} changed={changed} />
        </Panel>
      </div>
      <PlanLegend />

      <Panel title="Why cases moved" note={blocked}>
        {day.changes.length === 0 ? (
          <p className="text-sm text-slate-500">No case moved on this seed.</p>
        ) : (
          <DataTable head={["Case", "What changed", "From", "To", "Why"]} left={[0, 1, 2, 3, 4]}>
            {day.changes.map((c) => (
              <tr key={c.case_id}>
                <td className="px-3 py-2">
                  <span className="font-semibold text-slate-900">{c.case_id}</span>
                  <span className="block text-xs text-slate-500">{c.title}</span>
                </td>
                <td className="px-3 py-2">
                  <Badge tone={KIND[c.kind].tone}>{KIND[c.kind].label}</Badge>
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-xs tabular-nums">
                  {c.from_room ? `${c.from_room} ${c.from_start != null ? hm(c.from_start) : ""}` : "—"}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-xs tabular-nums">
                  {c.to_room ? `${c.to_room} ${c.to_start != null ? hm(c.to_start) : ""}` : "—"}
                </td>
                <td className="px-3 py-2 text-xs text-slate-600">{c.reason}</td>
              </tr>
            ))}
          </DataTable>
        )}
      </Panel>
    </>
  );
}
