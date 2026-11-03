import { X } from "lucide-react";
import { Icons } from "@/shared/ui/icons";
import { Toggle } from "@/shared/ui/ui";
import { DAY_NAMES, dayError, hoursLabel, suggestBreak, workMinutes } from "../rules";
import type { DaySchedule } from "../types";

export function TimeInput({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) {
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

export function DayRow({
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
