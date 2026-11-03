import { useState } from "react";
import type { Patient } from "../types";
import { PatientForm } from "./PatientForm";

export function PatientEditor({ initial, onSave }: { initial: Patient; onSave: (p: Patient) => Promise<void> }) {
  const [value, setValue] = useState(initial);
  const [saving, setSaving] = useState(false);
  return (
    <div className="mt-4 border-t border-slate-100 pt-4">
      <PatientForm value={value} onChange={setValue} />
      <button
        disabled={saving || !value.name.trim()}
        onClick={async () => {
          setSaving(true);
          await onSave(value).finally(() => setSaving(false));
        }}
        className="mt-3 rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save details"}
      </button>
    </div>
  );
}
