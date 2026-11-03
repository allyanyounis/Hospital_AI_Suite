"use client";

import { useEffect, useState } from "react";
import { useSession } from "@/features/auth";
import { type StaffMember, staffApi } from "@/features/staff";
import { useNow } from "@/shared/hooks";
import { Icons } from "@/shared/ui/icons";
import { Card, EmptyState, Notice, PageHeader, Spinner, StatCard } from "@/shared/ui/ui";
import { scheduleApi } from "../api";
import { ClosedDates } from "../components/ClosedDates";
import { DayRow } from "../components/DayRow";
import { WeekAtAGlance } from "../components/WeekAtAGlance";
import { DAY_NAMES, dayError, hoursLabel, slotCount, weekdayIndex, workMinutes } from "../rules";
import type { DaySchedule, DoctorScheduleInput } from "../types";

const SLOT_OPTIONS = [10, 15, 20, 30, 45, 60];

const weekdays = (enabled: number[], start: string, end: string, lunch: boolean): DaySchedule[] =>
  DAY_NAMES.map((_, i) => ({
    enabled: enabled.includes(i),
    start,
    end,
    breaks: lunch ? [{ start: "13:00", end: "14:00" }] : [],
  }));

const PRESETS = [
  { label: "9–5 with lunch", days: () => weekdays([0, 1, 2, 3, 4], "09:00", "17:00", true) },
  { label: "8–6 with lunch", days: () => weekdays([0, 1, 2, 3, 4], "08:00", "18:00", true) },
  { label: "Mornings, Mon–Sat", days: () => weekdays([0, 1, 2, 3, 4, 5], "08:00", "13:00", false) },
];

/** Each bookable doctor's OPD week, plus the hospital's closed dates. Read-only without schedule.edit. */
export function SchedulerView() {
  const canEdit = useSession().can("schedule.edit");
  const [doctors, setDoctors] = useState<StaffMember[] | null>(null);
  const [doctorId, setDoctorId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    staffApi
      .doctors()
      .then((list) => {
        setDoctors(list);
        setDoctorId((id) => id ?? list[0]?.id ?? null);
      })
      .catch((e) => {
        setDoctors([]);
        setError(e instanceof Error ? e.message : "Could not load doctors");
      });
  }, []);

  const doctor = doctors?.find((d) => d.id === doctorId) ?? null;

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Calendar className="h-6 w-6" />}
        title="OPD Schedules"
        subtitle="Each doctor's outpatient hours, breaks and slot length, and the hospital's closed dates. Appointments, the AI receptionist and the scribe's after-hours metric follow these."
        aside={
          doctors && doctors.length > 0 ? (
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-700" htmlFor="schedule-doctor">
              Doctor
              <select
                id="schedule-doctor"
                value={doctorId ?? ""}
                onChange={(e) => setDoctorId(Number(e.target.value))}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-800 outline-none focus:border-brand-700"
              >
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.display_name} · {d.department.name}
                  </option>
                ))}
              </select>
            </label>
          ) : undefined
        }
      />
      {error && <Notice tone="error">{error}</Notice>}
      {!canEdit && <Notice>Read-only: only an administrator can change OPD hours and closed dates.</Notice>}

      {doctors === null ? (
        <div className="flex justify-center p-16">
          <Spinner className="h-6 w-6" />
        </div>
      ) : !doctor ? (
        <Card>
          <EmptyState icon={<Icons.Calendar />} title="No bookable doctors yet">
            Mark a doctor as bookable in Hospital → Staff to give them an OPD schedule.
          </EmptyState>
        </Card>
      ) : (
        <DoctorWeek key={doctor.id} doctor={doctor} canEdit={canEdit} />
      )}
      <ClosedDates canEdit={canEdit} />
    </main>
  );
}

