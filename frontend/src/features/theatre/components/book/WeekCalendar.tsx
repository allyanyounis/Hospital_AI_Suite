"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Icons } from "@/shared/ui/icons";
import { Badge, Card, Notice, Spinner } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../../api";
import { addDays, dayLabel, hm, span } from "../../lib/time";
import type { CalendarCell, Procedure } from "../../types";

const navButton =
  "flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:border-brand-300 hover:text-brand-800 disabled:opacity-40";

/**
 * One week × every theatre: how full each list is, free minutes and who operates. With an operation chosen, the
 * theatres of its specialty show where it fits (start–end and surgeon) or why not; a fitting cell picks that day.
 */
export function WeekCalendar({
  start,
  onStart,
  procedure,
  surgeonId,
  selectedDay,
  onPickDay,
}: {
  start: string | null;
  onStart: (start: string | null) => void;
  procedure: Procedure | null;
  surgeonId: number | null;
  selectedDay: string | null;
  onPickDay: (day: string) => void;
}) {
  const code = procedure?.code ?? "";
  const cal = useQuery({
    queryKey: theatreKeys.calendar(start, code, surgeonId),
    queryFn: () => theatreApi.calendar(start, code, surgeonId),
    placeholderData: keepPreviousData,
  });
  const theatres = useQuery({ queryKey: theatreKeys.theatres(), queryFn: theatreApi.theatres });
  const specialtyOf = new Map((theatres.data ?? []).map((t) => [t.id, t.specialty]));
  const data = cal.data;
  const rooms = data?.days[0]?.rooms ?? [];

  return (
    <Card className="min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Icons.Calendar className="h-4 w-4 text-brand-700" />
            {data ? `Week of ${dayLabel(data.start, { month: "long", day: "numeric" })}` : "Theatre week"}
            {cal.isFetching && <Spinner className="h-3.5 w-3.5" />}
          </h2>
          <p className="text-xs text-slate-500">
            {procedure
              ? `${procedure.title} takes about ${span(procedure.minutes)}. Pick a highlighted slot.`
              : "Choose an operation to see where it fits."}
          </p>
        </div>
        {data && (
          <div className="flex gap-1.5">
            <button
              type="button"
              className={navButton}
              disabled={data.start <= data.today}
              onClick={() => onStart(addDays(data.start, -7) <= data.today ? null : addDays(data.start, -7))}
            >
              <Icons.ChevronLeft className="h-3.5 w-3.5" /> Previous
            </button>
            <button type="button" className={navButton} disabled={start === null} onClick={() => onStart(null)}>
              This week
            </button>
            <button type="button" className={navButton} onClick={() => onStart(addDays(data.start, 7))}>
              Next <Icons.ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>

      {cal.isError ? (
        <div className="p-5">
          <Notice tone="error">{cal.error.message}</Notice>
        </div>
      ) : !data ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6" />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[44rem] table-fixed border-collapse text-sm">
            <thead>
              <tr className="text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                <th className="w-28 px-4 py-2" />
                {rooms.map((r) => {
                  const target = procedure && specialtyOf.get(r.room) === procedure.specialty;
                  return (
                    <th key={r.room} className={`px-2 py-2 ${target ? "bg-brand-50 text-brand-800" : ""}`}>
                      {r.code}
                      <span className="block truncate text-[10px] font-medium normal-case tracking-normal text-slate-400">
                        {specialtyOf.get(r.room) ?? ""}
                      </span>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {data.days.map((d) => (
                <tr key={d.day} className={`border-t border-slate-100 align-top ${d.past ? "opacity-50" : ""}`}>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">
                    {dayLabel(d.day)}
                    {d.day === data.today && (
                      <Badge tone="brand" className="mt-1">
                        Today
                      </Badge>
                    )}
                  </th>
                  {d.rooms.map((cell) => (
                    <td key={cell.room} className="p-1.5">
                      <CalendarSlot
                        cell={cell}
                        selected={selectedDay === d.day && cell.fit != null && "start" in cell.fit}
                        onPick={() => onPickDay(d.day)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function CalendarSlot({ cell, selected, onPick }: { cell: CalendarCell; selected: boolean; onPick: () => void }) {
  const fit = cell.fit;
  const fits = fit != null && "start" in fit;
  const body = (
    <>
      <div className="flex items-center gap-2">
        <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
          <span
            className={`block h-full rounded-full ${cell.used_pct >= 90 ? "bg-amber-500" : "bg-brand-700"}`}
            style={{ width: `${cell.used_pct}%` }}
          />
        </span>
        <span className="text-[10px] tabular-nums text-slate-500">{cell.used_pct}%</span>
      </div>
      <p className="mt-1 text-[11px] text-slate-600">
        {cell.cases} case{cell.cases === 1 ? "" : "s"}
        {cell.staff.length > 0 && <> · {span(cell.free)} free</>}
      </p>
      {cell.staff.length === 0 ? (
        <p className="text-[11px] text-slate-400">No surgeon rostered</p>
      ) : (
        <ul className="mt-0.5 space-y-0.5">
          {cell.staff.map((s) => (
            <li key={s} title={s} className="truncate text-[11px] text-slate-500">
              {s}
            </li>
          ))}
        </ul>
      )}
      {fit &&
        (fits ? (
          <p
            className={`mt-1.5 rounded-md px-1.5 py-1 text-[11px] font-semibold tabular-nums ${
              selected ? "bg-brand-700 text-white" : "bg-emerald-50 text-emerald-800"
            }`}
          >
            {hm(fit.start)}–{hm(fit.end)}
            <span className="block truncate font-medium">{fit.surgeon}</span>
          </p>
        ) : (
          <p className="mt-1.5 text-[11px] leading-snug text-slate-400" title={fit.reason}>
            {fit.reason}
          </p>
        ))}
    </>
  );

  const frame = `block w-full rounded-lg border p-2 text-left ${
    selected ? "border-brand-700 ring-2 ring-brand-700/20" : fit ? "border-brand-100 bg-white" : "border-slate-100 bg-slate-50/50"
  }`;
  return fits ? (
    <button type="button" onClick={onPick} className={`${frame} hover:border-brand-300 hover:bg-brand-50/40`}>
      {body}
    </button>
  ) : (
    <div className={frame}>{body}</div>
  );
}
