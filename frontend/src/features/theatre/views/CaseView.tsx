"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useSession } from "@/features/auth";
import { ClinicalRecord } from "@/features/clinical";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, PageHeader, Spinner, Tabs } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../api";
import { CaseActions } from "../components/CaseActions";
import { RiskPill, UrgencyBadge } from "../components/common";
import { IntakeModal } from "../components/IntakeModal";
import { useDemoClock } from "../lib/demoClock";
import { dayLabel, hm, span } from "../lib/time";
import type { Cardiac, CaseDetail } from "../types";

type Tab = "overview" | "risk" | "patient";

/** One operation (/theatre/cases/[id]): when and where, its phases, the actions, the risk and the patient's record. */
export function CaseView({ caseId }: { caseId: number }) {
  const session = useSession();
  const router = useRouter();
  const at = useDemoClock();
  const [tab, setTab] = useState<Tab>("overview");
  const [intake, setIntake] = useState(false);
  const q = useQuery({ queryKey: theatreKeys.case(caseId, at), queryFn: () => theatreApi.caseDetail(caseId, at) });
  const d = q.data;

  return (
    <main className="space-y-4 px-4 py-6 sm:px-8">
      <Link href="/theatre" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-700">
        <Icons.ArrowLeft className="h-4 w-4" /> Theatre board
      </Link>
      {q.isPending ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-6 w-6" />
        </div>
      ) : q.isError || !d ? (
        <Notice tone="error">{q.error?.message ?? "Case not found"}</Notice>
      ) : (
        <>
          <PageHeader
            icon={<Icons.Scissors className="h-6 w-6" />}
            title={d.procedure.title}
            subtitle={`${d.patient.name} · ${d.patient.age} ${d.patient.sex} · ${d.procedure.specialty}`}
            aside={<UrgencyBadge urgency={d.urgency} />}
          />
          <Card className="overflow-hidden">
            <Tabs<Tab>
              value={tab}
              onChange={setTab}
              tabs={[
                { id: "overview", label: "Overview", icon: <Icons.Grid className="h-4 w-4" /> },
                { id: "risk", label: "Risk", icon: <Icons.Gauge className="h-4 w-4" /> },
                ...(session.can("clinical.view")
                  ? [{ id: "patient" as const, label: "Patient record", icon: <Icons.User className="h-4 w-4" /> }]
                  : []),
              ]}
            />
            <div className="p-4">
              {tab === "overview" && (
                <Overview
                  d={d}
                  canManage={session.can("theatre.manage")}
                  onIntake={() => setIntake(true)}
                  onCanceled={() => router.push("/theatre")}
                />
              )}
              {tab === "risk" && <RiskPanel d={d} />}
              {tab === "patient" && (
                <div className="space-y-3">
                  <Link href={`/patients/${d.patient.id}`} className="text-sm font-semibold text-brand-700 hover:underline">
                    Open the full chart
                  </Link>
                  <ClinicalRecord patientId={d.patient.id} />
                </div>
              )}
            </div>
          </Card>
          {intake && <IntakeModal caseId={d.id} onClose={() => setIntake(false)} />}
        </>
      )}
    </main>
  );
}

function Overview({
  d,
  canManage,
  onIntake,
  onCanceled,
}: {
  d: CaseDetail;
  canManage: boolean;
  onIntake: () => void;
  onCanceled: () => void;
}) {
  const t = d.timing;
  const high = d.risk.pct >= 1.5 * d.risk.average;
  const when = d.day ? `${d.day === d.today ? "Today" : dayLabel(d.day)}${t ? ` · ${hm(t.start)}–${hm(t.end)}` : ""}` : "Waiting list";
  const stats: [string, React.ReactNode, string][] = [
    ["Risk", <RiskPill key="r" pct={d.risk.pct} high={high} model={d.risk.model} />, d.risk.model === "EuroSCORE II" ? "EuroSCORE II, death" : "ICU or death"],
    ["Start", t ? hm(t.start) : "—", t ? (t.start > t.booked ? `${t.start - t.booked} min late` : "on time") : ""],
    ["Finish", t ? hm(t.end) : "—", t ? `1 in 10 after ${hm(t.latest)}` : ""],
    ["Late start", t && t.state === "wait" ? `${t.late_pct}%` : "—", "chance of 30+ min"],
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {stats.map(([label, value, note]) => (
          <div key={label} className="rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{value}</p>
            <p className="text-xs text-slate-500">{note}</p>
          </div>
        ))}
      </div>
      {t?.rota && <Notice tone="warning">{t.rota}</Notice>}
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="space-y-3">
          <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-y-2 text-sm">
            <dt className="text-slate-500">When</dt>
            <dd className="text-slate-900">{when}</dd>
            <dt className="text-slate-500">Theatre</dt>
            <dd className="text-slate-900">{d.room.code}</dd>
            <dt className="text-slate-500">Surgeon</dt>
            <dd className="text-slate-900">{d.surgeon ?? "—"}</dd>
            <dt className="text-slate-500">Pre-op</dt>
            <dd className="text-slate-900">
              ASA {d.preop.asa}
              {d.preop.weight_kg ? ` · ${d.preop.weight_kg} kg` : ""}
              {d.preop.height_cm ? ` · ${d.preop.height_cm} cm` : ""}
            </dd>
            <dt className="text-slate-500">Allergies</dt>
            <dd className={d.patient.allergies && d.patient.allergies !== "None known" ? "text-rose-700" : "text-slate-900"}>
              {d.patient.allergies || "None known"}
            </dd>
          </dl>
          {canManage && <CaseActions detail={d} onIntake={onIntake} onCanceled={onCanceled} />}
        </section>
        <section>
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Time in theatre</h3>
          <table className="w-full text-sm">
            <tbody className="divide-y divide-slate-100">
              {t
                ? t.phases.map((p) => (
                    <tr key={p.key} className={t.state === "in" && t.phase === p.label ? "bg-brand-50 font-semibold" : ""}>
                      <td className="py-1.5 text-slate-700">{p.label}</td>
                      <td className="py-1.5 tabular-nums text-slate-500">
                        {hm(p.start)}–{hm(p.end)}
                      </td>
                      <td className="py-1.5 text-right tabular-nums">{span(p.end - p.start)}</td>
                    </tr>
                  ))
                : d.phases.map((p) => (
                    <tr key={p.key}>
                      <td className="py-1.5 text-slate-700">{p.label}</td>
                      <td />
                      <td className="py-1.5 text-right tabular-nums">{span(p.minutes)}</td>
                    </tr>
                  ))}
              <tr className="font-semibold">
                <td className="py-1.5">Under anaesthesia</td>
                <td />
                <td className="py-1.5 text-right tabular-nums">{span(t ? t.end - t.start : d.procedure.minutes)}</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-2 text-xs text-slate-500">Planned length from {d.procedure.source}.</p>
        </section>
      </div>
    </div>
  );
}

