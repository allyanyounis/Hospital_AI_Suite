import type { Patient } from "../types";

export const VISIT_TYPES = ["New visit", "Follow-up", "Urgent / ED", "Telehealth", "Procedure review"];
const SEXES = ["Female", "Male", "Other", "Not stated"];

const input =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800 outline-none focus:border-brand-600";

export function PatientForm({ value, onChange, compact }: { value: Patient; onChange: (p: Patient) => void; compact?: boolean }) {
  const set = (k: keyof Patient) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...value, [k]: e.target.value });

  return (
    <div className={`grid gap-3 ${compact ? "grid-cols-2" : "sm:grid-cols-2 lg:grid-cols-3"}`}>
      <label className={`block text-xs font-semibold text-slate-600 ${compact ? "col-span-2" : ""}`}>
        Patient name <span className="text-rose-500">*</span>
        <input value={value.name} onChange={set("name")} placeholder="e.g. Jane Doe" maxLength={120} className={input} />
      </label>
      <label className="block text-xs font-semibold text-slate-600">
        MRN
        <input value={value.mrn} onChange={set("mrn")} placeholder="Medical record no." maxLength={60} className={input} />
      </label>
      <label className="block text-xs font-semibold text-slate-600">
        Date of birth
        <input type="date" value={value.dob} onChange={set("dob")} className={input} />
      </label>
      <label className="block text-xs font-semibold text-slate-600">
        Sex
        <select value={value.sex} onChange={set("sex")} className={input}>
          <option value="">—</option>
          {SEXES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label className="block text-xs font-semibold text-slate-600">
        Visit type
        <select value={value.visit_type} onChange={set("visit_type")} className={input}>
          <option value="">—</option>
          {VISIT_TYPES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
