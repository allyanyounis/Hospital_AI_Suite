/** Shared building blocks. Colours come from the theme tokens in globals.css (brand-*, surface). */

import { Icons } from "./icons";

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

export type BadgeTone = "neutral" | "brand" | "ok" | "warn" | "bad" | "info";
const BADGE_STYLE: Record<BadgeTone, string> = {
  neutral: "border-slate-200 bg-slate-50 text-slate-600",
  brand: "border-brand-200 bg-brand-50 text-brand-800",
  ok: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warn: "border-amber-200 bg-amber-50 text-amber-700",
  bad: "border-rose-200 bg-rose-50 text-rose-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
};

/** Small uppercase status label (same look as the scribe StatusPill). */
export function Badge({
  tone = "neutral",
  className = "",
  title,
  children,
}: {
  tone?: BadgeTone;
  className?: string;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${BADGE_STYLE[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export type TabDef<T extends string = string> = {
  id: T;
  label: React.ReactNode;
  /** Shown as an amber pill after the label when > 0 */
  count?: number;
  icon?: React.ReactNode;
  disabled?: boolean;
  /** Tooltip, e.g. why the tab is disabled */
  title?: string;
};

/** Underlined tab strip for the top of a Card. Renders only the buttons; the caller renders the active panel. */
export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  className = "",
}: {
  tabs: TabDef<T>[];
  value: T;
  onChange: (id: T) => void;
  className?: string;
}) {
  return (
    <div role="tablist" className={`flex gap-1 overflow-x-auto border-b border-slate-100 px-4 ${className}`}>
      {tabs.map((tab) => {
        const active = tab.id === value;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.id)}
            disabled={tab.disabled}
            title={tab.title}
            className={`flex shrink-0 items-center gap-2 whitespace-nowrap border-b-2 px-3 py-3.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
              active ? "border-brand-700 text-brand-800" : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab.icon}
            {tab.label}
            {tab.count != null && tab.count > 0 && (
              <span className="rounded-full bg-amber-400 px-1.5 text-[10px] font-bold tabular-nums text-brand-950">
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export type SegmentedOption<T extends string = string> = { value: T; label: React.ReactNode; hint?: string };

/** Pill-shaped single choice (view modes, ranges); an option's `hint` is its tooltip. */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
  className = "",
}: {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Accessible name of the group */
  label?: string;
  className?: string;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={`inline-flex rounded-xl border border-slate-200 bg-slate-50 p-0.5 ${className}`}
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={active}
            title={option.hint}
            onClick={() => onChange(option.value)}
            className={`rounded-[10px] px-3 py-1.5 text-xs font-semibold ${
              active ? "bg-white text-brand-800 shadow-sm" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
