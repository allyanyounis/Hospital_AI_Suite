"use client";

import type { Finding } from "@/lib/api";

const SEVERITY_STYLE: Record<Finding["severity"], string> = {
  high: "border-red-300 bg-red-50 text-red-800",
  medium: "border-amber-300 bg-amber-50 text-amber-900",
  low: "border-slate-200 bg-slate-50 text-slate-700",
};

const CATEGORY_LABEL: Record<Finding["category"], string> = {
  unsupported: "Not supported by transcript",
  missing: "Possibly missing",
  inconsistency: "Inconsistent",
  safety: "Safety",
};

export function ReviewPanel({
  findings,
  onSelect,
  onDismiss,
}: {
  findings: Finding[];
  onSelect: (sourceIds: number[]) => void;
  onDismiss: () => void;
}) {
  return (
    <div className="mb-5 rounded-lg border border-slate-200 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Safety check · {findings.length ? `${findings.length} to review` : "no issues found"}
        </h3>
        <button onClick={onDismiss} className="text-xs text-slate-400 hover:text-slate-700">
          Hide
        </button>
      </div>
      {findings.length === 0 ? (
        <p className="text-sm text-slate-600">The note matches the transcript. You are still responsible for what you sign.</p>
      ) : (
        <ul className="space-y-1.5">
          {findings.map((f, i) => (
            <li key={i}>
              <button
                onClick={() => onSelect(f.source_segment_ids)}
                className={`w-full rounded-md border px-3 py-2 text-left text-sm ${SEVERITY_STYLE[f.severity]}`}
              >
                <span className="mr-2 text-xs font-semibold uppercase">
                  {f.severity} · {CATEGORY_LABEL[f.category]}
                  {f.section && ` · ${f.section}`}
                </span>
                <span className="block">{f.message}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
