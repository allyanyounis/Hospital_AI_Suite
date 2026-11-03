"use client";

import { useEffect, useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Spinner } from "@/shared/ui/ui";
import { patientsApi } from "../api";
import type { PatientRecord } from "../types";

/** Search the registry and pick one patient (used when booking an appointment). */
export function PatientPicker({
  id,
  value,
  onChange,
}: {
  id: string;
  value: PatientRecord | null;
  onChange: (patient: PatientRecord | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PatientRecord[] | null>(null);

  useEffect(() => {
    if (value) return;
    const timer = setTimeout(() => {
      patientsApi
        .search(query)
        .then(setResults)
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query, value]);

  if (value) {
    return (
      <div className="mt-1 flex items-center justify-between gap-2 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-sm">
        <span className="min-w-0 truncate">
          <span className="font-semibold text-slate-900">{value.full_name}</span>
          <span className="ml-2 text-xs text-slate-500">{[value.mrn, value.phone].filter(Boolean).join(" · ")}</span>
        </span>
        <button type="button" onClick={() => onChange(null)} className="text-xs font-semibold text-brand-700 hover:underline">
          Change
        </button>
      </div>
    );
  }

  return (
    <div className="mt-1">
      <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 focus-within:border-brand-700">
        <Icons.Search className="h-4 w-4 text-slate-400" />
        <input
          id={id}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Name, MRN or phone"
          autoComplete="off"
          className="w-full bg-transparent text-sm text-slate-900 outline-none"
        />
      </div>
      <ul className="mt-1 max-h-48 overflow-y-auto rounded-lg border border-slate-100 bg-white">
        {results === null ? (
          <li className="flex justify-center py-3">
            <Spinner />
          </li>
        ) : results.length === 0 ? (
          <li className="px-3 py-2 text-xs text-slate-400">No matching patients. Register them in the patient registry first.</li>
        ) : (
          results.slice(0, 8).map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => onChange(p)}
                className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-brand-50"
              >
                <span className="truncate font-medium text-slate-800">{p.full_name}</span>
                <span className="shrink-0 text-xs text-slate-400">{[p.mrn, p.phone].filter(Boolean).join(" · ")}</span>
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
