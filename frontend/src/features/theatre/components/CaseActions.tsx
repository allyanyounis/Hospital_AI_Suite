"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Notice } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../api";
import { addDays, weekday } from "../lib/time";
import type { CaseDetail, Urgency } from "../types";
import { URGENCIES, URGENCY_INFO } from "../types";
import { useCaseAction } from "./common";

const btn =
  "rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50";
const primary =
  "rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50";
const input = "rounded-lg border border-slate-200 px-2 py-1.5 text-sm";

/** What can be done with a case, depending on where it is: on a list, in theatre now, or waiting. */
export function CaseActions({
  detail,
  onIntake,
  onCanceled,
}: {
  detail: CaseDetail;
  onIntake?: (caseId: number) => void;
  onCanceled?: () => void;
}) {
  const action = useCaseAction();
  const state = detail.timing?.state;
  const listed = detail.day != null;
  const started = state === "in" || state === "done";
  const [day, setDay] = useState(() => weekday(addDays(detail.today, 1)));
  const surgeons = useQuery({ queryKey: theatreKeys.surgeons(), queryFn: theatreApi.surgeons });
  const colleagues = (surgeons.data ?? []).filter((s) => s.specialty === detail.procedure.specialty && s.active);
  const run = (a: Parameters<typeof action.mutate>[0], then?: () => void) => action.mutate(a, { onSuccess: then });
  const id = detail.id;

  return (
    <div className="space-y-4">
      {action.isError && <Notice tone="error">{action.error.message}</Notice>}
      {action.isSuccess && <Notice tone="success">Done. The lists have been updated.</Notice>}

      {state === "in" && (
        <Group title="In theatre">
          {[15, 30, 60].map((m) => (
            <button key={m} className={btn} disabled={action.isPending} onClick={() => run({ id, action: "overrun", input: { minutes: m } })}>
              Running {m} min long
            </button>
          ))}
        </Group>
      )}

      {listed && !started && (
        <Group title="On the list">
          <button className={btn} disabled={action.isPending} onClick={() => run({ id, action: "earlier" })}>
            Earlier
          </button>
          <button className={btn} disabled={action.isPending} onClick={() => run({ id, action: "later" })}>
            Later
          </button>
          <button className={btn} disabled={action.isPending} onClick={() => run({ id, action: "unschedule" })}>
            Back to waiting list
          </button>
        </Group>
      )}

      {!started && (
        <Group title={listed ? "Move to another day" : "Put on a list"}>
          <input
            type="date"
            aria-label="Day"
            className={input}
            value={day}
            min={detail.today}
            onChange={(e) => setDay(e.target.value)}
          />
          <button
            className={primary}
            disabled={action.isPending || !day}
            onClick={() => run({ id, action: listed ? "defer" : "schedule", input: { day } })}
          >
            {listed ? "Move" : "Schedule"}
          </button>
          {!listed && onIntake && (
            <button className={btn} onClick={() => onIntake(id)}>
              Find a place by urgency
            </button>
          )}
        </Group>
      )}

      {!started && (
        <Group title="Urgency and surgeon">
          <select
            aria-label="Urgency"
            className={input}
            value={detail.urgency}
            disabled={action.isPending}
            onChange={(e) => run({ id, action: "urgency", input: { urgency: e.target.value as Urgency } })}
          >
            {URGENCIES.map((u) => (
              <option key={u} value={u}>
                {URGENCY_INFO[u].label}
              </option>
            ))}
          </select>
          <select
            aria-label="Surgeon"
            className={input}
            value={detail.surgeon_id ?? ""}
            disabled={action.isPending || !colleagues.length}
            onChange={(e) => e.target.value && run({ id, action: "surgeon", input: { surgeon_id: Number(e.target.value) } })}
          >
            <option value="">No surgeon</option>
            {colleagues.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <button
            className="rounded-lg px-3 py-1.5 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
            disabled={action.isPending}
            onClick={() => window.confirm("Cancel this operation?") && run({ id, action: "cancel" }, onCanceled)}
          >
            Cancel operation
          </button>
        </Group>
      )}
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">{title}</p>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}
