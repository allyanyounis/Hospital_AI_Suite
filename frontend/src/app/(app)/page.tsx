"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Icons } from "@/components/icons";
import { UpcomingChart } from "@/components/reception/UpcomingChart";
import { useSession } from "@/components/shell/SessionProvider";
import { Avatar, Card, Notice, Spinner, StatCard, StatusPill } from "@/components/ui";
import { api, type ClinicSchedule, type EncounterSummary, type Sample } from "@/lib/api";
import { isUpcoming, nextUp, todaysActive, topReasons } from "@/lib/appointments";
import { countdown, formatClockTime, formatDateTime, greeting, initials, isToday, relativeDay, toDateKey } from "@/lib/format";
import { useAppointments, useNow } from "@/lib/hooks";
import { weekdayIndex } from "@/lib/schedule";

export default function OverviewPage() {
  const { user } = useSession();
  const router = useRouter();
  const now = useNow(60_000);
  const { appointments } = useAppointments();
  const [encounters, setEncounters] = useState<EncounterSummary[] | null>(null);
  const [schedule, setSchedule] = useState<ClinicSchedule | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [busySample, setBusySample] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .encounters()
      .then(setEncounters)
      .catch(() => setEncounters([]));
    api
      .schedule()
      .then(setSchedule)
      .catch(() => {});
    api
      .samples()
      .then(setSamples)
      .catch(() => {});
  }, []);

  const bookings = appointments ?? [];
  const notes = encounters ?? [];
  const todayAppointments = todaysActive(bookings).sort((a, b) => a.start_time.localeCompare(b.start_time));
  const next = nextUp(bookings, now);
  const toReview = notes.filter((e) => e.status === "ready").length;
  const drafting = notes.filter((e) => e.status === "drafting").length;
  const signedToday = notes.filter((e) => e.approved_at && isToday(e.approved_at)).length;
  const todayHours = schedule?.days[weekdayIndex(now)];

  async function openSample(id: string) {
    setBusySample(id);
    setError(null);
    try {
      const e = await api.startFromSample(id);
      router.push(`/scribe/session?encounter=${e.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the sample");
      setBusySample(null);
    }
  }

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

      {/* Headline numbers from both modules */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard
          icon={<Icons.CalendarClock />}
          label="Appointments today"
          value={todayAppointments.length}
          note="Booked by the voice agent"
        />
        <StatCard
          icon={<Icons.Calendar />}
          label="Upcoming appointments"
          value={bookings.filter((a) => isUpcoming(a, now)).length}
        />
        <StatCard
          icon={<Icons.File />}
          label="Notes to review"
          value={toReview}
          note={drafting ? `${drafting} drafting now` : "Scribe pipeline"}
          accent={toReview > 0}
        />
        <StatCard icon={<Icons.CheckCircle />} label="Notes signed today" value={signedToday} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          {/* Bookings chart */}
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
                {topReasons(bookings).length === 0 ? (
                  <p className="text-sm italic text-slate-400">No active bookings yet.</p>
                ) : (
                  <ol className="space-y-3">
                    {topReasons(bookings).map((r, i) => (
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

          {/* Recent scribe encounters */}
          <Card>
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <p className="text-sm font-semibold text-slate-900">Recent encounters</p>
                <p className="text-xs text-slate-500">Your latest scribe sessions and where each note stands</p>
              </div>
              <Link href="/scribe/board" className="flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
                Open board <Icons.ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
            {encounters === null ? (
              <div className="flex justify-center py-10">
                <Spinner />
              </div>
            ) : notes.length === 0 ? (
              <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-700">
                  <Icons.Mic />
                </span>
                <p className="text-sm font-semibold text-slate-800">No encounters yet</p>
                <p className="text-sm text-slate-500">Start a live session, or open an example consultation.</p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {notes.slice(0, 5).map((e) => (
                  <li key={e.id}>
                    <Link
                      href={`/scribe/encounters?id=${e.id}`}
                      className="flex items-center gap-3 px-5 py-3 hover:bg-brand-50/40"
                    >
                      <Avatar text={initials(e.patient.name)} size="sm" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-slate-900">{e.patient.name || "Unnamed patient"}</p>
                        <p className="text-xs text-slate-500">{formatDateTime(e.created_at)}</p>
                      </div>
                      <StatusPill status={e.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Samples */}
          {samples.length > 0 && (
            <Card className="p-5">
              <div className="mb-3 flex items-start gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
                  <Icons.Book />
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Example consultations</p>
                  <p className="text-xs text-slate-500">Synthetic cardiology transcripts to try the scribe without recording.</p>
                </div>
              </div>
              <ul className="grid gap-1.5 sm:grid-cols-2">
                {samples.map((s) => (
                  <li key={s.id}>
                    <button
                      onClick={() => openSample(s.id)}
                      disabled={busySample !== null}
                      className="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2 text-left text-sm text-slate-700 hover:border-brand-200 hover:bg-brand-50/50 disabled:opacity-50"
                    >
                      <span className="truncate">{s.title}</span>
                      {busySample === s.id ? (
                        <Spinner className="h-3.5 w-3.5" />
                      ) : (
                        <Icons.ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        {/* Right rail */}
        <div className="space-y-5">
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

          <Card className="p-5">
            <p className="text-sm font-semibold text-slate-900">Today&apos;s appointments</p>
            <p className="mb-3 text-xs text-slate-500">In time order</p>
            {todayAppointments.length === 0 ? (
              <p className="py-4 text-center text-sm text-slate-400">Nothing booked for today.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {todayAppointments.slice(0, 8).map((a) => {
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

          <Card className="flex gap-3 border-amber-200 bg-amber-50/60 p-5">
            <Icons.Mic className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div>
              <p className="text-sm font-semibold text-slate-900">Tip: microphone position</p>
              <p className="text-xs leading-relaxed text-slate-600">
                Place the device between you and the patient. Clear speech from both sides gives the best speaker separation and
                more accurate medical terms.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </main>
  );
}
