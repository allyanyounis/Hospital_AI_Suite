"use client";

/** The receptionist's cards on the dashboard home page. */

import Link from "next/link";
import { Icons } from "@/components/icons";
import { UpcomingChart } from "@/components/reception/UpcomingChart";
import { Card, Spinner, StatCard } from "@/components/ui";
import type { Appointment, ClinicSchedule } from "@/lib/api";
import { isUpcoming, todaysActive, topReasons } from "@/lib/appointments";
import { formatClockTime } from "@/lib/format";

/** Today's active bookings in time order. */
export function todaysAppointments(appointments: Appointment[]): Appointment[] {
  return todaysActive(appointments).sort((a, b) => a.start_time.localeCompare(b.start_time));
}

export function ReceptionStats({ appointments, now }: { appointments: Appointment[]; now: Date }) {
  return (
    <>
      <StatCard
        icon={<Icons.CalendarClock />}
        label="Appointments today"
        value={todaysAppointments(appointments).length}
        note="Booked by the voice agent"
      />
      <StatCard
        icon={<Icons.Calendar />}
        label="Upcoming appointments"
        value={appointments.filter((a) => isUpcoming(a, now)).length}
      />
    </>
  );
}

export function BookingsCard({
  appointments,
  schedule,
}: {
  appointments: Appointment[] | null;
  schedule: ClinicSchedule | null;
}) {
  const bookings = appointments ?? [];
  const reasons = topReasons(bookings);
  return (
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">Appointments · next 10 days</p>
          <p className="text-xs text-slate-500">Active bookings per day; closed days and holidays in amber</p>
        </div>
        <Link
          href="/reception/appointments"
          className="flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline"
        >
          All appointments <Icons.ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
      <div className="grid gap-6 lg:grid-cols-[1fr_220px]">
        {appointments === null ? <Spinner /> : <UpcomingChart appointments={bookings} schedule={schedule} />}
        <div>
          <p className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Top visit reasons</p>
          {reasons.length === 0 ? (
            <p className="text-sm italic text-slate-400">No active bookings yet.</p>
          ) : (
            <ol className="space-y-3">
              {reasons.map((r, i) => (
                <li key={r.title} className="flex items-center gap-3 text-sm">
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] ${
                      i < 3 ? "bg-brand-700 text-white" : "bg-slate-100 text-brand-800"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span className="flex-1 truncate text-slate-700">{r.title}</span>
                  <span className="font-bold text-slate-900">{r.count}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </Card>
  );
}

export function TodaysAppointmentsCard({ appointments, now }: { appointments: Appointment[]; now: Date }) {
  const today = todaysAppointments(appointments);
  return (
    <Card className="p-5">
      <p className="text-sm font-semibold text-slate-900">Today&apos;s appointments</p>
      <p className="mb-3 text-xs text-slate-500">In time order</p>
      {today.length === 0 ? (
        <p className="py-4 text-center text-sm text-slate-400">Nothing booked for today.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {today.slice(0, 8).map((a) => {
            const start = new Date(a.start_time);
            const past = start < now;
            return (
              <li key={a.id} className={`flex items-center gap-3 py-2.5 ${past ? "opacity-50" : ""}`}>
                <span className="w-16 text-sm font-semibold tabular-nums text-brand-700">{formatClockTime(start)}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-slate-800">{a.patient_name}</span>
                  <span className="block truncate text-xs text-slate-500">{a.reason || "General Consultation"}</span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
