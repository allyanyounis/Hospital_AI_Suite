import type { Room } from "../../types";
import { hm } from "../../lib/time";

/** One chip per theatre (what is happening now, when it ends, chance of passing 16:00); click to focus it. */
export function RoomChips({
  rooms,
  selected,
  onSelect,
}: {
  rooms: Room[];
  selected: number | null;
  onSelect: (id: number | null) => void;
}) {
  const chip = (on: boolean) =>
    `card-hover flex min-w-[9.5rem] shrink-0 flex-col gap-0.5 rounded-xl border px-3 py-2 text-left shadow-sm ${
      on ? "border-brand-300 bg-brand-50" : "border-slate-200 bg-white"
    }`;
  return (
    <div className="flex gap-2 overflow-x-auto pb-1" role="group" aria-label="Theatres">
      <button onClick={() => onSelect(null)} className={chip(selected == null)}>
        <b className="text-sm text-slate-900">All theatres</b>
        <small className="text-xs text-slate-500">{rooms.reduce((n, r) => n + r.cases.length, 0)} cases</small>
      </button>
      {rooms.map((r) => {
        const current = r.cases.find((c) => c.state === "in");
        const next = r.cases.find((c) => c.state === "wait");
        const over = r.forecast.over_pct;
        return (
          <button key={r.id} onClick={() => onSelect(r.id)} className={chip(selected === r.id)}>
            <span className="flex items-baseline justify-between gap-2">
              <b className="text-sm text-slate-900">{r.code}</b>
              <small className="truncate text-[11px] text-slate-400">{r.specialty}</small>
            </span>
            <small className="truncate text-xs text-slate-600">
              {current
                ? `${current.name.split(" ").pop()} · ${current.phase ?? "Turnover"}`
                : next
                  ? `Next ${hm(next.start)} · ${next.name.split(" ").pop()}`
                  : r.cases.length
                    ? "List finished"
                    : "No list"}
            </small>
            {r.cases.length > 0 && (
              <span className="flex items-center justify-between text-[11px] text-slate-500">
                Ends {hm(r.finish)}
                <i
                  className={`rounded-full px-1.5 not-italic font-semibold ${
                    over >= 50 ? "bg-rose-50 text-rose-700" : over >= 25 ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
                  }`}
                >
                  {over}% past 16:00
                </i>
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
