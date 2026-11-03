import type { Board, BoardCase, PhaseKey, Room } from "../../types";
import { hm } from "../../lib/time";

const PHASE_CLASS: Record<PhaseKey, string> = {
  induction: "bg-phase-anaes",
  lead_in: "bg-phase-prep",
  incision: "bg-phase-surgery",
  lead_out: "bg-phase-prep",
  emergence: "bg-phase-anaes",
};

/**
 * The day as lanes, one per theatre: each case is a block split into its phases. Dashed amber = a case the planner
 * suggests moving off today; dashed grey = where a waiting urgent case would go. Red line 16:00, maroon line now.
 */
export function Timeline({
  board,
  rooms,
  marked,
  onOpen,
}: {
  board: Board;
  rooms: Room[];
  marked: Set<number>;
  onOpen: (c: BoardCase) => void;
}) {
  const last = Math.max(board.close + 60, ...rooms.map((r) => r.finish + 30));
  const scale: [number, number] = [board.open, Math.min(24 * 60, Math.ceil(last / 60) * 60)];
  const x = (m: number) => `${((m - scale[0]) / (scale[1] - scale[0])) * 100}%`;
  const w = (a: number, b: number) => `${((b - a) / (scale[1] - scale[0])) * 100}%`;
  const hours: number[] = [];
  for (let m = scale[0]; m <= scale[1]; m += 60) hours.push(m);
  const isToday = board.day === board.today;
  const codeOf = new Map(board.rooms.map((r) => [r.id, r.code]));

  return (
    <div className="space-y-1.5 p-4">
      <Lane label="">
        <div className="relative h-4 text-[10px] text-slate-400">
          {hours.map((m) => (
            <span key={m} className="absolute -translate-x-1/2" style={{ left: x(m) }}>
              {hm(m).slice(0, 2)}
            </span>
          ))}
        </div>
      </Lane>
      <div className="relative space-y-1.5">
        {rooms.map((room) => (
          <Lane key={room.id} label={room.code} sub={room.specialty}>
            <div className="relative h-11 rounded-lg bg-slate-50">
              {room.cases.map((c) => (
                <button
                  key={c.id}
                  onClick={() => onOpen(c)}
                  title={`${c.name} · ${c.procedure} · ${hm(c.start)}–${hm(c.end)}`}
                  className={`absolute top-1 bottom-1 flex overflow-hidden rounded-md text-left ring-offset-1 hover:ring-2 hover:ring-brand-300 ${
                    c.state === "done" ? "opacity-45" : ""
                  } ${c.state === "in" ? "ring-2 ring-brand-600" : ""} ${
                    marked.has(c.id) ? "outline-2 outline-dashed outline-amber-500" : ""
                  }`}
                  style={{ left: x(c.start), width: w(c.start, c.end) }}
                >
                  {c.phases.map((p) => (
                    <i
                      key={p.key}
                      className={PHASE_CLASS[p.key]}
                      style={{ width: `${((p.end - p.start) / Math.max(1, c.end - c.start)) * 100}%` }}
                    />
                  ))}
                  <em className="absolute inset-0 truncate px-1.5 pt-1 text-[11px] font-semibold not-italic text-white drop-shadow">
                    {c.name.split(" ").pop()}
                  </em>
                </button>
              ))}
              {(board.proposals ?? [])
                .filter((p) => p.slot.room === room.id && p.slot.day === board.day)
                .map((p) => (
                  <div
                    key={`p${p.case}`}
                    title={`${p.name} · suggested ${hm(p.slot.start)} in ${codeOf.get(p.slot.room)}`}
                    className="absolute top-1 bottom-1 truncate rounded-md border-2 border-dashed border-slate-400 bg-white/70 px-1.5 pt-1 text-[11px] text-slate-600"
                    style={{ left: x(p.slot.start), width: w(p.slot.start, p.slot.start + p.planned_min) }}
                  >
                    {p.name.split(" ").pop()}
                  </div>
                ))}
            </div>
          </Lane>
        ))}
        <div className="pointer-events-none absolute inset-y-0 left-28 right-0">
          <div className="absolute inset-y-0 w-0.5 bg-close-line" style={{ left: x(board.close) }} />
          {isToday && board.now > scale[0] && board.now < scale[1] && (
            <div className="absolute inset-y-0 w-0.5 bg-brand-800" style={{ left: x(board.now) }} />
          )}
        </div>
      </div>
      <p className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-2 text-[11px] text-slate-500">
        <Key className="h-3 w-4 bg-phase-anaes" label="Anaesthesia" />
        <Key className="h-3 w-4 bg-phase-surgery" label="Surgery" />
        <Key className="h-3 w-4 bg-phase-prep" label="Prep and closing" />
        <Key className="h-3 w-0.5 bg-close-line" label="16:00" />
        {isToday && <Key className="h-3 w-0.5 bg-brand-800" label="Now" />}
        <Key className="h-3 w-4 border-2 border-dashed border-amber-500" label="Can move off today" />
        <Key className="h-3 w-4 border-2 border-dashed border-slate-400" label="Suggested place for an urgent case" />
      </p>
    </div>
  );
}

function Lane({ label, sub, children }: { label: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[7rem_minmax(0,1fr)] items-center">
      <div className="truncate pr-2">
        <p className="text-sm font-semibold text-slate-800">{label}</p>
        {sub && <p className="truncate text-[11px] text-slate-400">{sub}</p>}
      </div>
      {children}
    </div>
  );
}

function Key({ className, label }: { className: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <i className={`inline-block rounded-sm ${className}`} />
      {label}
    </span>
  );
}
