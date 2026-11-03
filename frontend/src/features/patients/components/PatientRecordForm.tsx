"use client";

import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Notice, Spinner } from "@/shared/ui/ui";
import { patientsApi } from "../api";
import { EMPTY_PATIENT_INPUT, type PatientInput, type PatientRecord, SEXES, type Sex } from "../types";

const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";

/** Register a new patient, or edit an existing record (pass `current`). */
export function PatientRecordForm({
  current,
  onSaved,
  onCancel,
}: {
  current?: PatientRecord;
  onSaved: (patient: PatientRecord) => void;
  onCancel?: () => void;
}) {
  const [form, setForm] = useState<PatientInput>(
    current
      ? {
          full_name: current.full_name,
          mrn: current.mrn,
          sex: current.sex,
          date_of_birth: current.date_of_birth,
          phone: current.phone,
          email: current.email,
        }
      : EMPTY_PATIENT_INPUT,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (patch: Partial<PatientInput>) => setForm((f) => ({ ...f, ...patch }));
  const id = current ? `patient-${current.id}` : "patient-new";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const clean: PatientInput = {
      ...form,
      full_name: form.full_name.trim(),
      mrn: form.mrn.trim(),
      phone: form.phone.trim(),
      email: form.email.trim(),
    };
    try {
      const saved = current ? await patientsApi.update(current.id, clean) : await patientsApi.register(clean);
      if (!current) setForm(EMPTY_PATIENT_INPUT);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the patient");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {error && <Notice tone="error">{error}</Notice>}
      <label className={labelClass} htmlFor={`${id}-name`}>
        Full name
        <input
          id={`${id}-name`}
          value={form.full_name}
          onChange={(e) => set({ full_name: e.target.value })}
          maxLength={120}
          required
          className={field}
        />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className={labelClass} htmlFor={`${id}-mrn`}>
          Medical record number
          <input
            id={`${id}-mrn`}
            value={form.mrn}
            onChange={(e) => set({ mrn: e.target.value })}
            maxLength={60}
            className={field}
          />
        </label>
        <label className={labelClass} htmlFor={`${id}-dob`}>
          Date of birth
          <input
            id={`${id}-dob`}
            type="date"
            value={form.date_of_birth}
            onChange={(e) => set({ date_of_birth: e.target.value })}
            className={field}
          />
        </label>
        <label className={labelClass} htmlFor={`${id}-sex`}>
          Sex
          <select id={`${id}-sex`} value={form.sex} onChange={(e) => set({ sex: e.target.value as Sex })} className={field}>
            <option value="">—</option>
            {SEXES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className={labelClass} htmlFor={`${id}-phone`}>
          Phone
          <input
            id={`${id}-phone`}
            type="tel"
            value={form.phone}
            onChange={(e) => set({ phone: e.target.value })}
            maxLength={30}
            className={field}
          />
        </label>
      </div>
      <label className={labelClass} htmlFor={`${id}-email`}>
        Email
        <input
          id={`${id}-email`}
          type="email"
          value={form.email}
          onChange={(e) => set({ email: e.target.value })}
          maxLength={254}
          className={field}
        />
      </label>
      <div className="flex justify-end gap-2 pt-1">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
        )}
        <button
          disabled={busy || !form.full_name.trim()}
          className="flex items-center gap-2 rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
        >
          {busy ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : current ? <Icons.Check /> : <Icons.Plus />}
          {current ? "Save changes" : "Register patient"}
        </button>
      </div>
    </form>
  );
}
