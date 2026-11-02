"use client";

import { ArrowDownUp, BellRing, Calendar, Clock, MessageSquareText, RefreshCw, Search, Stethoscope, User, X } from "lucide-react";
import { useState } from "react";
import { Icons } from "@/components/icons";
import { CallTranscriptModal } from "@/components/reception/CallTranscriptModal";
import { Card, Notice, PageHeader } from "@/components/ui";
import { api, type Appointment } from "@/lib/api";
import { nextUp } from "@/lib/appointments";
import { countdown, dayOffset, formatClockTime, formatDate, relativeDay, toDateKey } from "@/lib/format";
import { useAppointments, useNow } from "@/lib/hooks";

type Tab = "upcoming" | "today" | "past" | "cancelled" | "all";
type SortMode = "time" | "booked";

const TABS: { key: Tab; label: string }[] = [
  { key: "upcoming", label: "Upcoming" },
  { key: "today", label: "Today" },
  { key: "past", label: "Past" },
  { key: "cancelled", label: "Cancelled" },
  { key: "all", label: "All" },
];
const NEW_BOOKING_MS = 86_400_000;
const COLUMNS = 8;

function inTab(a: Appointment, tab: Tab, now: Date): boolean {
  const start = new Date(a.start_time);
  switch (tab) {
    case "upcoming":
      return !a.canceled && start >= now;
    case "today":
      return !a.canceled && dayOffset(start, now) === 0;
    case "past":
      return !a.canceled && start < now;
    case "cancelled":
      return a.canceled;
    case "all":
      return true;
  }
}

function statusOf(a: Appointment, now: Date) {
  const start = new Date(a.start_time);
  if (a.canceled) return { label: "Cancelled", className: "bg-rose-100 text-rose-600" };
  if (start < now) return { label: "Past", className: "bg-slate-100 text-slate-500" };
  if (dayOffset(start, now) === 0) return { label: "Today", className: "bg-amber-100 text-amber-800" };
  return { label: "Upcoming", className: "bg-brand-100 text-brand-800" };
}

function dayHeading(date: Date, now: Date): string {
  const label = date.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
  const rel = relativeDay(date, now);
  return ["Today", "Tomorrow", "Yesterday"].includes(rel) ? `${rel} · ${label}` : label;
}

