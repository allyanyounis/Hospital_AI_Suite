"use client";

import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { toDateKey } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, Spinner } from "@/shared/ui/ui";
import { scheduleApi } from "../api";
import type { Closure } from "../types";

const input =
  "min-w-0 rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-800 outline-none focus:border-brand-700 disabled:bg-slate-50";

/** Hospital-wide closed dates (holidays). Saved on their own; they apply to every doctor's OPD. */
export function ClosedDates({ canEdit }: { canEdit: boolean }) {
  const [saved, setSaved] = useState<Closure[] | null>(null);
  const [draft, setDraft] = useState<Closure[]>([]);
  const [newDate, setNewDate] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const todayKey = toDateKey(new Date());

  useEffect(() => {
    scheduleApi
      .closures()
      .then((list) => {
        setSaved(list);
        setDraft(list);
      })
      .catch((e) => setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not load closed dates" }));
  }, []);

  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const add = () => {
    if (newDate && !draft.some((c) => c.date === newDate)) {
      setDraft([...draft, { date: newDate, reason: reason.trim() }].sort((a, b) => a.date.localeCompare(b.date)));
    }
    setNewDate("");
    setReason("");
  };

  async function save() {
    setBusy(true);
    try {
      const list = await scheduleApi.saveClosures(draft);
      setSaved(list);
      setDraft(list);
      setNotice({ ok: true, text: "Closed dates saved." });
    } catch (e) {
      setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not save closed dates" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-5">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">Hospital closed dates</p>
          <p className="text-xs text-slate-500">Public holidays. No doctor can be booked on these days.</p>
        </div>
        {canEdit && dirty && (
          <button
            onClick={save}
            disabled={busy}
            className="flex items-center gap-1.5 rounded-lg bg-brand-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-800 disabled:opacity-40"
          >
            {busy ? <Spinner className="h-3.5 w-3.5 border-white/30 border-t-white" /> : <Icons.Check />}
            Save dates
          </button>
        )}
      </div>
      {notice && (
        <div className="mb-3">
          <Notice tone={notice.ok ? "success" : "error"}>{notice.text}</Notice>
        </div>
      )}
      {canEdit && (
        <div className="mb-3 flex flex-wrap gap-2">
          <input
            id="closure-date"
            type="date"
            value={newDate}
            min={todayKey}
            aria-label="Closed date"
            onChange={(e) => setNewDate(e.target.value)}
            className={input}
          />
          <input
            id="closure-reason"
            value={reason}
            aria-label="Reason"
            placeholder="Reason, e.g. Eid holiday"
            maxLength={120}
            onChange={(e) => setReason(e.target.value)}
            className={`${input} flex-1`}
          />
          <button
            onClick={add}
            disabled={!newDate}
            className="rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-40"
          >
            Add
          </button>
        </div>
      )}
      {saved === null && !notice ? (
        <Spinner />
      ) : draft.length === 0 ? (
        <p className="text-xs text-slate-400">No closed dates.</p>
      ) : (
        <ul className="space-y-1.5">
          {draft.map((c) => (
            <li
              key={c.date}
              className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs ${
                c.date < todayKey ? "border-slate-200 bg-slate-50 text-slate-400" : "border-brand-200 bg-brand-50 text-brand-700"
              }`}
            >
              <span className="font-semibold">
                {new Date(`${c.date}T00:00:00`).toLocaleDateString(undefined, {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
              <span className="min-w-0 flex-1 truncate text-slate-500">{c.reason}</span>
              {canEdit && (
                <button
                  aria-label={`Remove ${c.date}`}
                  onClick={() => setDraft(draft.filter((x) => x.date !== c.date))}
                  className="rounded-full p-0.5 hover:bg-white"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
