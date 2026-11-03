"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { useState } from "react";
import { cursorPagination, flattenPages } from "@/shared/api/pagination";
import { EmptyState, Segmented } from "@/shared/ui/ui";
import { VirtualTable, type VirtualColumn } from "@/shared/ui/virtual";
import { theatreApi, theatreKeys } from "../../api";
import { dayLabel, span } from "../../lib/time";
import type { OffListCase, Urgency } from "../../types";
import { URGENCY_INFO } from "../../types";
import { UrgencyBadge } from "../common";

const base: VirtualColumn<OffListCase>[] = [
  {
    key: "patient",
    header: "Patient",
    width: "minmax(10rem,1.2fr)",
    render: (c) => <span className="font-semibold text-slate-900">{c.name}</span>,
  },
  {
    key: "op",
    header: "Operation",
    width: "minmax(12rem,2fr)",
    render: (c) => (
      <span>
        {c.procedure} <span className="text-xs text-slate-400">· {span(c.minutes)}</span>
      </span>
    ),
  },
  { key: "surgeon", header: "Surgeon", width: "minmax(8rem,1fr)", render: (c) => c.surgeon ?? "—" },
];

/** Cases not on any list yet, filtered by urgency; "Find a place" opens the intake for one. */
export function WaitingTable({
  canManage,
  onIntake,
  onOpen,
}: {
  canManage: boolean;
  onIntake: (caseId: number) => void;
  onOpen: (caseId: number) => void;
}) {
  const [urgency, setUrgency] = useState<Urgency | "">("");
  const q = useInfiniteQuery({
    queryKey: theatreKeys.waiting(urgency),
    queryFn: ({ pageParam }) => theatreApi.waiting(urgency, pageParam),
    ...cursorPagination<OffListCase>(),
  });
  const rows = flattenPages(q.data);

  return (
    <div>
      <div className="flex justify-end border-b border-slate-100 px-4 py-2">
        <Segmented<Urgency | "">
          label="Urgency"
          value={urgency}
          onChange={setUrgency}
          options={[
            { value: "", label: "All" },
            ...(["immediate", "urgent", "expedited", "elective"] as Urgency[]).map((u) => ({
              value: u,
              label: URGENCY_INFO[u].label,
            })),
          ]}
        />
      </div>
      <VirtualTable
        items={rows}
        height={480}
        estimateSize={48}
        getKey={(c) => c.id}
        loading={q.isPending || q.isFetchingNextPage}
        onEndReached={() => q.hasNextPage && q.fetchNextPage()}
        onRowClick={(c) => onOpen(c.id)}
        empty={<EmptyState title="Nobody waiting" />}
        columns={[
          ...base,
          { key: "urgency", header: "Urgency", width: "7rem", render: (c) => <UrgencyBadge urgency={c.urgency} /> },
          {
            key: "act",
            header: "",
            width: "8rem",
            className: "text-right",
            render: (c) =>
              canManage ? (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onIntake(c.id);
                  }}
                  className="rounded-lg bg-brand-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-brand-800"
                >
                  Find a place
                </button>
              ) : null,
          },
        ]}
      />
    </div>
  );
}

/** Cases the planner (or a user) moved off today to a later day. */
export function LaterTable({ onOpen }: { onOpen: (caseId: number) => void }) {
  const q = useInfiniteQuery({
    queryKey: theatreKeys.deferred(),
    queryFn: ({ pageParam }) => theatreApi.deferred(pageParam),
    ...cursorPagination<OffListCase>(),
  });
  return (
    <VirtualTable
      items={flattenPages(q.data)}
      height={480}
      estimateSize={48}
      getKey={(c) => c.id}
      loading={q.isPending || q.isFetchingNextPage}
      onEndReached={() => q.hasNextPage && q.fetchNextPage()}
      onRowClick={(c) => onOpen(c.id)}
      empty={<EmptyState title="No case moved" />}
      columns={[
        ...base,
        { key: "day", header: "New date", width: "8rem", render: (c) => (c.day ? dayLabel(c.day) : "—") },
      ]}
    />
  );
}