export default function AppointmentsPage() {
  const now = useNow(60_000); // keeps countdowns and Past/Upcoming current
  const { appointments, error, loading, lastUpdated, reload, live } = useAppointments();
  const [date, setDate] = useState("");
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<Tab>("upcoming");
  const [sort, setSort] = useState<SortMode>("time");
  const [transcriptFor, setTranscriptFor] = useState<Appointment | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const list = appointments ?? [];
  const query = search.trim().toLowerCase();
  // Search and date apply before tabs, so the tab counts reflect them
  const searched = list.filter(
    (a) =>
      (a.patient_name.toLowerCase().includes(query) || (a.reason ?? "").toLowerCase().includes(query)) &&
      (!date || toDateKey(new Date(a.start_time)) === date),
  );
  const counts = Object.fromEntries(TABS.map(({ key }) => [key, searched.filter((a) => inTab(a, key, now)).length])) as Record<
    Tab,
    number
  >;

  const startMs = (a: Appointment) => new Date(a.start_time).getTime();
  const visible = searched
    .filter((a) => inTab(a, tab, now))
    .sort((a, b) => {
      if (sort === "booked") return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      // Upcoming and today read soonest-first; the rest latest-first
      return tab === "upcoming" || tab === "today" ? startMs(a) - startMs(b) : startMs(b) - startMs(a);
    });

  // Group by appointment day when sorting by time
  const groups: { heading: string | null; items: Appointment[] }[] = [];
  for (const a of visible) {
    const heading = sort === "time" ? dayHeading(new Date(a.start_time), now) : null;
    const last = groups.at(-1);
    if (last && last.heading === heading) last.items.push(a);
    else groups.push({ heading, items: [a] });
  }

  const next = nextUp(list, now);

  async function cancel(a: Appointment) {
    if (!confirm(`Cancel ${a.patient_name}'s appointment on ${formatDate(new Date(a.start_time))}?`)) return;
    setActionError(null);
    try {
      await api.cancelAppointment(a.id);
      await reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not cancel the appointment");
    }
  }

  let row = 0;

  return (
    <main className="px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.CalendarClock className="h-6 w-6" />}
        title="Appointments"
        subtitle={
          <>
            Booked by the AI voice receptionist, soonest first.{" "}
            <span className={live ? "text-emerald-600" : "text-slate-400"}>{live ? "● Live" : "○ Reconnecting…"}</span>
            {lastUpdated && <span className="ml-2 text-xs text-slate-400">Updated {lastUpdated.toLocaleTimeString()}</span>}
          </>
        }
        aside={
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
              <Calendar className="h-4 w-4 text-slate-400" />
              <input
                type="date"
                value={date}
                aria-label="Filter by date"
                onChange={(e) => {
                  setDate(e.target.value);
                  if (e.target.value) setTab("all"); // a chosen date may be in the past
                }}
                className="bg-transparent text-sm text-slate-700 outline-none"
              />
              {date && (
                <button onClick={() => setDate("")} title="Clear date" className="text-slate-400 hover:text-slate-700">
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <button
              onClick={reload}
              disabled={loading}
              className="flex items-center gap-2 rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        }
      />

      {(error || actionError) && (
        <Notice tone="error" className="mb-4">
          {error || actionError}
        </Notice>
      )}

      {next ? (
        <div className="mb-6 flex flex-col gap-4 rounded-2xl bg-gradient-to-r from-brand-700 to-brand-800 p-5 text-white shadow-md sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white/15">
              <BellRing className="h-6 w-6" />
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-white/70">Next up</p>
              <p className="text-xl font-bold">{next.patient_name}</p>
              <p className="text-sm text-white/80">{next.reason || "General Consultation"}</p>
            </div>
          </div>
          <div className="sm:text-right">
            <p className="text-lg font-semibold">
              {relativeDay(new Date(next.start_time), now)} · {formatClockTime(new Date(next.start_time))}
            </p>
            <p className="text-sm text-white/80">
              {formatDate(new Date(next.start_time))} · {countdown(new Date(next.start_time), now)}
            </p>
          </div>
        </div>
      ) : (
        appointments !== null && (
          <div className="mb-6 rounded-2xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">
            No upcoming appointments. New bookings from the AI receptionist appear here automatically.
          </div>
        )
      )}

      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`rounded-full px-4 py-2 text-sm font-medium ${
                tab === key
                  ? "bg-brand-700 text-white shadow-sm"
                  : "border border-slate-200 bg-white text-slate-600 hover:border-brand-700 hover:text-brand-700"
              }`}
            >
              {label}
              <span className={`ml-2 text-xs ${tab === key ? "text-white/80" : "text-slate-400"}`}>{counts[key]}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex w-full items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 shadow-sm sm:w-72">
            <Search className="h-4 w-4 shrink-0 text-slate-400" />
            <input
              placeholder="Search by patient or reason…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-transparent text-sm text-slate-700 outline-none"
            />
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
            <ArrowDownUp className="h-4 w-4 text-slate-400" />
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortMode)}
              aria-label="Sort"
              className="bg-transparent text-sm text-slate-700 outline-none"
            >
              <option value="time">By appointment time</option>
              <option value="booked">Latest booked first</option>
            </select>
          </div>
        </div>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="w-12 px-5 py-3 text-center">#</th>
                <th className="px-4 py-3">Patient</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">Booked at</th>
                <th className="px-4 py-3">Call</th>
                <th className="px-5 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {appointments === null ? (
                <tr>
                  <td colSpan={COLUMNS} className="py-10 text-center text-slate-400">
                    <RefreshCw className="mr-2 inline-block h-5 w-5 animate-spin" />
                    Loading appointments…
                  </td>
                </tr>
              ) : visible.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNS} className="py-10 text-center italic text-slate-400">
                    {date ? `No appointments on ${date}.` : `No ${tab === "all" ? "" : `${tab} `}appointments.`}
                  </td>
                </tr>
              ) : (
                groups.map((group, gi) => (
                  <GroupRows key={group.heading ?? gi} heading={group.heading} count={group.items.length}>
                    {group.items.map((a) => (
                      <AppointmentRow
                        key={a.id}
                        appointment={a}
                        index={row++}
                        now={now}
                        onTranscript={setTranscriptFor}
                        onCancel={cancel}
                      />
                    ))}
                  </GroupRows>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-5 py-3 text-sm text-slate-500">
          <span>
            Showing <strong>{visible.length}</strong> of <strong>{list.length}</strong> appointments
          </span>
          <span className="text-xs text-slate-400">
            {date ? `Filtered by ${date}` : sort === "booked" ? "Latest bookings first" : "Grouped by day"}
          </span>
        </div>
      </Card>

      {transcriptFor && <CallTranscriptModal appointment={transcriptFor} onClose={() => setTranscriptFor(null)} />}
    </main>
  );
}

function AppointmentRow({
  appointment: a,
  index,
  now,
  onTranscript,
  onCancel,
}: {
  appointment: Appointment;
  index: number;
  now: Date;
  onTranscript: (a: Appointment) => void;
  onCancel: (a: Appointment) => void;
}) {
  const start = new Date(a.start_time);
  const created = new Date(a.created_at);
  const status = statusOf(a, now);
  const isNew = now.getTime() - created.getTime() < NEW_BOOKING_MS;
  const upcoming = !a.canceled && start >= now;

  return (
    <tr className={`group hover:bg-brand-50/60 ${a.canceled || start < now ? "opacity-60" : ""}`}>
      <td className="w-12 px-5 py-3.5 text-center font-medium text-slate-400">{index + 1}</td>
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700">
            <User className="h-4 w-4" />
          </span>
          <div>
            <p className="flex items-center gap-2 font-semibold text-slate-800">
              {a.patient_name}
              {isNew && (
                <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-amber-700">New</span>
              )}
            </p>
            <p className="text-xs text-slate-400">ID #{a.id}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3.5 text-slate-600">
        <p>{formatDate(start)}</p>
        <p className="text-xs text-slate-400">{relativeDay(start, now)}</p>
      </td>
      <td className="px-4 py-3.5 text-slate-600">
        <span className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-400" />
          <span className={a.canceled ? "line-through" : ""}>{formatClockTime(start)}</span>
        </span>
      </td>
      <td className="px-4 py-3.5 text-slate-600">
        <span className="flex items-center gap-2">
          <Stethoscope className="h-4 w-4 text-slate-400" />
          {a.reason || "General Consultation"}
        </span>
      </td>
      <td className="px-4 py-3.5 text-xs text-slate-500">
        {formatDate(created)}, {formatClockTime(created)}
      </td>
      <td className="px-4 py-3.5">
        {a.transcript ? (
          <button
            onClick={() => onTranscript(a)}
            className="flex items-center gap-1.5 rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-200"
          >
            <MessageSquareText className="h-3.5 w-3.5" />
            View
          </button>
        ) : (
          <span className="text-xs text-slate-300">No transcript</span>
        )}
      </td>
      <td className="px-5 py-3.5 text-right">
        <div className="flex items-center justify-end gap-2">
          {upcoming && (
            <button
              onClick={() => onCancel(a)}
              className="rounded-full border border-rose-200 px-2.5 py-1 text-xs font-semibold text-rose-600 opacity-0 hover:bg-rose-50 focus:opacity-100 group-hover:opacity-100"
            >
              Cancel
            </button>
          )}
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status.className}`}>{status.label}</span>
        </div>
      </td>
    </tr>
  );
}

function GroupRows({ heading, count, children }: { heading: string | null; count: number; children: React.ReactNode }) {
  return (
    <>
      {heading && (
        <tr className="bg-brand-50">
          <td colSpan={COLUMNS} className="px-5 py-2 text-xs font-semibold uppercase tracking-wide text-brand-700">
            {heading}
            <span className="ml-2 font-normal normal-case text-slate-400">
              {count} appointment{count === 1 ? "" : "s"}
            </span>
          </td>
        </tr>
      )}
      {children}
    </>
  );
}
