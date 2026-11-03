"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, Spinner, Tabs } from "@/shared/ui/ui";
import { clinicalApi, clinicalKeys } from "../api";
import { AllergyBanner } from "./AllergyBanner";
import { HistoryPanel } from "./HistoryPanel";
import { LabsPanel } from "./LabsPanel";
import { OverviewPanel } from "./OverviewPanel";
import { ReportsPanel } from "./ReportsPanel";
import { VitalsPanel } from "./VitalsPanel";

type Tab = "overview" | "labs" | "vitals" | "reports" | "history";

/** A patient's clinical record in tabs, one topic per tab; each tab loads its own data when opened. */
export function ClinicalRecord({ patientId }: { patientId: number }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [test, setTest] = useState("");
  const summary = useQuery({ queryKey: clinicalKeys.summary(patientId), queryFn: () => clinicalApi.summary(patientId) });

  if (summary.isPending)
    return (
      <div className="flex justify-center py-12">
        <Spinner className="h-6 w-6" />
      </div>
    );
  if (summary.isError) return <Notice tone="error">{summary.error.message}</Notice>;
  const s = summary.data;
  const reports = Object.values(s.report_counts).reduce((n, c) => n + (c ?? 0), 0);

  return (
    <div className="space-y-4">
      <AllergyBanner allergies={s.allergies} />
      <Card className="overflow-hidden">
        <Tabs<Tab>
          value={tab}
          onChange={setTab}
          tabs={[
            { id: "overview", label: "Overview", icon: <Icons.Grid className="h-4 w-4" /> },
            { id: "labs", label: "Labs", icon: <Icons.Flask className="h-4 w-4" />, count: s.out_of_range },
            { id: "vitals", label: "Vitals", icon: <Icons.Heart className="h-4 w-4" /> },
            { id: "reports", label: `Reports (${reports})`, icon: <Icons.File className="h-4 w-4" /> },
            { id: "history", label: "History", icon: <Icons.Clipboard className="h-4 w-4" /> },
          ]}
        />
        <div className="p-4">
          {tab === "overview" && (
            <OverviewPanel
              summary={s}
              onOpenLab={(code) => {
                setTest(code);
                setTab("labs");
              }}
            />
          )}
          {tab === "labs" && <LabsPanel patientId={patientId} latest={s.labs} test={test} onTest={setTest} />}
          {tab === "vitals" && <VitalsPanel patientId={patientId} ranges={s.vital_ranges} />}
          {tab === "reports" && <ReportsPanel patientId={patientId} counts={s.report_counts} />}
          {tab === "history" && <HistoryPanel patientId={patientId} />}
        </div>
      </Card>
    </div>
  );
}
