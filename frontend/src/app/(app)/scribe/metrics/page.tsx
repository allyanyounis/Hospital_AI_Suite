"use client";

import { useEffect, useState } from "react";
import { useSession } from "@/components/shell/SessionProvider";
import { api, type Metrics, type User } from "@/lib/api";

export default function MetricsPage() {
  return (
    <>
      <MetricsBody />
    </>
  );
}

function MetricsBody() {
  const { user } = useSession();
  return <Dashboard user={user} />;
}

function Dashboard({ user }: { user: User }) {
  const [all, setAll] = useState(user.role === "admin");
  const [loaded, setLoaded] = useState<{ all: boolean; metrics: Metrics } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .metrics(all)
      .then((metrics) => setLoaded({ all, metrics }))
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load metrics"));
  }, [all]);

  if (error) return <p className="p-6 text-sm text-rose-700">{error}</p>;
  if (!loaded || loaded.all !== all) return <p className="p-6 text-sm text-slate-500">Loading…</p>;
  const { metrics } = loaded;

  const hours = Math.floor(metrics.est_minutes_saved / 60);
  const minutes = metrics.est_minutes_saved % 60;

  return (
    <main className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Pilot metrics · last {metrics.days} days</h2>
          <p className="text-xs text-slate-500">
            {metrics.scope === "all" ? "All clinicians" : "Your encounters"}. Built from timings and edit counts only, never note
            content.
          </p>
        </div>
        {user.role === "admin" && (
          <div className="flex rounded-full border border-slate-300 bg-white p-0.5 text-sm">
            {[
              ["All clinicians", true],
              ["Just me", false],
            ].map(([label, value]) => (
              <button
                key={String(value)}
                onClick={() => setAll(value as boolean)}
                className={`rounded-full px-3 py-1 ${all === value ? "bg-slate-900 text-white" : "text-slate-600"}`}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
        <Stat
          label="Est. documentation time saved"
          value={metrics.notes_approved ? `${hours}h ${minutes}m` : "-"}
          hint={`Assumes ${metrics.baseline_minutes_per_note} min per note without the scribe, minus measured review time`}
        />
        <Stat label="Notes approved" value={metrics.notes_approved} hint={`${metrics.encounters} encounters started`} />
        <Stat
          label="Median review time"
          value={metrics.median_review_minutes !== null ? `${metrics.median_review_minutes} min` : "-"}
          hint={
            metrics.median_draft_seconds !== null
              ? `Draft ready in ${metrics.median_draft_seconds}s (median)`
              : "From draft to approval"
          }
        />
        <Stat
          label="Draft lines kept unchanged"
          value={metrics.lines_kept_pct !== null ? `${metrics.lines_kept_pct}%` : "-"}
          hint="Higher means less rework for clinicians"
        />
        <Stat
          label="Approved after hours"
          value={metrics.after_hours_approvals}
          hint={`Outside ${metrics.workday}; the burnout signal to drive down`}
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-slate-900">Notes approved per day · last 14 days</h3>
        <DailyBars data={metrics.by_day} />
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-slate-900">Safety & documents</h3>
          <dl className="space-y-2 text-sm">
            <Row label="Safety checks run" value={metrics.reviews_run} />
            <Row label="Letters & summaries generated" value={metrics.documents_generated} />
          </dl>
        </section>
        {metrics.by_clinician && (
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-slate-900">By clinician</h3>
            {metrics.by_clinician.length ? (
              <dl className="space-y-2 text-sm">
                {metrics.by_clinician.map((c) => (
                  <Row key={c.username} label={c.name} value={`${c.notes_approved} notes`} />
                ))}
              </dl>
            ) : (
              <p className="text-sm text-slate-500">No approved notes yet.</p>
            )}
          </section>
        )}
      </div>
    </main>
  );
}

function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      <p className="mt-1 text-xs leading-snug text-slate-400">{hint}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between border-b border-slate-100 pb-2 last:border-0">
      <dt className="text-slate-600">{label}</dt>
      <dd className="font-medium tabular-nums text-slate-900">{value}</dd>
    </div>
  );
}

function DailyBars({ data }: { data: Metrics["by_day"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...data.map((d) => d.approved));
  const label = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });

  return (
    <div>
      <div className="relative flex h-40 items-end gap-[2px] border-b border-slate-300">
        {data.map((d, i) => (
          <div
            key={d.date}
            className="relative flex h-full flex-1 items-end"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          >
            <div
              className={`w-full rounded-t-[4px] ${hover === i ? "bg-brand-800" : "bg-brand-600"}`}
              style={{ height: d.approved ? `${(d.approved / max) * 100}%` : 0 }}
            />
            {hover === i && (
              <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs text-white">
                {label(d.date)}: {d.approved} approved
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-xs text-slate-400">
        <span>{label(data[0].date)}</span>
        <span>Max {max}/day</span>
        <span>{label(data[data.length - 1].date)}</span>
      </div>
      <table className="sr-only">
        <caption>Notes approved per day</caption>
        <tbody>
          {data.map((d) => (
            <tr key={d.date}>
              <th>{d.date}</th>
              <td>{d.approved}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
