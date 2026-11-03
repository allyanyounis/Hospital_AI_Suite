import type { PlanRow } from "../../insightsTypes";
import { hm } from "../../lib/time";

const OPEN = 8 * 60;
const CLOSE = 16 * 60;
const END = 19 * 60;
const pct = (m: number) => `${((m - OPEN) / (END - OPEN)) * 100}%`;

/** One simulated day as room lanes from 08:00 to 19:00, with the 16:00 close line; changed cases are highlighted. */
export function PlanLanes({
  rows,
  rooms,
  changed,
}: {
  rows: PlanRow[];
  rooms: { id: string; specialty: string }[];
  changed: Set<string>;
}) {
  const deferred = rows.filter((r) => r.status === "deferred");
  return (
    <div className="space-y-1.5">
      <div className="grid grid-cols-[6.5rem_1fr] gap-2 text-[10px] text-slate-400">
        <span />
        <div className="relative h-3">
          {[8, 10, 12, 14, 16, 18].map((h) => (
            <span key={h} className="absolute -translate-x-1/2 tabular-nums" style={{ left: pct(h * 60) }}>
              {String(h).padStart(2, "0")}:00
            </span>
          ))}
        </div>
      </div>
      {rooms.map((room) => (
        <div key={room.id} className="grid grid-cols-[6.5rem_1fr] items-center gap-2">
          <span className="min-w-0">
            <span className="block text-xs font-semibold text-slate-800">{room.id}</span>
            <span className="block truncate text-[10px] text-slate-400">{room.specialty}</span>
          </span>
          <div className="relative h-7 rounded-md bg-slate-50">
            <span className="absolute inset-y-0 w-px bg-rose-400" style={{ left: pct(CLOSE) }} title="16:00" />
            {rows
              .filter((r) => r.status === "scheduled" && r.room_id === room.id && r.start_min != null && r.end_min != null)
              .map((r) => {
                const start = r.start_min ?? OPEN;
                const end = r.end_min ?? start;
                const urgent = r.urgency === "Urgent" || r.urgency === "Immediate";
                const tone = changed.has(r.case_id)
                  ? "bg-brand-700 text-white"
                  : urgent
                    ? "bg-amber-400 text-brand-950"
                    : "bg-brand-100 text-brand-900";
                return (
                  <span
                    key={r.case_id}
                    title={`${r.case_id} · ${r.title} · ${r.urgency} · ${hm(start)}–${hm(end)}`}
                    className={`absolute inset-y-0.5 flex items-center overflow-hidden rounded px-1 text-[10px] font-semibold ${tone}`}
                    style={{ left: pct(start), width: `max(${((end - start) / (END - OPEN)) * 100}%, 6px)` }}
                  >
                    {r.case_id}
                  </span>
                );
              })}
          </div>
        </div>
      ))}
      {deferred.length > 0 && (
        <p className="pt-1 text-xs text-slate-500">
          <span className="font-semibold text-rose-700">Deferred:</span>{" "}
          {deferred.map((r) => `${r.case_id} ${r.title}`).join(" · ")}
        </p>
      )}
    </div>
  );
}

export function PlanLegend() {
  return (
    <div className="flex flex-wrap gap-4 text-xs text-slate-500">
      <span className="flex items-center gap-1.5">
        <i className="h-2.5 w-4 rounded-sm bg-brand-100" /> Unchanged
      </span>
      <span className="flex items-center gap-1.5">
        <i className="h-2.5 w-4 rounded-sm bg-brand-700" /> Changed by the replan
      </span>
      <span className="flex items-center gap-1.5">
        <i className="h-2.5 w-4 rounded-sm bg-amber-400" /> Urgent or Immediate
      </span>
      <span className="flex items-center gap-1.5">
        <i className="h-3 w-px bg-rose-400" /> 16:00
      </span>
    </div>
  );
}
