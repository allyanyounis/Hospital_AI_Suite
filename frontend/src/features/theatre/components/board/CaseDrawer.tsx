"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Drawer } from "@/shared/ui/overlays";
import { Notice, Spinner } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../../api";
import { useDemoClock } from "../../lib/demoClock";
import { dayLabel, hm, span } from "../../lib/time";
import { CaseActions } from "../CaseActions";
import { RiskPill, UrgencyBadge } from "../common";

/** A quick look at one case from the board, with its actions; the full case page is one click away. */
export function CaseDrawer({
  caseId,
  canManage,
  onClose,
  onIntake,
}: {
  caseId: number;
  canManage: boolean;
  onClose: () => void;
  onIntake: (caseId: number) => void;
}) {
  const at = useDemoClock();
  const q = useQuery({ queryKey: theatreKeys.case(caseId, at), queryFn: () => theatreApi.caseDetail(caseId, at) });
  const d = q.data;
  const t = d?.timing;

  return (
    <Drawer
      title={d?.patient.name ?? "Case"}
      subtitle={d ? `${d.procedure.title} · ${d.room.code}` : undefined}
      onClose={onClose}
      footer={
        <div className="flex gap-3 text-sm font-semibold">
          <Link href={`/theatre/cases/${caseId}`} className="text-brand-700 hover:underline">
            Open case
          </Link>
          {d && (
            <Link href={`/patients/${d.patient.id}`} className="text-brand-700 hover:underline">
              Patient chart
            </Link>
          )}
        </div>
      }
    >
      {q.isPending ? (
        <div className="flex justify-center py-10">
          <Spinner className="h-5 w-5" />
        </div>
      ) : q.isError ? (
        <Notice tone="error">{q.error.message}</Notice>
      ) : (
        d && (
          <div className="space-y-5">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <Item label="Urgency">
                <UrgencyBadge urgency={d.urgency} />
              </Item>
              <Item label="Risk">
                <span className="flex items-center gap-1.5">
                  <RiskPill pct={d.risk.pct} high={d.risk.pct >= 1.5 * d.risk.average} model={d.risk.model} />
                  <span className="text-xs text-slate-500">avg {d.risk.average}%</span>
                </span>
              </Item>
              <Item label="Day">{d.day ? dayLabel(d.day) : "Waiting list"}</Item>
              <Item label="Time">{t ? `${hm(t.start)}–${hm(t.end)}` : "—"}</Item>
              <Item label="Surgeon">{d.surgeon ?? "—"}</Item>
              <Item label="Planned">{span(d.procedure.minutes + d.overrun)}</Item>
              <Item label="Patient">
                {d.patient.age} {d.patient.sex} · ASA {d.preop.asa}
              </Item>
              <Item label="Allergies">
                <span className={d.patient.allergies && d.patient.allergies !== "None known" ? "text-rose-700" : ""}>
                  {d.patient.allergies || "None known"}
                </span>
              </Item>
            </dl>
            {t?.rota && <Notice tone="warning">{t.rota}</Notice>}
            {canManage && <CaseActions detail={d} onIntake={onIntake} onCanceled={onClose} />}
          </div>
        )
      )}
    </Drawer>
  );
}

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</dt>
      <dd className="mt-0.5 text-slate-800">{children}</dd>
    </div>
  );
}
