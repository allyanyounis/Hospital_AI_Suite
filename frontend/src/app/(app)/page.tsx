"use client";

/** Dashboard home: a greeting, then each module's cards (components/<module>/overview.tsx). */

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icons } from "@/components/icons";
import { BookingsCard, ReceptionStats, TodaysAppointmentsCard } from "@/components/reception/overview";
import {
  MicrophoneTipCard,
  RecentEncountersCard,
  SampleConsultationsCard,
  ScribeStats,
  useEncounters,
} from "@/components/scribe/overview";
import { useSession } from "@/components/shell/SessionProvider";
import { Notice } from "@/components/ui";
import { api, type Appointment, type ClinicSchedule } from "@/lib/api";
import { nextUp } from "@/lib/appointments";
import { countdown, formatClockTime, greeting, relativeDay, toDateKey } from "@/lib/format";
import { useAppointments, useNow } from "@/lib/hooks";
import { weekdayIndex } from "@/lib/schedule";

export default function OverviewPage() {
  const { user } = useSession();
  const now = useNow(60_000);
  const { appointments } = useAppointments();
  const encounters = useEncounters();
  const [schedule, setSchedule] = useState<ClinicSchedule | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .schedule()
      .then(setSchedule)
      .catch(() => {});
  }, []);

  const bookings = appointments ?? [];
  const todayHours = schedule?.days[weekdayIndex(now)];

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      {/* Greeting */}
      <div className="flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-amber-100 text-amber-600">
          <Icons.Sun className="h-5 w-5" />
        </span>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {greeting(now)}, {user.display_name}
          </h1>
          <p className="text-sm text-slate-500">
            {now.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}
            {todayHours && (
              <>
                {" · "}
                <Link href="/schedule" className="font-medium text-brand-700 hover:underline">
                  {schedule?.holidays.includes(toDateKey(now))
                    ? "Clinic closed today"
                    : todayHours.enabled
                      ? `Clinic open ${todayHours.start}–${todayHours.end}`
                      : "Clinic closed today"}
                </Link>
              </>
            )}
          </p>
        </div>
      </div>

      {error && <Notice tone="error">{error}</Notice>}

      {/* Headline numbers from every module */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <ReceptionStats appointments={bookings} now={now} />
        <ScribeStats encounters={encounters ?? []} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <BookingsCard appointments={appointments} schedule={schedule} />
          <RecentEncountersCard encounters={encounters} />
          <SampleConsultationsCard onError={setError} />
        </div>

        {/* Right rail */}
        <div className="space-y-5">
          <NextPatientCard next={nextUp(bookings, now)} now={now} />
          <TodaysAppointmentsCard appointments={bookings} now={now} />
          <MicrophoneTipCard />
        </div>
      </div>
    </main>
  );
}

/** The next booking, with quick links into both modules. */
function NextPatientCard({ next, now }: { next: Appointment | undefined; now: Date }) {
  return (
    <section className="rounded-2xl bg-gradient-to-br from-brand-800 to-brand-950 p-5 text-white shadow-md">
      <p className="text-xs font-semibold uppercase tracking-wider text-brand-200">Next patient</p>
      {next ? (
        <>
          <p className="mt-1 text-xl font-bold">{next.patient_name}</p>
          <p className="text-sm text-brand-100/80">{next.reason || "General Consultation"}</p>
          <p className="mt-3 text-sm font-semibold">
            {relativeDay(new Date(next.start_time), now)} · {formatClockTime(new Date(next.start_time))}{" "}
            <span className="font-normal text-brand-100/80">({countdown(new Date(next.start_time), now)})</span>
          </p>
        </>
      ) : (
        <p className="mt-1 text-sm text-brand-100/80">No upcoming appointments.</p>
      )}
      <div className="mt-5 grid grid-cols-2 gap-2">
        <Link
          href="/scribe/session"
          className="flex items-center justify-center gap-1.5 rounded-xl bg-amber-400 py-2.5 text-sm font-bold text-brand-950 hover:bg-amber-300"
        >
          <Icons.Mic /> Start scribe
        </Link>
        <Link
          href="/reception/agent"
          className="flex items-center justify-center gap-1.5 rounded-xl bg-white/10 py-2.5 text-sm font-semibold text-white hover:bg-white/20"
        >
          <Icons.Phone /> Voice agent
        </Link>
      </div>
    </section>
  );
}
