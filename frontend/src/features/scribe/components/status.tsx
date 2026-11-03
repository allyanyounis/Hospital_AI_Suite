/** Scribe pipeline status: progress bar, pill and capture-source tag. */

import type { PipelineStatus } from "../types";

export const STATUS_META: Record<PipelineStatus, { label: string; tone: string; bar: string; step: number }> = {
  pending: { label: "Awaiting note", tone: "text-slate-600", bar: "bg-slate-300", step: 1 },
  drafting: { label: "Drafting note", tone: "text-amber-700", bar: "bg-amber-500", step: 2 },
  ready: { label: "Ready to review", tone: "text-emerald-700", bar: "bg-emerald-500", step: 3 },
  failed: { label: "Failed", tone: "text-rose-700", bar: "bg-rose-500", step: 3 },
  signed: { label: "Signed", tone: "text-brand-800", bar: "bg-brand-700", step: 4 },
};

/** Pipeline progress: transcript -> drafting -> ready -> signed */
export function PipelineBar({ status, error }: { status: PipelineStatus; error?: string | null }) {
  const meta = STATUS_META[status];
  return (
    <div className="w-44" title={error ?? undefined}>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className={`flex items-center gap-1.5 font-semibold ${meta.tone}`}>
          {status === "drafting" ? (
            <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-amber-200 border-t-amber-600" />
          ) : (
            <span className={`h-1.5 w-1.5 rounded-full ${meta.bar}`} />
          )}
          {meta.label}
        </span>
        <span className="tabular-nums text-slate-400">{meta.step}/4</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${meta.bar} ${status === "drafting" ? "animate-pulse" : ""}`}
          style={{ width: `${(meta.step / 4) * 100}%` }}
        />
      </div>
    </div>
  );
}

const PILL_STYLE: Record<PipelineStatus, string> = {
  pending: "border-slate-200 bg-slate-50 text-slate-600",
  drafting: "border-amber-200 bg-amber-50 text-amber-700",
  ready: "border-emerald-200 bg-emerald-50 text-emerald-700",
  failed: "border-rose-200 bg-rose-50 text-rose-700",
  signed: "border-brand-200 bg-brand-50 text-brand-800",
};

export function StatusPill({ status }: { status: PipelineStatus }) {
  const label = status === "ready" ? "Draft" : STATUS_META[status].label;
  return (
    <span className={`rounded-md border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${PILL_STYLE[status]}`}>
      {label}
    </span>
  );
}

export function SourceTag({ source }: { source: string }) {
  if (source === "live")
    return (
      <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-emerald-600">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        Live
      </span>
    );
  if (source === "recording") return <span className="text-[10px] font-bold uppercase tracking-wide text-sky-600">Upload</span>;
  return <span className="text-[10px] font-bold uppercase tracking-wide text-violet-600">Sample</span>;
}
