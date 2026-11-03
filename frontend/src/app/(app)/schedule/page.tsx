"use client";

import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { Icons } from "@/components/icons";
import { Card, Notice, PageHeader, Spinner, StatCard, Toggle } from "@/components/ui";
import { api, type ClinicScheduleInput, type DaySchedule } from "@/lib/api";
import { toDateKey } from "@/lib/format";
import { useNow } from "@/lib/hooks";
import { DAY_NAMES, dayError, hoursLabel, slotCount, suggestBreak, toMinutes, weekdayIndex, workMinutes } from "@/lib/schedule";

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

export default function SchedulePage() {
  const now = useNow(60_000);
  const [saved, setSaved] = useState<ClinicScheduleInput | null>(null);
  const [draft, setDraft] = useState<ClinicScheduleInput | null>(null);
  const [isDefault, setIsDefault] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  function load(schedule: ClinicScheduleInput & { is_default: boolean }) {
    const { days, slot_minutes, holidays } = schedule;
    setSaved({ days, slot_minutes, holidays });
    setDraft(structuredClone({ days, slot_minutes, holidays }));
    setIsDefault(schedule.is_default);
  }

  useEffect(() => {
    api
      .schedule()
      .then(load)
      .catch((e) => setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not load the schedule" }));
  }, []);

  if (!draft || !saved) {
    return (
      <main className="flex justify-center p-16">
        {notice ? <Notice tone="error">{notice.text}</Notice> : <Spinner className="h-6 w-6" />}
      </main>
    );
  }

  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const hasErrors = draft.days.some((d) => dayError(d));
  const today = weekdayIndex(now);
  const todayHours = draft.days[today];

  const update = (patch: Partial<ClinicScheduleInput>) => {
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
      load(await api.saveSchedule(draft));
      setNotice({ ok: true, text: "Hours saved. The AI receptionist now books with this schedule." });
    } catch (e) {
      setNotice({ ok: false, text: `Couldn't save: ${e instanceof Error ? e.message : "please try again"}` });
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Calendar className="h-6 w-6" />}
        title="Clinic Schedulers
        "
        subtitle="Working hours, breaks and closed dates. The AI receptionist only books inside these hours, and the scribe uses them to spot after-hours sign-offs."
        aside={
          <div className="flex gap-2">
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
        }
      />

      {isDefault && !dirty && (
        <Notice tone="warning">You&apos;re seeing the clinic default. Adjust it to your real hours and save.</Notice>
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
          </div>

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
        </Card>

        <div className="space-y-5">
          <WeekAtAGlance days={draft.days} now={now} />
          <ClosedDates holidays={draft.holidays} onChange={(holidays) => update({ holidays })} />
        </div>
      </div>
    </main>
  );
}

function TimeInput({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) {
  return (
    <input
      type="time"
      value={value}
      aria-label={label}
      onChange={(e) => e.target.value && onChange(e.target.value)}
      className="w-[7.5rem] rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm tabular-nums text-slate-800 outline-none focus:border-brand-700"
    />
  );
}

function DayRow({
  index,
  day,
  isToday,
  onChange,
  onCopy,
}: {
  index: number;
  day: DaySchedule;
  isToday: boolean;
  onChange: (day: DaySchedule) => void;
  onCopy: () => void;
}) {
  const name = DAY_NAMES[index];
  const error = dayError(day);
  const suggestion = day.enabled ? suggestBreak(day) : null;
  const setBreak = (i: number, field: "start" | "end", value: string) =>
    onChange({ ...day, breaks: day.breaks.map((b, j) => (j === i ? { ...b, [field]: value } : b)) });

  return (
    <div className={`border-t border-slate-100 px-5 py-3 ${isToday ? "bg-amber-50/50" : ""}`}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Toggle checked={day.enabled} label={`${name} working`} onChange={(enabled) => onChange({ ...day, enabled })} />
        <span
          className={`flex w-32 items-center gap-2 text-sm font-semibold ${day.enabled ? "text-slate-800" : "text-slate-400"}`}
        >
          {name}
          {isToday && <span className="rounded bg-amber-400 px-1.5 py-0.5 text-[10px] font-bold text-brand-950">TODAY</span>}
        </span>
        {day.enabled ? (
          <>
            <span className="flex items-center gap-2">
              <TimeInput value={day.start} label={`${name} start`} onChange={(start) => onChange({ ...day, start })} />
              <span className="text-slate-400">–</span>
              <TimeInput value={day.end} label={`${name} finish`} onChange={(end) => onChange({ ...day, end })} />
            </span>
            <button
              disabled={!suggestion}
              onClick={() => suggestion && onChange({ ...day, breaks: [...day.breaks, suggestion] })}
              className="flex items-center gap-1 text-xs font-semibold text-brand-700 hover:underline disabled:text-slate-300 disabled:no-underline"
            >
              <Icons.Plus className="h-3.5 w-3.5" /> Add break
            </button>
            <span className="ml-auto flex items-center gap-3">
              <span className="w-12 text-right text-sm tabular-nums text-slate-600">
                {error ? "" : hoursLabel(workMinutes(day))}
              </span>
              <button
                onClick={onCopy}
                title="Copy these hours to all working days"
                aria-label={`Copy ${name} hours to all working days`}
                className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-brand-700"
              >
                <Icons.Copy />
              </button>
            </span>
          </>
        ) : (
          <span className="text-sm text-slate-400">Day off</span>
        )}
      </div>

      {day.enabled &&
        day.breaks.map((b, i) => (
          <div key={i} className="mt-2 flex flex-wrap items-center gap-2 sm:pl-[11.5rem]">
            <Icons.Coffee className="h-3.5 w-3.5 text-slate-500" />
            <TimeInput value={b.start} label={`${name} break ${i + 1} start`} onChange={(v) => setBreak(i, "start", v)} />
            <span className="text-slate-400">–</span>
            <TimeInput value={b.end} label={`${name} break ${i + 1} end`} onChange={(v) => setBreak(i, "end", v)} />
            <button
              aria-label="Remove break"
              onClick={() => onChange({ ...day, breaks: day.breaks.filter((_, j) => j !== i) })}
              className="rounded-md p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}

      {error && (
        <p className="mt-2 flex items-center gap-1 text-xs text-rose-600 sm:pl-[11.5rem]">
          <Icons.Alert className="h-3.5 w-3.5" /> {error}
        </p>
      )}
    </div>
  );
}

function WeekAtAGlance({ days, now }: { days: DaySchedule[]; now: Date }) {
  const valid = days.filter((d) => d.enabled && !dayError(d));
  const first = Math.min(6, ...valid.map((d) => Math.floor(toMinutes(d.start) / 60)));
  const last = Math.max(22, ...valid.map((d) => Math.ceil(toMinutes(d.end) / 60)));
  const span = (last - first) * 60;
  const pct = (minutes: number) => `${((minutes - first * 60) / span) * 100}%`;
  const width = (from: string, to: string) => `${((toMinutes(to) - toMinutes(from)) / span) * 100}%`;
  const ticks = Array.from({ length: Math.floor((last - first) / 2) + 1 }, (_, i) => first + i * 2);
  const nowMin = now.getHours() * 60 + now.getMinutes();
  const today = weekdayIndex(now);

  return (
    <Card className="p-5">
      <p className="text-sm font-semibold text-slate-900">Week at a glance</p>
      <p className="mb-4 text-xs text-slate-500">Working time in maroon, breaks hatched. The amber line is now.</p>
      <div className="overflow-x-auto">
        <div className="min-w-[420px]">
          <div className="relative mb-1 ml-10 mr-12 h-4">
            {ticks.map((h) => (
              <span
                key={h}
                className="absolute -translate-x-1/2 text-[10px] tabular-nums text-slate-400"
                style={{ left: pct(h * 60) }}
              >
                {String(h).padStart(2, "0")}:00
              </span>
            ))}
          </div>
          {days.map((day, i) => (
            <div key={DAY_NAMES[i]} className="flex h-9 items-center">
              <span className={`w-10 text-xs font-semibold ${i === today ? "text-amber-600" : "text-slate-500"}`}>
                {DAY_NAMES[i].slice(0, 3)}
              </span>
              <div className="relative h-6 flex-1 overflow-hidden rounded bg-slate-100">
                {day.enabled && !dayError(day) ? (
                  <>
                    <div
                      className="absolute inset-y-0 rounded-sm bg-brand-700"
                      style={{ left: pct(toMinutes(day.start)), width: width(day.start, day.end) }}
                    />
                    {day.breaks.map((b, j) => (
                      <div
                        key={j}
                        title={`Break ${b.start}–${b.end}`}
                        className="absolute inset-y-0 bg-brand-50"
                        style={{
                          left: pct(toMinutes(b.start)),
                          width: width(b.start, b.end),
                          backgroundImage: "repeating-linear-gradient(135deg, var(--color-brand-300) 0 2px, transparent 2px 6px)",
                        }}
                      />
                    ))}
                  </>
                ) : (
                  <span className="absolute inset-0 flex items-center justify-center text-[11px] text-slate-400">
                    {day.enabled ? "Fix hours" : "Day off"}
                  </span>
                )}
                {i === today && nowMin >= first * 60 && nowMin <= last * 60 && (
                  <span className="absolute -inset-y-0.5 w-0.5 bg-amber-400" style={{ left: pct(nowMin) }} />
                )}
              </div>
              <span className="w-12 text-right text-xs tabular-nums text-slate-600">
                {day.enabled ? hoursLabel(workMinutes(day)) : "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function ClosedDates({ holidays, onChange }: { holidays: string[]; onChange: (h: string[]) => void }) {
  const [newDate, setNewDate] = useState("");
  const todayKey = toDateKey(new Date());
  const add = () => {
    if (newDate && !holidays.includes(newDate)) onChange([...holidays, newDate].sort());
    setNewDate("");
  };

  return (
    <Card className="p-5">
      <p className="text-sm font-semibold text-slate-900">Closed dates</p>
      <p className="mb-3 text-xs text-slate-500">Holidays or leave. The AI receptionist won&apos;t book on these days.</p>
      <div className="mb-3 flex gap-2">
        <input
          type="date"
          value={newDate}
          min={todayKey}
          aria-label="Closed date"
          onChange={(e) => setNewDate(e.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-800 outline-none focus:border-brand-700"
        />
        <button
          onClick={add}
          disabled={!newDate}
          className="rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-40"
        >
          Add
        </button>
      </div>
      {holidays.length === 0 ? (
        <p className="text-xs text-slate-400">No closed dates.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {holidays.map((h) => (
            <span
              key={h}
              className={`flex items-center gap-1 rounded-full border py-1 pl-2.5 pr-1 text-xs font-medium ${
                h < todayKey ? "border-slate-200 bg-slate-50 text-slate-400" : "border-brand-200 bg-brand-50 text-brand-700"
              }`}
            >
              {new Date(`${h}T00:00:00`).toLocaleDateString(undefined, {
                weekday: "short",
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
              <button
                aria-label={`Remove ${h}`}
                onClick={() => onChange(holidays.filter((x) => x !== h))}
                className="rounded-full p-0.5 hover:bg-white"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </Card>
  );
}
