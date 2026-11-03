"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { type PatientRecord, PatientPicker, SEXES, type Sex } from "@/features/patients";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, Segmented, Spinner } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../../api";
import { dayLabel } from "../../lib/time";
import type { Cardiac, CaseInput, Procedure, Surgeon, Urgency } from "../../types";
import { URGENCIES, URGENCY_INFO } from "../../types";
import { CardiacFields } from "./CardiacFields";

const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";
const primary =
  "flex flex-1 items-center justify-center gap-2 rounded-xl bg-brand-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:opacity-50";
const secondary =
  "flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-300 hover:text-brand-800 disabled:opacity-50";

const EUROSCORE = "euroscore2";
const EMPTY_PATIENT = { name: "", age: "", sex: "" as Sex, allergies: "" };

/** Group operations by specialty for the select's optgroups. */
function bySpecialty(procedures: Procedure[]): [string, Procedure[]][] {
  const groups = new Map<string, Procedure[]>();
  for (const p of procedures) groups.set(p.specialty, [...(groups.get(p.specialty) ?? []), p]);
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

const numberOrNull = (v: string) => (v.trim() === "" ? null : Number(v));

/**
 * Book an operation: the patient (from the registry or a new provisional one), pre-op facts, urgency and surgeon.
 * The day comes from the calendar; without one the case joins the waiting list.
 */
export function BookForm({
  procedures,
  surgeons,
  procedureCode,
  onProcedure,
  surgeonId,
  onSurgeon,
  day,
  onDay,
}: {
  procedures: Procedure[];
  surgeons: Surgeon[];
  procedureCode: string;
  onProcedure: (code: string) => void;
  surgeonId: number | null;
  onSurgeon: (id: number | null) => void;
  day: string | null;
  onDay: (day: string | null) => void;
}) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [patient, setPatient] = useState<PatientRecord | null>(null);
  const [newPatient, setNewPatient] = useState(EMPTY_PATIENT);
  const [urgency, setUrgency] = useState<Urgency>("elective");
  const [asa, setAsa] = useState(2);
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [cardiac, setCardiac] = useState<Cardiac>({});
  const [problem, setProblem] = useState<string | null>(null);
  const [booked, setBooked] = useState<{ id: number; day: string | null } | null>(null);

  const procedure = procedures.find((p) => p.code === procedureCode) ?? null;
  const team = procedure ? surgeons.filter((s) => s.active && s.specialty === procedure.specialty) : [];
  const emergency = urgency === "immediate" || urgency === "urgent";

  const book = useMutation({
    mutationFn: (input: CaseInput) => theatreApi.book(input),
    onSuccess: (res, input) => {
      setBooked({ id: res.case, day: input.day ?? null });
      setPatient(null);
      setNewPatient(EMPTY_PATIENT);
      onDay(null);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: theatreKeys.all }),
  });

  function submit(withDay: boolean) {
    setProblem(null);
    setBooked(null);
    book.reset();
    if (!procedure) return setProblem("Choose an operation.");
    if (mode === "existing" && !patient) return setProblem("Pick the patient from the registry.");
    if (mode === "new" && (!newPatient.name.trim() || newPatient.age === "")) {
      return setProblem("Enter the new patient's name and age.");
    }
    if (withDay && !day) return setProblem("Pick a day in the calendar.");
    book.mutate({
      procedure_code: procedure.code,
      urgency,
      day: withDay ? day : null,
      surgeon_id: surgeonId,
      asa,
      weight_kg: numberOrNull(weight),
      height_cm: numberOrNull(height),
      cardiac: procedure.risk_model === EUROSCORE ? cardiac : null,
      ...(mode === "existing" && patient
        ? { patient_id: patient.id }
        : {
            patient: {
              name: newPatient.name.trim(),
              age: Number(newPatient.age),
              sex: newPatient.sex,
              allergies: newPatient.allergies.trim(),
            },
          }),
    });
  }

  const error = problem ?? (book.isError ? book.error.message : null);

  return (
    <Card className="space-y-4 p-5">
      {booked && (
        <Notice tone="success">
          {booked.day ? `Booked for ${dayLabel(booked.day)}.` : "Added to the waiting list."}{" "}
          <Link href={`/theatre/cases/${booked.id}`} className="font-semibold underline">
            Open the case
          </Link>
        </Notice>
      )}
      {error && <Notice tone="error">{error}</Notice>}

      <label className={labelClass}>
        Operation
        <select
          value={procedureCode}
          onChange={(e) => {
            onProcedure(e.target.value);
            setCardiac({});
          }}
          className={field}
        >
          <option value="">Choose an operation</option>
          {bySpecialty(procedures).map(([specialty, list]) => (
            <optgroup key={specialty} label={specialty}>
              {list.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.title}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>

      <div>
        <div className="flex items-center justify-between gap-2">
          <span className={labelClass}>Patient</span>
          <Segmented
            label="Patient"
            value={mode}
            onChange={setMode}
            options={[
              { value: "existing", label: "From registry" },
              { value: "new", label: "New patient" },
            ]}
          />
        </div>
        {mode === "existing" ? (
          <PatientPicker id="theatre-book-patient" value={patient} onChange={setPatient} />
        ) : (
          <div className="mt-2 grid grid-cols-6 gap-2">
            <label className={`${labelClass} col-span-6`}>
              Name
              <input
                value={newPatient.name}
                maxLength={120}
                onChange={(e) => setNewPatient({ ...newPatient, name: e.target.value })}
                className={field}
              />
            </label>
            <label className={`${labelClass} col-span-2`}>
              Age
              <input
                type="number"
                min={0}
                max={120}
                value={newPatient.age}
                onChange={(e) => setNewPatient({ ...newPatient, age: e.target.value })}
                className={field}
              />
            </label>
            <label className={`${labelClass} col-span-4`}>
              Sex
              <select
                value={newPatient.sex}
                onChange={(e) => setNewPatient({ ...newPatient, sex: e.target.value as Sex })}
                className={field}
              >
                <option value="">Not recorded</option>
                {SEXES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className={`${labelClass} col-span-6`}>
              Allergies
              <input
                value={newPatient.allergies}
                maxLength={240}
                placeholder="None known"
                onChange={(e) => setNewPatient({ ...newPatient, allergies: e.target.value })}
                className={field}
              />
            </label>
          </div>
        )}
      </div>

      <div>
        <span className={labelClass}>Urgency</span>
        <Segmented
          className="mt-1 w-full [&>button]:flex-1"
          label="Urgency"
          value={urgency}
          onChange={setUrgency}
          options={URGENCIES.map((u) => ({ value: u, label: URGENCY_INFO[u].label, hint: URGENCY_INFO[u].target }))}
        />
      </div>

      <div className="grid grid-cols-3 gap-2">
        <label className={labelClass}>
          ASA
          <select value={asa} onChange={(e) => setAsa(Number(e.target.value))} className={field}>
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className={labelClass}>
          Weight kg
          <input type="number" min={1} max={399} value={weight} onChange={(e) => setWeight(e.target.value)} className={field} />
        </label>
        <label className={labelClass}>
          Height cm
          <input type="number" min={31} max={259} value={height} onChange={(e) => setHeight(e.target.value)} className={field} />
        </label>
      </div>

      {procedure?.risk_model === EUROSCORE && <CardiacFields value={cardiac} onChange={setCardiac} />}

      <label className={labelClass}>
        Surgeon
        <select
          value={surgeonId ?? ""}
          disabled={!procedure}
          onChange={(e) => onSurgeon(e.target.value ? Number(e.target.value) : null)}
          className={field}
        >
          <option value="">Any available {procedure ? procedure.specialty.toLowerCase() : ""} surgeon</option>
          {team.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>

      {emergency ? (
        <Notice tone="warning">
          {URGENCY_INFO[urgency].label} cases are placed by the emergency intake on the{" "}
          <Link href="/theatre" className="font-semibold underline">
            theatre board
          </Link>
          , which finds the earliest safe slot. You can add the case to the waiting list here and place it from there.
        </Notice>
      ) : (
        <div className="flex items-center justify-between gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm">
          <span className="text-slate-600">
            Day:{" "}
            <span className="font-semibold text-slate-900">{day ? dayLabel(day) : "pick a slot in the calendar"}</span>
          </span>
          {day && (
            <button type="button" onClick={() => onDay(null)} className="text-xs font-semibold text-brand-700 hover:underline">
              Clear
            </button>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {!emergency && (
          <button type="button" disabled={book.isPending || !day} onClick={() => submit(true)} className={primary}>
            {book.isPending ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Check />}
            {day ? `Book ${dayLabel(day)}` : "Book on a day"}
          </button>
        )}
        <button
          type="button"
          disabled={book.isPending}
          onClick={() => submit(false)}
          className={emergency ? primary : secondary}
        >
          <Icons.Clipboard /> Add to waiting list
        </button>
      </div>
    </Card>
  );
}
