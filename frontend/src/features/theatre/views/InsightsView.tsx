"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, PageHeader, Spinner, Tabs } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../api";
import { ExperimentPanel } from "../components/insights/ExperimentPanel";
import { ModelAuditPanel } from "../components/insights/ModelAuditPanel";
import { OneDayPanel } from "../components/insights/OneDayPanel";

type Tab = "audit" | "experiment" | "day";

/** /theatre/insights: whether the risk and duration models hold on real data, and the CP-SAT replanning experiment. */
export function InsightsView() {
  const [tab, setTab] = useState<Tab>("audit");
  const audit = useQuery({ queryKey: theatreKeys.modelAudit(), queryFn: theatreApi.modelAudit, staleTime: Infinity });
  const experiment = useQuery({
    queryKey: theatreKeys.experiment(),
    queryFn: theatreApi.experiment,
    staleTime: Infinity,
    enabled: tab !== "audit",
  });
  const q = tab === "audit" ? audit : experiment;

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Gauge className="h-6 w-6" />}
        title="Model check"
        subtitle="What the theatre's AI does and whether it works: the risk score and operation lengths checked against held-out patients, and a replanning experiment on simulated days. Nothing here changes the real lists."
      />
      <Card>
        <Tabs<Tab>
          tabs={[
            { id: "audit", label: "Risk model check", icon: <Icons.Heart /> },
            { id: "experiment", label: "Replanning experiment", icon: <Icons.Flask /> },
            { id: "day", label: "Try one day", icon: <Icons.Sparkles /> },
          ]}
          value={tab}
          onChange={setTab}
        />
      </Card>
      {q.isError ? (
        <Notice tone="error">{q.error.message}</Notice>
      ) : !q.data ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6" />
        </div>
      ) : tab === "audit" && audit.data ? (
        <ModelAuditPanel audit={audit.data} />
      ) : tab === "experiment" && experiment.data ? (
        <ExperimentPanel summary={experiment.data} />
      ) : null}
      {/* Stays mounted so a finished run survives switching tabs */}
      {experiment.data && (
        <div hidden={tab !== "day"}>
          <OneDayPanel example={experiment.data.experiment.example} />
        </div>
      )}
    </main>
  );
}
