"use client";

import type { Cardiac } from "../../types";

const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";

type Flag = Exclude<keyof Cardiac, "lvef" | "nyha" | "pa_systolic">;

const FLAGS: { key: Flag; label: string }[] = [
  { key: "ccs4", label: "CCS class 4 angina" },
  { key: "recent_mi", label: "Heart attack within 90 days" },
  { key: "redo", label: "Previous heart surgery" },
  { key: "iddm", label: "Diabetes on insulin" },
  { key: "lung", label: "Chronic lung disease" },
  { key: "arteriopathy", label: "Extracardiac arteriopathy" },
  { key: "poor_mobility", label: "Poor mobility" },
  { key: "dialysis", label: "On dialysis" },
  { key: "endocarditis", label: "Active endocarditis" },
  { key: "critical", label: "Critical pre-operative state" },
];

const numberOrNull = (v: string) => (v === "" ? null : Number(v));

/** EuroSCORE II inputs, shown only for operations scored with EuroSCORE II. */
export function CardiacFields({ value, onChange }: { value: Cardiac; onChange: (value: Cardiac) => void }) {
  return (
    <fieldset className="space-y-3 rounded-xl border border-brand-100 bg-brand-50/40 p-3">
      <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-brand-800">EuroSCORE II</legend>
      <div className="grid grid-cols-3 gap-2">
        <label className={labelClass}>
          LVEF %
          <input
            type="number"
            min={5}
            max={90}
            value={value.lvef ?? ""}
            onChange={(e) => onChange({ ...value, lvef: numberOrNull(e.target.value) })}
            className={field}
          />
        </label>
        <label className={labelClass}>
          NYHA
          <select
            value={value.nyha ?? ""}
            onChange={(e) => onChange({ ...value, nyha: numberOrNull(e.target.value) })}
            className={field}
          >
            <option value="">—</option>
            {[1, 2, 3, 4].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className={labelClass} title="Pulmonary artery systolic pressure">
          PA sys. mmHg
          <input
            type="number"
            min={5}
            max={150}
            value={value.pa_systolic ?? ""}
            onChange={(e) => onChange({ ...value, pa_systolic: numberOrNull(e.target.value) })}
            className={field}
          />
        </label>
      </div>
      <div className="grid gap-x-3 gap-y-1.5 sm:grid-cols-2">
        {FLAGS.map((f) => (
          <label key={f.key} className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={Boolean(value[f.key])}
              onChange={(e) => onChange({ ...value, [f.key]: e.target.checked })}
              className="h-3.5 w-3.5 accent-brand-700"
            />
            {f.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
