"use client";

import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Card, Spinner } from "@/shared/ui/ui";
import { DEPARTMENT_KINDS, type DepartmentKind, type NewDepartment } from "../types";

const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";

/** Add a department. `onCreate` resolves true when it was saved, so the form clears only then. */
export function NewDepartmentForm({ onCreate }: { onCreate: (department: NewDepartment) => Promise<boolean> }) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<DepartmentKind>("clinical");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    if (await onCreate({ code: code.trim().toUpperCase(), name: name.trim(), kind })) {
      setCode("");
      setName("");
    }
    setBusy(false);
  }

  return (
    <Card className="p-5">
      <p className="text-sm font-semibold text-slate-900">New department</p>
      <p className="mb-4 text-xs text-slate-500">The code is a short label shown on schedules and reports, e.g. CARD.</p>
      <form onSubmit={submit} className="space-y-3">
        <label className={labelClass} htmlFor="department-code">
          Code
          <input
            id="department-code"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            maxLength={16}
            placeholder="CARD"
            required
            className={`${field} font-mono`}
          />
        </label>
        <label className={labelClass} htmlFor="department-name">
          Name
          <input
            id="department-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
            placeholder="Cardiology"
            required
            className={field}
          />
        </label>
        <label className={labelClass} htmlFor="department-kind">
          Kind
          <select id="department-kind" value={kind} onChange={(e) => setKind(e.target.value as DepartmentKind)} className={field}>
            {DEPARTMENT_KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
        </label>
        <button
          disabled={busy || !code.trim() || !name.trim()}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-700 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:opacity-50"
        >
          {busy ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Plus />}
          Add department
        </button>
      </form>
    </Card>
  );
}
