"use client";

import { Icons } from "@/shared/ui/icons";
import { Card, EmptyState } from "@/shared/ui/ui";
import { placeLine } from "../../lib/explain";
import { dayLabel, hm, span } from "../../lib/time";
import type { Board, BoardCase, Room } from "../../types";
import { RiskPill, UrgencyBadge, useCaseAction } from "../common";

/**
 * What needs a decision today: who is in theatre now, rooms likely to run past 16:00 with the case to move, and
 * urgent cases waiting for a place. Each card has one main action; the reasoning is folded away.
 */
export function ActionNeeded({
  board,
  canManage,
  onOpen,
}: {
  board: Board;
  canManage: boolean;
  onOpen: (c: BoardCase) => void;
}) {
  const action = useCaseAction();
  const code = (id: number) => board.rooms.find((r) => r.id === id)?.code ?? `#${id}`;
  const active = board.rooms.flatMap((room) => room.cases.filter((c) => c.state === "in").map((c) => ({ c, room })));
  const tips = board.rooms.filter((r) => r.suggestion || r.nudge);
  const proposals = board.proposals ?? [];
  const busy = (id: number) => action.isPending && action.variables?.id === id;

  if (!active.length && !tips.length && !proposals.length)
    return (
      <EmptyState icon={<Icons.CheckCircle className="h-6 w-6" />} title="Nothing needs a decision">
        Every list is on time and no urgent case is waiting.
      </EmptyState>
    );

  return (
    <div className="space-y-6 p-4">
      {action.isError && <p className="text-sm text-rose-700">{action.error.message}</p>}

      {proposals.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-900">Urgent cases waiting for a place</h3>
          {proposals.map((p) => (
            <Card key={p.case} className={`p-4 ${p.slot.met ? "" : "border-rose-200 bg-rose-50/40"}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-2">
                    <UrgencyBadge urgency={p.urgency} />
                    <b className="text-slate-900">{p.name}</b>
                    <span className="text-xs text-slate-500">
                      {p.age} · ASA {p.asa}
                    </span>
                  </p>
                  <p className="text-sm text-slate-600">
                    {p.procedure} · {span(p.planned_min)}
                  </p>
                  <p className="mt-1 text-sm">
                    <b>
                      {code(p.slot.room)} ·{" "}
                      {p.slot.day === board.today ? `today at ${hm(p.slot.start)}` : `${dayLabel(p.slot.day)} at ${hm(p.slot.start)}`}
                    </b>{" "}
                    <span className={p.slot.met ? "text-emerald-700" : "text-rose-700"}>
                      · {p.slot.met ? "meets the target" : "misses the target"}
                    </span>
                  </p>
                </div>
                {canManage && (
                  <div className="flex shrink-0 gap-2">
                    <button
                      disabled={busy(p.case)}
                      onClick={() => action.mutate({ id: p.case, action: "book" })}
                      className="rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
                    >
                      Place here
                    </button>
                    {p.move && (
                      <button
                        disabled={busy(p.move.case)}
                        onClick={() =>
                          action.mutate({
                            id: p.move!.case,
                            action: "defer",
                            input: { day: p.move!.date, surgeon_id: p.move!.surgeon_id ?? undefined },
                          })
                        }
                        className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                      >
                        Move {p.move.name.split(" ").pop()} to {dayLabel(p.move.date)}
                      </button>
                    )}
                  </div>
                )}
              </div>
              <details className="mt-2 text-sm text-slate-600">
                <summary className="cursor-pointer text-xs font-semibold text-brand-700">Who is pushed back and why</summary>
                <p className="mt-1">
                  {p.pushed.length
                    ? p.pushed.map((x) => `${x.name} would move from ${hm(x.from)} to ${hm(x.to)}`).join(". ")
                    : "No case already on the list has to shift"}
                  . With {p.name.split(" ")[0]} on the list, the chance of passing 16:00 is {p.after_over}%.
                  {p.move &&
                    ` Taking ${p.move.name} off today brings it to ${p.move.over_pct}%. ${placeLine(p.move, code(p.move.room))}`}
                </p>
              </details>
            </Card>
          ))}
        </section>
      )}

      {tips.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-900">Lists likely to run late</h3>
          {tips.map((r) => (
            <Tip key={r.id} room={r} code={code} canManage={canManage} busy={busy} onMove={action.mutate} />
          ))}
        </section>
      )}

      {active.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-900">In theatre now</h3>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {active.map(({ c, room }) => (
              <button
                key={c.id}
                onClick={() => onOpen(c)}
                className={`card-hover rounded-2xl border bg-white p-4 text-left shadow-sm ${
                  c.risk_high ? "border-rose-200" : "border-slate-200/80"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-900">{c.name}</p>
                    <p className="text-xs text-slate-500">
                      {room.code} · {c.phase ?? "In theatre"}
                    </p>
                  </div>
                  <p className="text-right">
                    <b className="text-xl tabular-nums text-brand-800">{c.remain_min ?? 0}</b>
                    <small className="block text-[11px] text-slate-500">min left</small>
                  </p>
                </div>
                <p className="mt-2 text-xs text-slate-600">
                  {c.overrun ? `Running ${c.overrun} min long · ` : ""}
                  {c.overrun_pct ?? 0}% chance past {hm(c.end)}
                </p>
                <p className="mt-1 flex items-center gap-2 text-xs text-slate-600">
                  <RiskPill pct={c.risk} high={c.risk_high} model={c.risk_model} />
                  {c.risk_high ? "Higher than usual" : "Usual range"} ·{" "}
                  {c.risk_model === "EuroSCORE II" ? "death in hospital" : "ICU stay or death"}
                </p>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Tip({
  room,
  code,
  canManage,
  busy,
  onMove,
}: {
  room: Room;
  code: (id: number) => string;
  canManage: boolean;
  busy: (id: number) => boolean;
  onMove: ReturnType<typeof useCaseAction>["mutate"];
}) {
  const s = (room.suggestion ?? room.nudge)!;
  const firm = room.forecast.over_pct >= 50;
  return (
    <Card className={`p-4 ${firm ? "border-amber-200 bg-amber-50/50" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="min-w-0 text-sm text-slate-700">
          <b className="text-slate-900">
            {room.code} {firm ? "is more likely than not to run past 16:00" : "can run past 16:00"}
          </b>{" "}
          ({room.forecast.over_pct}%
          {room.forecast.expected_over ? `, about ${room.forecast.expected_over} min overtime` : ""}). Moving {s.name} off
          today takes that to {s.after.over_pct}%.
        </p>
        {canManage && (
          <button
            disabled={busy(s.case)}
            onClick={() => onMove({ id: s.case, action: "defer", input: { day: s.date, surgeon_id: s.surgeon_id ?? undefined } })}
            className="shrink-0 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm font-semibold text-amber-800 hover:bg-amber-50 disabled:opacity-50"
          >
            Move to {dayLabel(s.date)}
          </button>
        )}
      </div>
      <details className="mt-2 text-sm text-slate-600">
        <summary className="cursor-pointer text-xs font-semibold text-brand-700">Why this day</summary>
        <p className="mt-1">{placeLine(s, code(s.room))}</p>
      </details>
    </Card>
  );
}
