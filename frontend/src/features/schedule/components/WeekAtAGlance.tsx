import { Card } from "@/shared/ui/ui";
import { DAY_NAMES, dayError, hoursLabel, toMinutes, weekdayIndex, workMinutes } from "../rules";
import type { DaySchedule } from "../types";

export function WeekAtAGlance({ days, now }: { days: DaySchedule[]; now: Date }) {
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
