"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { toDateKey } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Badge, Notice, Spinner } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../../api";
import { dayLabel, hm } from "../../lib/time";
import type { LeaveConflict, Surgeon } from "../../types";
import { useCaseAction } from "../common";

const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";

const period = (from: string, to: string) => (from === to ? dayLabel(from) : `${dayLabel(from)} – ${dayLabel(to)}`);

/** Current and future leave with delete, and a form to add leave that then lists the cases it affects. */
export function LeavePanel({ surgeon, canEdit, canManage }: { surgeon: Surgeon; canEdit: boolean; canManage: boolean }) {
  const qc = useQueryClient();
  const today = toDateKey(new Date());
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(today);
  const [reason, setReason] = useState("Annual leave");
  const [conflicts, setConflicts] = useState<LeaveConflict[] | null>(null);
  const invalidate = () => qc.invalidateQueries({ queryKey: theatreKeys.all });

  const add = useMutation({
    mutationFn: () => theatreApi.addLeave({ staff_id: surgeon.id, starts_on: from, ends_on: to, reason: reason.trim() || "Leave" }),
    onSuccess: (res) => setConflicts(res.conflicts),
    onSettled: invalidate,
  });
  const remove = useMutation({ mutationFn: theatreApi.deleteLeave, onSettled: invalidate });

  return (
    <section className="space-y-3">
      <h4 className="text-sm font-semibold text-slate-900">Leave</h4>
      {surgeon.leave.length === 0 ? (
        <p className="text-sm text-slate-400">No leave booked.</p>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-xl border border-slate-100">
          {surgeon.leave.map((l) => (
            <li key={l.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
              <span className="min-w-0">
                <span className="font-medium text-slate-800">{period(l.starts_on, l.ends_on)}</span>
                <span className="ml-2 text-xs text-slate-500">{l.reason}</span>
              </span>
              {canEdit && (
                <button
                  type="button"
                  title="Remove this leave"
                  aria-label="Remove this leave"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(l.id)}
                  className="rounded-lg p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-40"
                >
                  <Icons.Trash className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {remove.isError && <Notice tone="error">{remove.error.message}</Notice>}

      {canEdit && (
        <form
          className="space-y-2 rounded-xl bg-slate-50 p-3"
          onSubmit={(e) => {
            e.preventDefault();
            setConflicts(null);
            add.mutate();
          }}
        >
          <div className="grid grid-cols-2 gap-2">
            <label className={labelClass}>
              From
              <input
                type="date"
                required
                min={today}
                value={from}
                onChange={(e) => {
                  setFrom(e.target.value);
                  if (to < e.target.value) setTo(e.target.value);
                }}
                className={field}
              />
            </label>
            <label className={labelClass}>
              To
              <input type="date" required min={from} value={to} onChange={(e) => setTo(e.target.value)} className={field} />
            </label>
          </div>
          <label className={labelClass}>
            Reason
            <input value={reason} maxLength={120} onChange={(e) => setReason(e.target.value)} className={field} />
          </label>
          {add.isError && <Notice tone="error">{add.error.message}</Notice>}
          <button
            disabled={add.isPending}
            className="flex items-center gap-2 rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
          >
            {add.isPending ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Plus />}
            Add leave
          </button>
        </form>
      )}

      {conflicts && <ConflictList conflicts={conflicts} canManage={canManage} />}
    </section>
  );
}

/** The surgeon's cases inside the new leave, each with a colleague who can cover that day or the first later slot. */
function ConflictList({ conflicts, canManage }: { conflicts: LeaveConflict[]; canManage: boolean }) {
  const action = useCaseAction();
  const [done, setDone] = useState<Record<number, string>>({});

  if (conflicts.length === 0) return <Notice tone="success">Leave added. No booked case falls in that period.</Notice>;
  return (
    <div className="space-y-2">
      <Notice tone="warning">
        Leave added. {conflicts.length} booked case{conflicts.length === 1 ? "" : "s"} need{conflicts.length === 1 ? "s" : ""} another
        surgeon or another day.
      </Notice>
      {action.isError && <Notice tone="error">{action.error.message}</Notice>}
      <ul className="space-y-2">
        {conflicts.map((c) => (
          <li key={c.case} className="rounded-xl border border-slate-200 p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-semibold text-slate-900">{c.name}</p>
                <p className="truncate text-xs text-slate-500">
                  {c.procedure} · {dayLabel(c.day)}
                </p>
              </div>
              <Link href={`/theatre/cases/${c.case}`} className="shrink-0 text-xs font-semibold text-brand-700 hover:underline">
                Open case
              </Link>
            </div>
            {done[c.case] ? (
              <Badge tone="ok" className="mt-2">
                {done[c.case]}
              </Badge>
            ) : (
              <div className="mt-2 space-y-1.5 text-xs text-slate-600">
                {c.cover && (
                  <ConflictOption
                    text={`${c.cover.name} can cover that day.`}
                    button={canManage ? `Give to ${c.cover.name}` : null}
                    busy={action.isPending}
                    onClick={() => {
                      const cover = c.cover;
                      if (!cover) return;
                      action.mutate(
                        { id: c.case, action: "surgeon", input: { surgeon_id: cover.id } },
                        { onSuccess: () => setDone((d) => ({ ...d, [c.case]: `Given to ${cover.name}` })) },
                      );
                    }}
                  />
                )}
                {c.later && (
                  <ConflictOption
                    text={`First later slot: ${dayLabel(c.later.day)} at ${hm(c.later.start)}.`}
                    button={canManage ? `Move to ${dayLabel(c.later.day)}` : null}
                    busy={action.isPending}
                    onClick={() => {
                      const later = c.later;
                      if (!later) return;
                      action.mutate(
                        { id: c.case, action: "defer", input: { day: later.day, surgeon_id: later.surgeon_id ?? undefined } },
                        { onSuccess: () => setDone((d) => ({ ...d, [c.case]: `Moved to ${dayLabel(later.day)}` })) },
                      );
                    }}
                  />
                )}
                {!c.cover && !c.later && <p className="text-amber-700">No colleague free that day and no later slot found.</p>}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ConflictOption({
  text,
  button,
  busy,
  onClick,
}: {
  text: string;
  button: string | null;
  busy: boolean;
  onClick: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span>{text}</span>
      {button && (
        <button
          type="button"
          disabled={busy}
          onClick={onClick}
          className="shrink-0 rounded-lg border border-brand-200 bg-brand-50 px-2 py-1 font-semibold text-brand-800 hover:bg-brand-100 disabled:opacity-50"
        >
          {button}
        </button>
      )}
    </div>
  );
}
