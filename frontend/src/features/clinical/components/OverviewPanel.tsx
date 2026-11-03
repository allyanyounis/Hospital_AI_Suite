import { Icons } from "@/shared/ui/icons";
import { Badge, Card, EmptyState } from "@/shared/ui/ui";
import type { ClinicalSummary, LabLatest, Trend, VitalRange } from "../types";
import { REPORT_LABEL } from "../types";
import { FLAG_TONE, flagText, formatNumber, shortDateTime, vitalValue } from "./format";

/** At-a-glance chart: the latest vitals against the previous set, the latest lab per test, and record counts. */
export function OverviewPanel({ summary, onOpenLab }: { summary: ClinicalSummary; onOpenLab: (test: string) => void }) {
  return (
    <div className="space-y-5">
      <VitalsSnapshot summary={summary} />
      <section>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-900">Latest labs</h3>
          {summary.out_of_range > 0 && <Badge tone="warn">{summary.out_of_range} out of range</Badge>}
        </div>
        {summary.labs.length === 0 ? (
          <Card>
            <EmptyState icon={<Icons.Flask className="h-6 w-6" />} title="No lab results yet" />
          </Card>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {summary.labs.map((lab) => (
              <LabTile key={lab.test} lab={lab} onClick={() => onOpenLab(lab.test)} />
            ))}
          </div>
        )}
      </section>
      <section className="flex flex-wrap gap-2 text-xs text-slate-600">
        {Object.entries(summary.report_counts).map(([kind, n]) => (
          <span key={kind} className="rounded-full border border-slate-200 bg-white px-2.5 py-1">
            {REPORT_LABEL[kind as keyof typeof REPORT_LABEL] ?? kind} · {n}
          </span>
        ))}
        <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1">
          History entries · {summary.history_count}
        </span>
      </section>
    </div>
  );
}

function TrendIcon({ trend }: { trend: Trend }) {
  if (trend === "up") return <Icons.TrendUp className="h-3.5 w-3.5 text-slate-500" />;
  if (trend === "down") return <Icons.TrendDown className="h-3.5 w-3.5 text-slate-500" />;
  if (trend === "same") return <Icons.Minus className="h-3.5 w-3.5 text-slate-400" />;
  return null;
}

function LabTile({ lab, onClick }: { lab: LabLatest; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`card-hover rounded-xl border bg-white px-3 py-2.5 text-left shadow-sm ${
        lab.flag === "normal" ? "border-slate-200" : "border-amber-200"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-xs font-semibold text-slate-500">{lab.name}</span>
        {lab.flag !== "normal" && <Badge tone={FLAG_TONE[lab.flag]}>{lab.flag}</Badge>}
      </div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className={`text-lg tabular-nums ${flagText(lab.flag)}`}>{formatNumber(lab.value, 2)}</span>
        <span className="text-xs text-slate-400">{lab.unit}</span>
        <TrendIcon trend={lab.trend} />
        {lab.previous != null && (
          <span className="text-[11px] text-slate-400">from {formatNumber(lab.previous, 2)}</span>
        )}
      </div>
      <p className="mt-0.5 text-[11px] text-slate-400">
        Range {lab.ref_low}–{lab.ref_high} · {shortDateTime(lab.collected_at)}
      </p>
    </button>
  );
}

const SHOWN: VitalRange["key"][] = ["heart_rate", "systolic_bp", "spo2", "temperature_c", "resp_rate"];

function VitalsSnapshot({ summary }: { summary: ClinicalSummary }) {
  const v = summary.vitals;
  if (!v)
    return (
      <Card>
        <EmptyState icon={<Icons.Heart className="h-6 w-6" />} title="No vitals recorded" />
      </Card>
    );
  const prev = summary.previous_vitals;
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Latest vitals</h3>
        <span className="text-xs text-slate-400">{shortDateTime(v.recorded_at)}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {SHOWN.map((key) => {
          const range = summary.vital_ranges.find((r) => r.key === key);
          const bp = key === "systolic_bp";
          const flag = v.flags[key] ?? (bp ? v.flags.diastolic_bp : undefined);
          return (
            <Card key={key} className="px-3 py-2.5">
              <p className="truncate text-xs font-semibold text-slate-500">{bp ? "Blood pressure" : range?.label}</p>
              <p className={`mt-1 text-lg tabular-nums ${flagText(flag)}`}>
                {vitalValue(v, key)} <span className="text-xs font-normal text-slate-400">{range?.unit}</span>
              </p>
              <p className="text-[11px] text-slate-400">{prev ? `Before ${vitalValue(prev, key)}` : "No earlier set"}</p>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
