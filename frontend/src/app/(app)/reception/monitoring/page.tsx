"use client";

import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Activity, Clock, DollarSign, PhoneCall, Timer, TrendingDown, TrendingUp, Info } from "lucide-react";
import { PageHeader } from "@/components/ui";
import { useMounted } from "@/lib/hooks";
import { CHART } from "@/lib/theme";

// ---------------------------------------------------------------------------
// Static sample data (replace with VAPI call data later)
// ---------------------------------------------------------------------------
type Range = "week" | "month";

// Actual per-minute rates of the current VAPI assistant setup (USD)
const RATES = [
  { name: "VAPI platform fee", provider: "VAPI", perMinute: 0.05 },
  { name: "Language model (LLM)", provider: "OpenAI GPT-4.1", perMinute: 0.02 },
  { name: "Text-to-speech (voice)", provider: "Elliot (VAPI Voice)", perMinute: 0.02 },
  { name: "Speech-to-text (transcriber)", provider: "Soniox / Deepgram", perMinute: 0.004 },
  { name: "Telephony / carrier", provider: "WebRTC browser audio", perMinute: 0 },
];
const COST_PER_MINUTE = RATES.reduce((t, r) => t + r.perMinute, 0); // $0.094
const PKR_PER_USD = 278; // ~25 PKR for $0.09

interface Period {
  label: string;
  calls: number;
  minutes: number;
}

const DATA: Record<Range, { periods: Period[]; previous: { calls: number; minutes: number }; caption: string }> = {
  week: {
    caption: "Last 7 days",
    periods: [
      { label: "Mon", calls: 18, minutes: 41.4 },
      { label: "Tue", calls: 22, minutes: 53.9 },
      { label: "Wed", calls: 15, minutes: 34.5 },
      { label: "Thu", calls: 26, minutes: 65.0 },
      { label: "Fri", calls: 20, minutes: 46.0 },
      { label: "Sat", calls: 9, minutes: 19.8 },
      { label: "Sun", calls: 3, minutes: 5.7 },
    ],
    previous: { calls: 101, minutes: 227.2 },
  },
  month: {
    caption: "Last 4 weeks",
    periods: [
      { label: "Week 1", calls: 94, minutes: 220.0 },
      { label: "Week 2", calls: 101, minutes: 227.2 },
      { label: "Week 3", calls: 117, minutes: 276.1 },
      { label: "Week 4", calls: 113, minutes: 266.3 },
    ],
    previous: { calls: 382, minutes: 889.5 },
  },
};

const OUTCOMES = [
  { name: "Appointment booked", share: 0.46, className: "bg-brand-700" },
  { name: "Availability checked only", share: 0.27, className: "bg-brand-400" },
  { name: "Appointment cancelled", share: 0.11, className: "bg-amber-400" },
  { name: "Caller hung up / no action", share: 0.16, className: "bg-slate-300" },
];

const RECENT_CALLS = [
  { time: "Today, 11:42 AM", caller: "Web call", seconds: 192, outcome: "Booked" },
  { time: "Today, 10:15 AM", caller: "Web call", seconds: 108, outcome: "Availability" },
  { time: "Today, 9:31 AM", caller: "Web call", seconds: 175, outcome: "Booked" },
  { time: "Yesterday, 4:20 PM", caller: "Web call", seconds: 34, outcome: "Hung up" },
  { time: "Yesterday, 2:05 PM", caller: "Web call", seconds: 130, outcome: "Cancelled" },
  { time: "Yesterday, 11:47 AM", caller: "Web call", seconds: 220, outcome: "Booked" },
];

const OUTCOME_BADGE: Record<string, string> = {
  Booked: "bg-green-100 text-green-700",
  Availability: "bg-brand-100 text-brand-700",
  Cancelled: "bg-amber-100 text-amber-700",
  "Hung up": "bg-slate-100 text-slate-600",
};

const usd = (n: number) => `$${n.toFixed(2)}`;
const pkr = (n: number) => `Rs ${Math.round(n * PKR_PER_USD).toLocaleString()}`;
const costOf = (minutes: number) => minutes * COST_PER_MINUTE;
const formatDuration = (s: number) => `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
const sum = (periods: Period[], key: "calls" | "minutes") => periods.reduce((t, p) => t + p[key], 0);

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------
function KpiCard({
  title,
  icon: Icon,
  value,
  note,
  change,
}: {
  title: string;
  icon: React.ElementType;
  value: string;
  note: string;
  change?: number;
}) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white shadow-sm p-5 card-hover">
      <div className="flex items-center justify-between text-slate-600 mb-3">
        <span className="text-sm font-medium">{title}</span>
        <Icon className="w-4 h-4 text-slate-400" />
      </div>
      <p className="text-3xl font-bold text-slate-800">{value}</p>
      <div className="flex items-center gap-2 mt-1">
        {change !== undefined && (
          <span className={`flex items-center gap-0.5 text-xs font-semibold ${change >= 0 ? "text-green-600" : "text-red-500"}`}>
            {change >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {Math.abs(change).toFixed(0)}%
          </span>
        )}
        <span className="text-xs text-slate-400">{note}</span>
      </div>
    </div>
  );
}

function ShareBar({
  name,
  value,
  share,
  className = "bg-brand-700",
}: {
  name: string;
  value: string;
  share: number;
  className?: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-700">{name}</span>
        <span className="font-semibold text-slate-800">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full ${className}`} style={{ width: `${share * 100}%` }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function MonitoringPage() {
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
                    <td className="py-2.5 pr-4 text-slate-600">{formatDuration(c.seconds)}</td>
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