/** One doctor's week: hours, breaks and slot length, edited as a draft and saved together. */
function DoctorWeek({ doctor, canEdit }: { doctor: StaffMember; canEdit: boolean }) {
  const now = useNow(60_000);
  const [saved, setSaved] = useState<DoctorScheduleInput | null>(null);
  const [draft, setDraft] = useState<DoctorScheduleInput | null>(null);
  const [isDefault, setIsDefault] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  function load(schedule: DoctorScheduleInput & { is_default: boolean }) {
    const { days, slot_minutes } = schedule;
    setSaved({ days, slot_minutes });
    setDraft(structuredClone({ days, slot_minutes }));
    setIsDefault(schedule.is_default);
  }

  useEffect(() => {
    scheduleApi
      .doctorSchedule(doctor.id)
      .then(load)
      .catch((e) => setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not load the schedule" }));
  }, [doctor.id]);

  if (!draft || !saved) {
    return (
      <div className="flex justify-center p-16">
        {notice ? <Notice tone="error">{notice.text}</Notice> : <Spinner className="h-6 w-6" />}
      </div>
    );
  }

  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const hasErrors = draft.days.some((d) => dayError(d));
  const today = weekdayIndex(now);
  const todayHours = draft.days[today];

  const update = (patch: Partial<DoctorScheduleInput>) => {
    setDraft({ ...draft, ...patch });
    setNotice(null);
  };
  const setDay = (i: number, day: DaySchedule) => update({ days: draft.days.map((d, j) => (j === i ? day : d)) });
  const copyToWorkingDays = (i: number) => {
    const src = draft.days[i];
    update({
      days: draft.days.map((d) =>
        d.enabled ? { ...d, start: src.start, end: src.end, breaks: structuredClone(src.breaks) } : d,
      ),
    });
  };

  async function save() {
    if (!draft) return;
    setSaving(true);
    try {
      load(await scheduleApi.saveDoctorSchedule(doctor.id, draft));
      setNotice({ ok: true, text: `Saved ${doctor.display_name}'s hours. New bookings follow them.` });
    } catch (e) {
      setNotice({ ok: false, text: `Couldn't save: ${e instanceof Error ? e.message : "please try again"}` });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      {canEdit && (
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button
            onClick={() => {
              setDraft(structuredClone(saved));
              setNotice(null);
            }}
            disabled={!dirty || saving}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Discard
          </button>
          <button
            onClick={save}
            disabled={!dirty || hasErrors || saving}
            className="flex items-center gap-2 rounded-xl bg-brand-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:opacity-40"
          >
            {saving ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Check />}
            Save hours
          </button>
        </div>
      )}
      {isDefault && !dirty && (
        <Notice tone="warning">
          {doctor.display_name} has no saved hours yet, so the hospital default (Mon–Fri 09:00–17:00) applies.
        </Notice>
      )}
      {dirty && <Notice>{hasErrors ? "Fix the highlighted days before saving." : "You have unsaved changes."}</Notice>}
      {notice && <Notice tone={notice.ok ? "success" : "error"}>{notice.text}</Notice>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<Icons.Clock />}
          label="Hours per week"
          value={hoursLabel(draft.days.reduce((n, d) => n + workMinutes(d), 0))}
        />
        <StatCard icon={<Icons.Calendar />} label="Working days" value={`${draft.days.filter((d) => d.enabled).length} of 7`} />
        <StatCard
          icon={<Icons.Sun />}
          accent
          label={`Today · ${DAY_NAMES[today]}`}
          value={todayHours.enabled ? `${todayHours.start}–${todayHours.end}` : "Day off"}
        />
        <StatCard
          icon={<Icons.ListCheck />}
          label="Appointment slots per week"
          note={`${draft.slot_minutes}-minute slots`}
          value={draft.days.reduce((n, d) => n + slotCount(d, draft.slot_minutes), 0)}
        />
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
            <div>
              <p className="text-sm font-semibold text-slate-900">Weekly hours</p>
              <p className="text-xs text-slate-500">Toggle a day off, set start and finish, and add breaks.</p>
            </div>
            {canEdit && (
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="text-slate-500">Presets:</span>
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => update({ days: p.days() })}
                    className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 font-semibold text-slate-700 hover:border-brand-300 hover:bg-brand-50"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* A disabled fieldset makes every control inside read-only for users without schedule.edit */}
          <fieldset disabled={!canEdit} className="min-w-0">
            {draft.days.map((day, i) => (
              <DayRow
                key={DAY_NAMES[i]}
                index={i}
                day={day}
                isToday={i === today}
                onChange={(d) => setDay(i, d)}
                onCopy={() => copyToWorkingDays(i)}
              />
            ))}

            <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 px-5 py-4">
              <label htmlFor="slot-length" className="text-sm font-semibold text-slate-800">
                Appointment slot length
              </label>
              <select
                id="slot-length"
                value={draft.slot_minutes}
                onChange={(e) => update({ slot_minutes: Number(e.target.value) })}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-800 outline-none focus:border-brand-700"
              >
                {SLOT_OPTIONS.map((m) => (
                  <option key={m} value={m}>
                    {m} minutes
                  </option>
                ))}
              </select>
              <span className="text-xs text-slate-500">
                Patients can only book at these steps, counted from opening and after each break.
              </span>
            </div>
          </fieldset>
        </Card>

        <WeekAtAGlance days={draft.days} now={now} />
      </div>
    </div>
  );
}
