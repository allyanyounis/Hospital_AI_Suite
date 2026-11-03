"use client";

import { ArrowDownUp, BellRing, Calendar, RefreshCw, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useSession } from "@/features/auth";
import { type StaffMember, staffApi } from "@/features/staff";
import { useNow } from "@/shared/hooks";
import { countdown, dayOffset, formatClockTime, formatDate, relativeDay, toDateKey } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, PageHeader } from "@/shared/ui/ui";
import { appointmentsApi } from "../api";
import { AppointmentRow, COLUMNS, GroupRows } from "../components/AppointmentRows";
import { CallTranscriptModal } from "../components/CallTranscriptModal";
import { NewAppointmentForm } from "../components/NewAppointmentForm";
import { nextUp } from "../helpers";
import { useAppointments } from "../hooks";
import type { Appointment } from "../types";

type Tab = "upcoming" | "today" | "past" | "cancelled" | "all";
type SortMode = "time" | "booked";

const TABS: { key: Tab; label: string }[] = [
  { key: "upcoming", label: "Upcoming" },
  { key: "today", label: "Today" },
  { key: "past", label: "Past" },
  { key: "cancelled", label: "Cancelled" },
  { key: "all", label: "All" },
];

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

function dayHeading(date: Date, now: Date): string {
  const label = date.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
  const rel = relativeDay(date, now);
  return ["Today", "Tomorrow", "Yesterday"].includes(rel) ? `${rel} · ${label}` : label;
}

export function AppointmentsView() {
  const now = useNow(60_000); // keeps countdowns and Past/Upcoming current
  const { appointments, error, loading, lastUpdated, reload, live } = useAppointments();
  const { can } = useSession();
  const canCancel = can("appointments.manage");
  const canBook = can("appointments.book");
  const [doctors, setDoctors] = useState<StaffMember[]>([]);
  const [department, setDepartment] = useState("");
  const [doctorId, setDoctorId] = useState<number | "">("");
  const [booking, setBooking] = useState(false);
  const [date, setDate] = useState("");
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<Tab>("upcoming");
  const [sort, setSort] = useState<SortMode>("time");
  const [transcriptFor, setTranscriptFor] = useState<Appointment | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    staffApi
      .doctors()
      .then(setDoctors)
      .catch(() => {});
  }, []);

  const list = appointments ?? [];
  const departments = [...new Set(list.map((a) => a.practitioner.department))].sort();
  const query = search.trim().toLowerCase();
  // Search, date, department and doctor apply before tabs, so the tab counts reflect them
  const searched = list.filter(
    (a) =>
      [a.patient_name, a.reason ?? "", a.practitioner.display_name].some((v) => v.toLowerCase().includes(query)) &&
      (!date || toDateKey(new Date(a.start_time)) === date) &&
      (!department || a.practitioner.department === department) &&
      (doctorId === "" || a.practitioner.id === doctorId),
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
      await appointmentsApi.cancel(a.id);
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
            Every booking from the front desk, the AI voice receptionist and the patient portal.{" "}
            <span className={live ? "text-emerald-600" : "text-slate-400"}>{live ? "● Live" : "○ Reconnecting…"}</span>
            {lastUpdated && <span className="ml-2 text-xs text-slate-400">Updated {lastUpdated.toLocaleTimeString()}</span>}
          </>
        }
        aside={
          <div className="flex flex-wrap items-center gap-3">
            {canBook && (
              <button
                onClick={() => setBooking(true)}
                className="flex items-center gap-2 rounded-lg bg-amber-400 px-4 py-2 text-sm font-bold text-brand-950 hover:bg-amber-300"
              >
                <Icons.Plus /> New appointment
              </button>
            )}
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

      {booking && (
        <NewAppointmentForm
          doctors={doctors}
          onClose={() => setBooking(false)}
          onBooked={async (a) => {
            setBooking(false);
            await reload();
            setActionError(null);
            setTab("upcoming");
            setSearch(a.patient_name);
          }}
        />
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
            No upcoming appointments. New bookings appear here automatically.
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
              placeholder="Search patient, doctor or reason…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-transparent text-sm text-slate-700 outline-none"
            />
          </div>
          <select
            id="appointments-department"
            aria-label="Department"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm outline-none"
          >
            <option value="">All departments</option>
            {departments.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
          <select
            id="appointments-doctor"
            aria-label="Doctor"
            value={doctorId}
            onChange={(e) => setDoctorId(e.target.value ? Number(e.target.value) : "")}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm outline-none"
          >
            <option value="">All doctors</option>
            {doctors
              .filter((d) => !department || d.department.name === department)
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.display_name}
                </option>
              ))}
          </select>
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
          <table className="w-full min-w-[1080px] text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="w-12 px-5 py-3 text-center">#</th>
                <th className="px-4 py-3">Patient</th>
                <th className="px-4 py-3">Doctor</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">Booked at</th>
                <th className="px-4 py-3">Booked via</th>
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
                        onCancel={canCancel ? cancel : undefined}
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
