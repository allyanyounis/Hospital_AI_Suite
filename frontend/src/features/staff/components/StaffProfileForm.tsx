"use client";

import { useEffect, useState } from "react";
import { type Department, departmentsApi } from "@/features/organization";
import { Icons } from "@/shared/ui/icons";
import { Notice, Spinner, Toggle } from "@/shared/ui/ui";
import { staffApi } from "../api";
import type { StaffMember, StaffProfileInput } from "../types";

const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";

/**
 * A staff member's hospital profile: department, title, specialty, registration number and whether patients can
 * book them. Used by the Staff directory (edit) and the Users page (right after creating a staff account).
 */
export function StaffProfileForm({
  username,
  current,
  suggestBookable = false,
  onSaved,
  onCancel,
}: {
  username: string;
  current?: StaffMember;
  /** Pre-tick "bookable" for a new doctor */
  suggestBookable?: boolean;
  onSaved: (member: StaffMember) => void;
  onCancel?: () => void;
}) {
  const [departments, setDepartments] = useState<Department[] | null>(null);
  const [form, setForm] = useState<StaffProfileInput>({
    department_id: current?.department.id ?? 0,
    job_title: current?.job_title ?? "",
    specialty: current?.specialty ?? "",
    registration_number: current?.registration_number ?? "",
    bookable: current?.bookable ?? suggestBookable,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (patch: Partial<StaffProfileInput>) => setForm((f) => ({ ...f, ...patch }));

  useEffect(() => {
    departmentsApi
      .list()
      .then((list) => {
        const active = list.filter((d) => d.active || d.id === current?.department.id);
        setDepartments(active);
        setForm((f) => (f.department_id ? f : { ...f, department_id: active[0]?.id ?? 0 }));
      })
      .catch((e) => {
        setDepartments([]);
        setError(e instanceof Error ? e.message : "Could not load departments");
      });
  }, [current?.department.id]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onSaved(
        await staffApi.saveProfile(username, {
          ...form,
          job_title: form.job_title.trim(),
          specialty: form.specialty.trim(),
          registration_number: form.registration_number.trim(),
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the profile");
    } finally {
      setBusy(false);
    }
  }

  if (departments === null) {
    return (
      <div className="flex justify-center py-6">
        <Spinner />
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {error && <Notice tone="error">{error}</Notice>}
      {departments.length === 0 ? (
        <Notice tone="warning">Add a department first (Hospital → Departments).</Notice>
      ) : (
        <label className={labelClass} htmlFor={`staff-dept-${username}`}>
          Department
          <select
            id={`staff-dept-${username}`}
            value={form.department_id}
            onChange={(e) => set({ department_id: Number(e.target.value) })}
            className={field}
          >
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.code})
              </option>
            ))}
          </select>
        </label>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <label className={labelClass} htmlFor={`staff-title-${username}`}>
          Job title
          <input
            id={`staff-title-${username}`}
            value={form.job_title}
            onChange={(e) => set({ job_title: e.target.value })}
            placeholder="e.g. Consultant, Staff Nurse"
            maxLength={120}
            className={field}
          />
        </label>
        <label className={labelClass} htmlFor={`staff-specialty-${username}`}>
          Specialty
          <input
            id={`staff-specialty-${username}`}
            value={form.specialty}
            onChange={(e) => set({ specialty: e.target.value })}
            placeholder="e.g. Cardiology"
            maxLength={120}
            className={field}
          />
        </label>
      </div>
      <label className={labelClass} htmlFor={`staff-reg-${username}`}>
        Registration number
        <input
          id={`staff-reg-${username}`}
          value={form.registration_number}
          onChange={(e) => set({ registration_number: e.target.value })}
          placeholder="Medical or nursing council number"
          maxLength={60}
          className={field}
        />
      </label>
      <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
        <span className="text-xs text-slate-600">
          <span className="block font-semibold text-slate-800">Bookable for OPD appointments</span>
          Has an outpatient schedule; the front desk and voice agent can book patients with them.
        </span>
        <Toggle checked={form.bookable} onChange={(bookable) => set({ bookable })} label="Bookable for appointments" />
      </div>
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
          disabled={busy || !form.department_id}
          className="flex items-center gap-2 rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
        >
          {busy ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Check />}
          Save profile
        </button>
      </div>
    </form>
  );
}
