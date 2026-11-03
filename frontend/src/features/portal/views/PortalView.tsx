"use client";

import { useEffect, useState } from "react";
import { useNow } from "@/shared/hooks";
import { countdown, formatClockTime, formatDate, initials, relativeDay } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Avatar, Card, EmptyState, Notice, PageHeader, Spinner } from "@/shared/ui/ui";
import { portalApi } from "../api";
import type { PortalAppointment, PortalProfile } from "../types";

/** A patient's own view: their details and their appointments. Read-only. */
export function PortalView() {
  const now = useNow(60_000);
  const [profile, setProfile] = useState<PortalProfile | null>(null);
  const [appointments, setAppointments] = useState<PortalAppointment[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fail = (e: unknown) => setError(e instanceof Error ? e.message : "Could not load your details");
    portalApi.me().then(setProfile).catch(fail);
    portalApi
      .appointments()
      .then(setAppointments)
      .catch((e) => {
        setAppointments([]);
        fail(e);
      });
  }, []);

  const sorted = [...(appointments ?? [])].sort((a, b) => a.start_time.localeCompare(b.start_time));
  const upcoming = sorted.filter((a) => !a.canceled && new Date(a.start_time) >= now);
  const past = sorted.filter((a) => a.canceled || new Date(a.start_time) < now).reverse();

  return (
    <main className="mx-auto max-w-4xl space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.CalendarClock className="h-6 w-6" />}
        title="My appointments"
        subtitle="Your details and visits at the hospital. To book, change or cancel, call the hospital; our voice assistant answers any time."
      />
      {error && <Notice tone="error">{error}</Notice>}

      <Card>
        {profile === null ? (
          <div className="flex justify-center py-8">{!error && <Spinner />}</div>
        ) : (
          <div className="flex flex-wrap items-center gap-4 p-5">
            <Avatar text={initials(profile.name)} />
            <div className="min-w-0 flex-1">
              <p className="text-lg font-semibold text-slate-900">{profile.name}</p>
              <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-sm">
                <Detail label="MRN" value={profile.mrn} />
                <Detail label="Date of birth" value={profile.dob && formatDate(new Date(`${profile.dob}T00:00:00`))} />
                <Detail label="Sex" value={profile.sex} />
              </dl>
            </div>
          </div>
        )}
      </Card>

      <section className="rounded-2xl bg-gradient-to-br from-brand-800 to-brand-950 p-5 text-white shadow-md">
        <p className="text-xs font-semibold uppercase tracking-wider text-brand-200">Next visit</p>
        {appointments === null ? (
          <Spinner className="mt-2 h-5 w-5 border-white/30 border-t-white" />
        ) : upcoming[0] ? (
          <>
            <p className="mt-1 text-xl font-bold">
              {relativeDay(new Date(upcoming[0].start_time), now)} · {formatClockTime(new Date(upcoming[0].start_time))}
            </p>
            <p className="text-sm text-brand-100/80">
              {upcoming[0].reason || "General Consultation"} · {countdown(new Date(upcoming[0].start_time), now)}
            </p>
            <p className="mt-1 text-sm font-semibold">
              {upcoming[0].doctor} · {upcoming[0].department}
            </p>
          </>
        ) : (
          <p className="mt-1 text-sm text-brand-100/80">No upcoming appointments.</p>
        )}
      </section>

      <AppointmentList title="Upcoming" items={upcoming} loading={appointments === null} empty="Nothing booked." />
      <AppointmentList title="Past and cancelled" items={past} loading={appointments === null} empty="No past visits yet." />
    </main>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-1.5">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value || "—"}</dd>
    </div>
  );
}

function AppointmentList({
  title,
  items,
  loading,
  empty,
}: {
  title: string;
  items: PortalAppointment[];
  loading: boolean;
  empty: string;
}) {
  return (
    <Card>
      <p className="border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-900">{title}</p>
      {loading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon={<Icons.Calendar />} title={empty} />
      ) : (
        <ul className="divide-y divide-slate-100">
          {items.map((a) => {
            const start = new Date(a.start_time);
            return (
              <li key={a.id} className={`flex items-center gap-4 px-5 py-3 ${a.canceled ? "opacity-60" : ""}`}>
                <span className="w-28 shrink-0 text-sm font-semibold text-brand-700">{formatDate(start)}</span>
                <span className={`w-20 shrink-0 text-sm tabular-nums text-slate-700 ${a.canceled ? "line-through" : ""}`}>
                  {formatClockTime(start)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-slate-700">{a.reason || "General Consultation"}</span>
                  <span className="block truncate text-xs text-slate-400">
                    {a.doctor} · {a.department}
                  </span>
                </span>
                {a.canceled && (
                  <span className="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-600">Cancelled</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
