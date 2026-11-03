"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Modal } from "@/shared/ui/overlays";
import { Notice, Segmented, Spinner } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../api";
import { useDemoClock } from "../lib/demoClock";
import { placeLine } from "../lib/explain";
import { dayLabel, hm, span } from "../lib/time";
import type { IntakeInput, IntakeOutlook, IntakePreview, Urgency } from "../types";
import { URGENCIES, URGENCY_INFO } from "../types";

const field = "mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm";
const label = "block text-xs font-semibold text-slate-600";

/**
 * Emergency or urgent case: pick a waiting case or enter a new patient, see where it would go (nothing is saved),
 * then book it, applying only the suggested moves the user ticks.
 */
export function IntakeModal({ caseId, onClose }: { caseId: number | null; onClose: () => void }) {
  const qc = useQueryClient();
  const at = useDemoClock();
  const waiting = useQuery({ queryKey: theatreKeys.waiting(""), queryFn: () => theatreApi.waiting("", null) });
  const procedures = useQuery({ queryKey: theatreKeys.procedures(), queryFn: theatreApi.procedures });
  const rooms = useQuery({ queryKey: theatreKeys.theatres(), queryFn: theatreApi.theatres });
  const waitingCases = waiting.data?.items ?? [];

  const [picked, setPicked] = useState<number | "">(caseId ?? "");
  const pickedCase = waitingCases.find((c) => c.id === picked);
  const [urgency, setUrgency] = useState<Urgency>(pickedCase?.urgency ?? "immediate");
  const [patient, setPatient] = useState({ name: "", age: "", sex: "Female", allergies: "", asa: "3", code: "" });
  const [moves, setMoves] = useState<Set<number>>(new Set());

  const body = (): IntakeInput =>
    picked
      ? { case_id: picked, urgency }
      : {
          urgency,
          procedure_code: patient.code,
          asa: Number(patient.asa),
          patient: { name: patient.name, age: Number(patient.age), sex: patient.sex, allergies: patient.allergies },
        };

  const preview = useMutation({
    mutationFn: () => theatreApi.intakePreview(body(), at),
    onSuccess: (p) => setMoves(new Set(p.moves.map((m) => m.case))),
  });
  const confirm = useMutation({
    mutationFn: (p: IntakePreview) =>
      theatreApi.intakeConfirm(
        { ...body(), moves: p.moves.filter((m) => moves.has(m.case)).map((m) => ({ case: m.case, date: m.date, surgeon_id: m.surgeon_id })) },
        at,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: theatreKeys.all });
      onClose();
    },
  });

  const ready = picked ? true : patient.name.trim() && patient.age !== "" && patient.code;
  const p = preview.data;
  const code = (id: number) => rooms.data?.find((r) => r.id === id)?.code ?? `#${id}`;
  const reset = () => preview.reset();

  return (
    <Modal
      title="Emergency or urgent case"
      subtitle="Find the soonest safe place; nothing changes until you book."
      size="lg"
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            Close
          </button>
          {p ? (
            <button
              onClick={() => confirm.mutate(p)}
              disabled={confirm.isPending}
              className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
            >
              {confirm.isPending ? "Booking…" : `Book${moves.size ? ` and move ${moves.size}` : ""}`}
            </button>
          ) : (
            <button
              onClick={() => preview.mutate()}
              disabled={!ready || preview.isPending}
              className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
            >
              {preview.isPending ? "Working it out…" : "Find a place"}
            </button>
          )}
        </div>
      }
    >
      <div className="space-y-4">
        <label className={label}>
          Patient
          <select
            className={field}
            value={picked}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : "";
              setPicked(id);
              const c = waitingCases.find((w) => w.id === id);
              if (c) setUrgency(c.urgency);
              reset();
            }}
          >
            <option value="">New patient</option>
            {waitingCases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} · {c.procedure} ({URGENCY_INFO[c.urgency].label})
              </option>
            ))}
          </select>
        </label>

        {!picked && (
          <div className="grid gap-3 sm:grid-cols-6">
            <label className={`${label} sm:col-span-3`}>
              Name
              <input className={field} value={patient.name} onChange={(e) => (setPatient({ ...patient, name: e.target.value }), reset())} />
            </label>
            <label className={label}>
              Age
              <input
                className={field}
                type="number"
                min={0}
                max={120}
                value={patient.age}
                onChange={(e) => (setPatient({ ...patient, age: e.target.value }), reset())}
              />
            </label>
            <label className={label}>
              Sex
              <select className={field} value={patient.sex} onChange={(e) => setPatient({ ...patient, sex: e.target.value })}>
                <option>Female</option>
                <option>Male</option>
              </select>
            </label>
            <label className={label}>
              ASA
              <select className={field} value={patient.asa} onChange={(e) => (setPatient({ ...patient, asa: e.target.value }), reset())}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </label>
            <label className={`${label} sm:col-span-4`}>
              Operation
              <select className={field} value={patient.code} onChange={(e) => (setPatient({ ...patient, code: e.target.value }), reset())}>
                <option value="">Choose</option>
                {Object.entries(Object.groupBy(procedures.data ?? [], (x) => x.specialty)).map(([specialty, list]) => (
                  <optgroup key={specialty} label={specialty}>
                    {(list ?? []).map((x) => (
                      <option key={x.code} value={x.code}>
                        {x.title} · {span(x.minutes)}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <label className={`${label} sm:col-span-2`}>
              Allergies
              <input className={field} placeholder="None known" value={patient.allergies} onChange={(e) => setPatient({ ...patient, allergies: e.target.value })} />
            </label>
          </div>
        )}

        <div>
          <p className={label}>Urgency</p>
          <Segmented<Urgency>
            label="Urgency"
            className="mt-1"
            value={urgency}
            onChange={(u) => (setUrgency(u), reset())}
            options={URGENCIES.map((u) => ({ value: u, label: URGENCY_INFO[u].label, hint: URGENCY_INFO[u].target }))}
          />
        </div>

        {preview.isPending && (
          <div className="flex justify-center py-6">
            <Spinner className="h-5 w-5" />
          </div>
        )}
        {preview.isError && <Notice tone="error">{preview.error.message}</Notice>}
        {confirm.isError && <Notice tone="error">{confirm.error.message}</Notice>}
        {p && <PreviewResult p={p} code={code} moves={moves} setMoves={setMoves} />}
      </div>
    </Modal>
  );
}

function PreviewResult({
  p,
  code,
  moves,
  setMoves,
}: {
  p: IntakePreview;
  code: (id: number) => string;
  moves: Set<number>;
  setMoves: (s: Set<number>) => void;
}) {
  const s = p.slot;
  const today = s.wait !== undefined;
  const when = today ? `today ${hm(s.start)}` : `${dayLabel(s.day)}, ${hm(s.start)}`;
  const target = URGENCY_INFO[p.urgency].target;
  const cols: [string, IntakeOutlook][] = [
    ...(p.before ? [["Now", p.before] as [string, IntakeOutlook]] : []),
    ["With this case", p.after],
    ...(p.moves.length ? [["With the moves", p.with_moves] as [string, IntakeOutlook]] : []),
  ];
  const rows: [string, (o: IntakeOutlook) => string][] = [
    ["List ends", (o) => hm(o.finish)],
    ["Chance past 16:00", (o) => `${o.over_pct}%`],
    ["Expected overtime", (o) => `${o.expected_over} min`],
  ];

  return (
    <div className="space-y-3">
      <div className={`rounded-xl border px-4 py-3 ${s.met ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50"}`}>
        <p className="font-semibold text-slate-900">
          {code(s.room)} · {when}
        </p>
        <p className="text-sm text-slate-700">
          {today && `Starts in ${span(s.wait!)}. `}Target {target}: {s.met ? "met." : "not met. Call in a second team or use another theatre."}
        </p>
      </div>
      <table className="w-full text-sm">
        <thead className="text-[11px] uppercase tracking-wider text-slate-500">
          <tr>
            <th />
            {cols.map(([h]) => (
              <th key={h} className="px-2 py-1 text-right font-semibold">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map(([name, f]) => (
            <tr key={name}>
              <td className="py-1.5 text-slate-600">{name}</td>
              {cols.map(([h, o]) => (
                <td key={h} className="px-2 py-1.5 text-right tabular-nums text-slate-900">
                  {f(o)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {p.moves.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-semibold text-slate-900">Cases that make room (untick to keep them)</p>
          {p.moves.map((m) => (
            <label key={m.case} className="flex items-start gap-2 rounded-lg border border-slate-200 p-3 text-sm text-slate-700">
              <input
                type="checkbox"
                className="mt-1 accent-brand-700"
                checked={moves.has(m.case)}
                onChange={(e) => {
                  const next = new Set(moves);
                  if (e.target.checked) next.add(m.case);
                  else next.delete(m.case);
                  setMoves(next);
                }}
              />
              <span>
                {placeLine(m, code(m.room))} Taking them off today brings this room to {m.over_pct}% past 16:00.
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
