/** Shared building blocks. Colours come from the theme tokens in globals.css (brand-*, surface). */

import { Icons } from "@/components/icons";
import type { PipelineStatus } from "@/lib/api";

export function PageHeader({
  icon,
  title,
  subtitle,
  aside,
}: {
  icon?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="flex items-center gap-2.5 text-2xl font-semibold text-slate-900">
          {icon && <span className="text-brand-700">{icon}</span>}
          {title}
        </h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-slate-500">{subtitle}</p>}
      </div>
      {aside}
    </div>
  );
}

export function Card({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return <section className={`rounded-2xl border border-slate-200/80 bg-white shadow-sm ${className}`}>{children}</section>;
}

export function StatCard({
  icon,
  label,
  value,
  note,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  note?: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <Card className={`card-hover flex items-center gap-3 p-4 ${accent ? "border-amber-200 bg-amber-50/60" : ""}`}>
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
          accent ? "bg-amber-400 text-brand-950" : "bg-brand-50 text-brand-700"
        }`}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <p className="truncate text-xl font-bold tabular-nums text-slate-900">{value}</p>
        <p className="truncate text-xs text-slate-500">{label}</p>
        {note && <p className="truncate text-[11px] text-slate-400">{note}</p>}
      </div>
    </Card>
  );
}

type NoticeTone = "info" | "success" | "warning" | "error";
const NOTICE_STYLE: Record<NoticeTone, string> = {
  info: "border-brand-200 bg-brand-50 text-brand-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning: "border-amber-200 bg-amber-50/70 text-amber-900",
  error: "border-rose-200 bg-rose-50 text-rose-700",
};

export function Notice({
  tone = "info",
  className = "",
  children,
}: {
  tone?: NoticeTone;
  className?: string;
  children: React.ReactNode;
}) {
  const Icon = tone === "success" ? Icons.CheckCircle : Icons.Alert;
  return (
    <div className={`flex items-start gap-2 rounded-xl border px-4 py-3 text-sm ${NOTICE_STYLE[tone]} ${className}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${checked ? "bg-brand-700" : "bg-slate-300"}`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${checked ? "left-[22px]" : "left-0.5"}`}
      />
    </button>
  );
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return <span className={`inline-block animate-spin rounded-full border-2 border-slate-200 border-t-brand-700 ${className}`} />;
}

export function EmptyState({ icon, title, children }: { icon?: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      {icon && (
        <span className="mb-1 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-700">{icon}</span>
      )}
      <p className="text-sm font-semibold text-slate-800">{title}</p>
      {children && <div className="max-w-sm text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function Avatar({
  text,
  tone = "brand",
  size = "md",
}: {
  text: string;
  tone?: "brand" | "amber" | "slate";
  size?: "sm" | "md";
}) {
  const tones = {
    brand: "border-brand-200 bg-brand-50 text-brand-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    slate: "border-slate-200 bg-white text-slate-600",
  };
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full border font-bold ${tones[tone]} ${
        size === "sm" ? "h-8 w-8 text-[11px]" : "h-10 w-10 text-xs"
      }`}
    >
      {text}
    </span>
  );
}

// --- Scribe pipeline status --------------------------------------------------------------------------------------

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

const STEPS = ["Setup", "Listening", "Synthesize"];

export function Stepper({ step }: { step: number }) {
  return (
    <Card className="mb-5 px-6 py-4">
      <ol className="flex items-start">
        {STEPS.map((label, i) => {
          const n = i + 1;
          const done = n < step;
          const active = n === step;
          return (
            <li key={label} className={`flex items-start ${n < STEPS.length ? "flex-1" : ""}`}>
              <div className="flex flex-col items-center gap-1.5">
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-colors ${
                    done
                      ? "bg-brand-700 text-white"
                      : active
                        ? "bg-amber-400 text-brand-950 ring-4 ring-amber-100"
                        : "border-2 border-slate-200 bg-white text-slate-400"
                  }`}
                >
                  {done ? <Icons.Check className="h-4 w-4" /> : n}
                </span>
                <span
                  className={`text-[11px] font-bold uppercase tracking-wider ${done || active ? "text-brand-900" : "text-slate-400"}`}
                >
                  {label}
                </span>
              </div>
              {n < STEPS.length && (
                <span className={`mx-3 mt-5 h-0.5 flex-1 rounded-full ${n < step ? "bg-brand-600" : "bg-slate-200"}`} />
              )}
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
