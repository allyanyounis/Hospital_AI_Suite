"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Notice, Spinner } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../../api";
import { DAY_CLOSE, DAY_OPEN, hm, WEEKDAYS } from "../../lib/time";
import type { RosterDay, Surgeon } from "../../types";

const timeField =
  "w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm tabular-nums text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20 disabled:bg-slate-50 disabled:text-slate-400";

/** Theatres run Monday to Friday; weekend entries are kept as they are. */
const THEATRE_DAYS = [0, 1, 2, 3, 4];

type Row = { on: boolean; start: string; end: string };

function minutesOf(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + (m || 0);
}

function rowsOf(surgeon: Surgeon): Row[] {
  return THEATRE_DAYS.map((wd) => {
    const d = surgeon.days.find((x) => x.weekday === wd);
    return { on: Boolean(d), start: hm(d?.start ?? DAY_OPEN), end: hm(d?.end ?? DAY_CLOSE) };
  });
}

/** A surgeon's theatre days: a checkbox and start/end time per weekday; read-only without theatre.roster. */
export function RosterEditor({ surgeon, canEdit }: { surgeon: Surgeon; canEdit: boolean }) {
  const qc = useQueryClient();
  const [rows, setRows] = useState<Row[]>(() => rowsOf(surgeon));
  const [problem, setProblem] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: (days: RosterDay[]) => theatreApi.saveRoster(surgeon.id, days),
    onSettled: () => qc.invalidateQueries({ queryKey: theatreKeys.all }),
  });

  const update = (i: number, patch: Partial<Row>) => {
    save.reset();
    setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  };

  function submit() {
    setProblem(null);
    const days: RosterDay[] = [];
    for (const [i, r] of rows.entries()) {
      if (!r.on) continue;
      const start = minutesOf(r.start);
      const end = minutesOf(r.end);
      if (end <= start) return setProblem(`${WEEKDAYS[THEATRE_DAYS[i]]}: the end must be after the start.`);
      days.push({ weekday: THEATRE_DAYS[i], start, end });
    }
    const weekend = surgeon.days.filter((d) => !THEATRE_DAYS.includes(d.weekday));
    save.mutate([...days, ...weekend]);
  }

  const error = problem ?? (save.isError ? save.error.message : null);

  return (
    <section className="space-y-3">
      <h4 className="text-sm font-semibold text-slate-900">Theatre days</h4>
      <div className="space-y-1.5">
        {rows.map((r, i) => (
          <div key={THEATRE_DAYS[i]} className="grid grid-cols-[5.5rem_1fr_1fr] items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={r.on}
                disabled={!canEdit}
                onChange={(e) => update(i, { on: e.target.checked })}
                className="h-4 w-4 accent-brand-700"
              />
              {WEEKDAYS[THEATRE_DAYS[i]]}
            </label>
            <input
              type="time"
              aria-label={`${WEEKDAYS[THEATRE_DAYS[i]]} start`}
              value={r.start}
              step={300}
              disabled={!canEdit || !r.on}
              onChange={(e) => update(i, { start: e.target.value })}
              className={timeField}
            />
            <input
              type="time"
              aria-label={`${WEEKDAYS[THEATRE_DAYS[i]]} end`}
              value={r.end}
              step={300}
              disabled={!canEdit || !r.on}
              onChange={(e) => update(i, { end: e.target.value })}
              className={timeField}
            />
          </div>
        ))}
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      {save.isSuccess && <Notice tone="success">Theatre days saved.</Notice>}
      {canEdit && (
        <button
          type="button"
          onClick={submit}
          disabled={save.isPending}
          className="flex items-center gap-2 rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
        >
          {save.isPending ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Check />}
          Save theatre days
        </button>
      )}
    </section>
  );
}
