"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useSession } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";
import { Card, EmptyState, Notice, PageHeader, Spinner, Tabs } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../api";
import { SurgeonDrawer } from "../components/surgeons/SurgeonDrawer";
import { SurgeonTable } from "../components/surgeons/SurgeonTable";
import type { Surgeon } from "../types";

/** /theatre/surgeons: surgeons by specialty with their theatre days and leave; a row opens the roster drawer. */
export function SurgeonsView() {
  const { can } = useSession();
  const q = useQuery({ queryKey: theatreKeys.surgeons(), queryFn: theatreApi.surgeons });
  const [tab, setTab] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);

  const groups = new Map<string, Surgeon[]>();
  for (const s of q.data ?? []) groups.set(s.specialty, [...(groups.get(s.specialty) ?? []), s]);
  const specialties = [...groups.keys()].sort((a, b) => a.localeCompare(b));
  const active = tab && groups.has(tab) ? tab : (specialties[0] ?? "");
  const open = q.data?.find((s) => s.id === openId) ?? null;

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.UserCog className="h-6 w-6" />}
        title="Surgeons & rosters"
        subtitle="Who operates on which weekday, upcoming leave and how many cases each surgeon has listed. Open a surgeon to change their theatre days or add leave."
      />
      {q.isError ? (
        <Notice tone="error">{q.error.message}</Notice>
      ) : !q.data ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6" />
        </div>
      ) : specialties.length === 0 ? (
        <Card>
          <EmptyState icon={<Icons.UserCog className="h-5 w-5" />} title="No theatre surgeons">
            Surgeons are staff members whose specialty matches a theatre&apos;s.
          </EmptyState>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <Tabs
            tabs={specialties.map((s) => ({ id: s, label: `${s} (${groups.get(s)?.length ?? 0})` }))}
            value={active}
            onChange={setTab}
          />
          <SurgeonTable surgeons={groups.get(active) ?? []} selectedId={openId} onOpen={(s) => setOpenId(s.id)} />
        </Card>
      )}
      {open && (
        <SurgeonDrawer
          surgeon={open}
          canEdit={can("theatre.roster")}
          canManage={can("theatre.manage")}
          onClose={() => setOpenId(null)}
        />
      )}
    </main>
  );
}
