"use client";

import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Activity, Clock, DollarSign, PhoneCall, Timer, Info } from "lucide-react";
import { useMounted } from "@/shared/hooks";
import { CHART } from "@/shared/lib/theme";
import { PageHeader } from "@/shared/ui/ui";
import { KpiCard, ShareBar } from "../components/MonitoringCards";
import {
  COST_PER_MINUTE,
  DATA,
  OUTCOME_BADGE,
  OUTCOMES,
  RATES,
  RECENT_CALLS,
  costOf,
  formatCallDuration,
  pkr,
  sum,
  usd,
  type Period,
  type Range,
} from "../monitoringData";

// ---------------------------------------------------------------------------
// Static sample data (replace with VAPI call data later)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------
export function MonitoringView() {
  const mounted = useMounted();
  const [range, setRange] = useState<Range>("week");
  const { periods, previous, caption } = DATA[range];
  const calls = sum(periods, "calls");
  const minutes = sum(periods, "minutes");
  const cost = costOf(minutes);
  const pctChange = (now: number, before: number) => ((now - before) / before) * 100;
  const periodWord = range === "week" ? "last week" : "last month";

  return (
    <main className="space-y-6 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Activity className="h-6 w-6" />}
        title="Call Costs"
        subtitle="How many calls the AI receptionist handled and what they cost."
        aside={
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
              <Info className="w-3.5 h-3.5" /> Sample data
            </span>
            <div className="flex rounded-lg border border-slate-200 bg-white p-0.5">
              {(["week", "month"] as Range[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRange(r)}
                  className={`px-4 py-1.5 rounded-md text-sm font-semibold ${range === r ? "bg-brand-700 text-white" : "text-slate-600 hover:text-brand-700"}`}
                >
                  {r === "week" ? "This week" : "This month"}
                </button>
              ))}
            </div>
          </div>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        <KpiCard
          title="Total Calls"
          icon={PhoneCall}
          value={String(calls)}
          change={pctChange(calls, previous.calls)}
          note={`vs ${periodWord}`}
        />
        <KpiCard
          title="Total Cost"
          icon={DollarSign}
          value={usd(cost)}
          change={pctChange(cost, costOf(previous.minutes))}
          note={`≈ ${pkr(cost)} · vs ${periodWord}`}
        />
        <KpiCard title="Avg Cost per Call" icon={DollarSign} value={usd(cost / calls)} note={`≈ ${pkr(cost / calls)} per call`} />
        <KpiCard
          title="Cost per Minute"
          icon={Timer}
          value={`$${COST_PER_MINUTE.toFixed(3)}`}
          note={`≈ ${pkr(COST_PER_MINUTE)} per minute`}
        />
        <KpiCard
          title="Talk Time"
          icon={Clock}
          value={`${Math.round(minutes)} min`}
          note={`${(minutes / calls).toFixed(1)} min average call`}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Calls chart */}
        <div className="xl:col-span-2 rounded-2xl border border-slate-200/80 bg-white shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-800">Calls {range === "week" ? "per day" : "per week"}</h3>
          <p className="text-xs text-slate-500 mt-0.5 mb-4">{caption}. Hover a bar to see its cost.</p>
          {mounted && (
            <ResponsiveContainer
              width="100%"
              height={280}
              minWidth={0}
              minHeight={280}
              initialDimension={{ width: 1, height: 280 }}
            >
              <BarChart data={periods} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: CHART.axis }} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: CHART.axis }} />
                <Tooltip
                  cursor={{ fill: CHART.primarySoft }}
                  formatter={(value, _name, item) => [
                    `${value} calls · ${usd(costOf((item.payload as Period).minutes))}`,
                    "Calls",
                  ]}
                />
                <Bar dataKey="calls" fill={CHART.primary} radius={[4, 4, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Cost breakdown */}
        <div className="rounded-2xl border border-slate-200/80 bg-white shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-800">Where the money goes</h3>
          <p className="text-xs text-slate-500 mt-0.5 mb-5">
            {usd(cost)} this {range} for {Math.round(minutes)} minutes at ${COST_PER_MINUTE.toFixed(3)} / min.
          </p>
          <div className="space-y-4">
            {RATES.map((r) => (
              <div key={r.name}>
                <ShareBar
                  name={r.name}
                  share={r.perMinute / COST_PER_MINUTE}
                  value={r.perMinute ? usd(costOf(minutes) * (r.perMinute / COST_PER_MINUTE)) : "FREE"}
                />
                <p className="text-xs text-slate-400 mt-1">
                  {r.provider} · {r.perMinute ? `$${r.perMinute} / min` : "$0.00 / min"}
                </p>
              </div>
            ))}
          </div>
          <div className="flex justify-between text-sm font-semibold text-slate-800 border-t border-slate-100 mt-5 pt-3">
            <span>Total per minute</span>
            <span>
              ${COST_PER_MINUTE.toFixed(3)} ≈ {pkr(COST_PER_MINUTE)}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Outcomes */}
        <div className="rounded-2xl border border-slate-200/80 bg-white shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-800">Call outcomes</h3>
          <p className="text-xs text-slate-500 mt-0.5 mb-5">What happened on the {calls} calls.</p>
          <div className="space-y-4">
            {OUTCOMES.map((o) => (
              <ShareBar
                key={o.name}
                name={o.name}
                share={o.share}
                className={o.className}
                value={`${Math.round(calls * o.share)} · ${Math.round(o.share * 100)}%`}
              />
            ))}
          </div>
        </div>

        {/* Recent calls */}
        <div className="xl:col-span-2 rounded-2xl border border-slate-200/80 bg-white shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-800 mb-4">Recent calls</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                  <th className="py-2 pr-4 font-medium">Time</th>
                  <th className="py-2 pr-4 font-medium">Caller</th>
                  <th className="py-2 pr-4 font-medium">Duration</th>
                  <th className="py-2 pr-4 font-medium">Outcome</th>
                  <th className="py-2 font-medium text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {RECENT_CALLS.map((c) => (
                  <tr key={c.time} className="border-b border-slate-50 last:border-0">
                    <td className="py-2.5 pr-4 text-slate-700 whitespace-nowrap">{c.time}</td>
                    <td className="py-2.5 pr-4 text-slate-600">{c.caller}</td>
                    <td className="py-2.5 pr-4 text-slate-600">{formatCallDuration(c.seconds)}</td>
                    <td className="py-2.5 pr-4">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${OUTCOME_BADGE[c.outcome]}`}>
                        {c.outcome}
                      </span>
                    </td>
                    <td className="py-2.5 text-right font-semibold text-slate-800">{usd(costOf(c.seconds / 60))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
