"use client";

import { useState } from "react";
import { ROLE_LABELS, type Role, STAFF_ROLES } from "@/features/auth";
import { SEXES, type Sex } from "@/features/patients";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, Spinner } from "@/shared/ui/ui";
import { usersApi } from "../api";
import type { UserAccount } from "../types";

export const MIN_PASSWORD_LENGTH = 10;
const ROLES: Role[] = [...STAFF_ROLES, "patient"];

export const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";

const EMPTY = { username: "", display_name: "", role: "doctor" as Role, password: "", mrn: "", dob: "", sex: "" as Sex };

/**
 * New staff or patient account. Patient accounts also create (or link, by MRN) the patient record; staff accounts
 * get their hospital profile (department etc.) in the next step.
 */
export function CreateAccountForm({ onCreated }: { onCreated: (account: UserAccount) => void }) {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (patch: Partial<typeof EMPTY>) => setForm({ ...form, ...patch });
  const isPatient = form.role === "patient";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await usersApi.create({
        username: form.username.trim(),
        display_name: form.display_name.trim(),
        role: form.role,
        password: form.password,
        ...(isPatient ? { patient: { mrn: form.mrn.trim(), dob: form.dob, sex: form.sex } } : {}),
      });
      setForm(EMPTY);
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the account");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-5">
      <p className="text-sm font-semibold text-slate-900">New account</p>
      <p className="mb-4 text-xs text-slate-500">
        There is no open sign-up. Share the first password with the person securely; they can change it under Account.
      </p>
      {error && (
        <div className="mb-4">
          <Notice tone="error">{error}</Notice>
        </div>
      )}
      <form onSubmit={submit} className="space-y-3">
        <label className={labelClass}>
          Role
          <select value={form.role} onChange={(e) => set({ role: e.target.value as Role })} className={field}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </label>
        <label className={labelClass}>
          {isPatient ? "Patient's full name" : "Display name"}
          <input
            value={form.display_name}
            onChange={(e) => set({ display_name: e.target.value })}
            placeholder={isPatient ? "e.g. Sara Ahmed" : "e.g. Dr. Rahman"}
            maxLength={120}
            required
            className={field}
          />
        </label>
        <label className={labelClass}>
          Username
          <input
            value={form.username}
            onChange={(e) => set({ username: e.target.value })}
            autoComplete="off"
            maxLength={64}
            required
            className={field}
          />
        </label>
        <label className={labelClass}>
          First password
          <input
            type="password"
            value={form.password}
            onChange={(e) => set({ password: e.target.value })}
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            required
            className={field}
          />
          <span className="mt-1 block font-normal text-slate-400">At least {MIN_PASSWORD_LENGTH} characters.</span>
        </label>

        {isPatient && (
          <div className="space-y-3 rounded-xl border border-brand-100 bg-brand-50/40 p-3">
            <p className="text-xs text-slate-600">
              Links to the patient record with this MRN, or creates one. The patient will only see their own details and
              appointments.
            </p>
            <label className={labelClass}>
              Medical record number
              <input value={form.mrn} onChange={(e) => set({ mrn: e.target.value })} maxLength={60} className={field} />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className={labelClass}>
                Date of birth
                <input type="date" value={form.dob} onChange={(e) => set({ dob: e.target.value })} className={field} />
              </label>
              <label className={labelClass}>
                Sex
                <select value={form.sex} onChange={(e) => set({ sex: e.target.value as Sex })} className={field}>
                  <option value="">—</option>
                  {SEXES.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        )}

        <button
          disabled={busy || !form.username.trim() || !form.display_name.trim() || form.password.length < MIN_PASSWORD_LENGTH}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-700 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:opacity-50"
        >
          {busy ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Plus />}
          Create account
        </button>
      </form>
    </Card>
  );
}
