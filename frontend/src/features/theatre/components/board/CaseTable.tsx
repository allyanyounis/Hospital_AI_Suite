import type { BoardCase, Room } from "../../types";
import { hm, span } from "../../lib/time";
import { RiskPill, UrgencyBadge } from "../common";

function Status({ c }: { c: BoardCase }) {
  if (c.state === "in")
    return (
      <span className="font-semibold text-brand-700">
        In theatre
        <small className="block font-normal text-slate-500">
          {c.phase ?? "Turnover"} · {c.remain_min ?? 0} min left
        </small>
      </span>
    );
  if (c.state === "done") return <span className="text-slate-400">Done</span>;
  if (c.late_pct >= 50 || c.delay_min)
    return (
      <span>
        Waiting
        <small className={`block ${c.late_pct >= 50 ? "text-amber-700" : "text-slate-500"}`}>
          {c.delay_min ? `about ${c.delay_min} min after booked time` : "on time"}
          {c.late_pct ? ` · ${c.late_pct}% chance 30+ min late` : ""}
        </small>
      </span>
    );
  return <span className="text-slate-600">Waiting</span>;
}

/** The day's cases by theatre, in list order. A room has at most a dozen cases, so no virtualisation is needed. */
export function CaseTable({
  rooms,
  marked,
  onOpen,
}: {
  rooms: Room[];
  marked: Set<number>;
  onOpen: (c: BoardCase) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] text-left text-sm">
        <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-4 py-2.5">Start</th>
            <th className="px-3 py-2.5">Patient</th>
            <th className="px-3 py-2.5">Operation</th>
            <th className="px-3 py-2.5">Urgency</th>
            <th className="px-3 py-2.5">Surgeon</th>
            <th className="px-3 py-2.5">Status</th>
            <th className="px-4 py-2.5 text-right">Risk</th>
          </tr>
        </thead>
        {rooms.map((room) => (
          <tbody key={room.id} className="divide-y divide-slate-100">
            <tr className="bg-brand-50/50">
              <th colSpan={7} className="px-4 py-2 text-xs font-semibold text-brand-800">
                {room.code} · {room.specialty}
                <span className="ml-2 font-normal text-slate-500">
                  {room.cases.length} cases · ends {hm(room.finish)}
                  {room.forecast.expected_over > 0 && (
                    <b className="ml-1 text-amber-700">· {room.forecast.expected_over} min overtime expected</b>
                  )}
                </span>
              </th>
            </tr>
            {room.cases.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-3 text-slate-400">
                  No cases
                </td>
              </tr>
            )}
            {room.cases.map((c) => (
              <tr
                key={c.id}
                onClick={() => onOpen(c)}
                className={`cursor-pointer hover:bg-brand-50/40 ${c.state === "done" ? "text-slate-400" : ""} ${
                  marked.has(c.id) ? "bg-amber-50/60" : ""
                }`}
              >
                <td className="px-4 py-2.5 tabular-nums">
                  {hm(c.start)}
                  <small className={`block ${c.start > c.booked ? "text-amber-700" : "text-slate-400"}`}>
                    {c.start > c.booked ? `+${c.start - c.booked} min` : hm(c.end)}
                  </small>
                </td>
                <td className="px-3 py-2.5">
                  <b className="font-semibold text-slate-900">{c.name}</b>
                  <small className="block text-slate-500">
                    {c.age} {c.sex} · ASA {c.asa}
                    {c.allergies && c.allergies !== "None known" && <span className="text-rose-600"> · Allergy</span>}
                  </small>
                </td>
                <td className="px-3 py-2.5">
                  {c.procedure}
                  <small className="block text-slate-500">
                    {span(c.end - c.start)}
                    {c.overrun > 0 && ` · running ${c.overrun} min long`}
                  </small>
                </td>
                <td className="px-3 py-2.5">
                  <UrgencyBadge urgency={c.urgency} />
                </td>
                <td className="px-3 py-2.5">
                  {c.surgeon ?? "—"}
                  {c.rota && <small className="block text-amber-700">{c.rota}</small>}
                </td>
                <td className="px-3 py-2.5">
                  <Status c={c} />
                </td>
                <td className="px-4 py-2.5 text-right">
                  <RiskPill pct={c.risk} high={c.risk_high} model={c.risk_model} />
                </td>
              </tr>
            ))}
          </tbody>
        ))}
      </table>
    </div>
  );
}
