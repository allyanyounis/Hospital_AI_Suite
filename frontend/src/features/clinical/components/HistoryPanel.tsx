"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, EmptyState, Spinner } from "@/shared/ui/ui";
import { clinicalApi, clinicalKeys } from "../api";
import type { HistoryKind } from "../types";
import { shortDate } from "./format";

const GROUPS: { kind: HistoryKind; label: string }[] = [
  { kind: "indication", label: "Reason for surgery" },
  { kind: "condition", label: "Conditions" },
  { kind: "surgery", label: "Previous operations" },
];

/** Medical history grouped by kind: the indication, ongoing conditions and past operations. */
export function HistoryPanel({ patientId }: { patientId: number }) {
  const q = useQuery({ queryKey: clinicalKeys.history(patientId), queryFn: () => clinicalApi.history(patientId) });
  if (q.isPending)
    return (
      <div className="flex justify-center py-10">
        <Spinner className="h-5 w-5" />
      </div>
    );
  const entries = q.data ?? [];
  if (!entries.length)
    return (
      <Card>
        <EmptyState title="No history recorded" />
      </Card>
    );
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {GROUPS.map((g) => {
        const items = entries.filter((e) => e.kind === g.kind);
        return (
          <Card key={g.kind} className="p-4">
            <p className="mb-2 text-sm font-semibold text-slate-900">{g.label}</p>
            {items.length === 0 ? (
              <p className="text-sm text-slate-400">None recorded</p>
            ) : (
              <ul className="space-y-2">
                {items.map((e) => (
                  <li key={e.id} className="text-sm text-slate-700">
                    {e.text}
                    <span className="block text-[11px] text-slate-400">{shortDate(e.noted_on)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        );
      })}
    </div>
  );
}