const CARDIAC_LABELS: Record<keyof Cardiac, [string, string?]> = {
  lvef: ["LV ejection fraction", "%"],
  nyha: ["NYHA class", ""],
  pa_systolic: ["PA systolic pressure", "mmHg"],
  ccs4: ["CCS 4 angina"],
  recent_mi: ["MI in last 90 days"],
  iddm: ["Diabetes on insulin"],
  redo: ["Previous cardiac surgery"],
  lung: ["Chronic lung disease"],
  arteriopathy: ["Extracardiac arteriopathy"],
  poor_mobility: ["Poor mobility"],
  dialysis: ["Dialysis"],
  endocarditis: ["Active endocarditis"],
  critical: ["Critical state"],
};

function RiskPanel({ d }: { d: CaseDetail }) {
  const r = d.risk;
  const cardiac = r.model === "EuroSCORE II";
  const top = Math.max(...r.factors.map((f) => Math.abs(f.push)), 0.01);
  const high = r.pct >= 1.5 * r.average;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section>
        <p className={`text-4xl font-semibold tabular-nums ${high ? "text-rose-700" : "text-slate-900"}`}>{r.pct}%</p>
        <p className="text-sm text-slate-600">
          <b>{r.outcome}</b> · average {r.average}%
        </p>
        <h4 className="mt-4 mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Main drivers</h4>
        <div className="space-y-2">
          {r.factors.map((f) => (
            <div key={f.label} className="grid grid-cols-[minmax(0,1fr)_8rem_3.5rem] items-center gap-2 text-sm">
              <span className="truncate">
                {f.label}{" "}
                <b>
                  {f.value}
                  {f.unit ? ` ${f.unit}` : ""}
                </b>
              </span>
              <span className="h-2 rounded-full bg-slate-100">
                <i
                  className={`block h-2 rounded-full ${f.push > 0 ? "bg-risk" : "bg-emerald-500"}`}
                  style={{ width: `${(Math.abs(f.push) / top) * 100}%` }}
                />
              </span>
              <small className="text-slate-500">{f.push > 0 ? "raises" : "lowers"}</small>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-500">
          {cardiac
            ? "EuroSCORE II (Nashef et al., 2012): 22,381 cardiac patients in 43 countries. Published coefficients, not trained here."
            : "Trained on 6,386 VitalDB operations (non-cardiac). Use for ranking and bed planning, not as a diagnosis."}{" "}
          The scheduler does not use this score; it plans from durations only.
        </p>
      </section>
      {cardiac && d.preop.cardiac && (
        <section>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">EuroSCORE II inputs</h4>
          <dl className="grid grid-cols-[minmax(0,1fr)_auto] gap-y-1.5 text-sm">
            {(Object.keys(CARDIAC_LABELS) as (keyof Cardiac)[]).map((key) => {
              const [label, unit] = CARDIAC_LABELS[key];
              const v = d.preop.cardiac![key];
              return (
                <div key={key} className="contents">
                  <dt className="text-slate-600">{label}</dt>
                  <dd className="text-right font-semibold text-slate-900">
                    {unit !== undefined ? `${v ?? "—"} ${unit}` : v ? "Yes" : <span className="font-normal text-slate-400">No</span>}
                  </dd>
                </div>
              );
            })}
          </dl>
        </section>
      )}
    </div>
  );
}
