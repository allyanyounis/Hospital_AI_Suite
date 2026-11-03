"use client";

import { Icons } from "@/shared/ui/icons";
import { Avatar, Badge, EmptyState } from "@/shared/ui/ui";
import { VirtualTable, type VirtualColumn } from "@/shared/ui/virtual";
import { dayLabel, hm, WEEKDAYS } from "../../lib/time";
import type { Surgeon } from "../../types";

const ROW = 56;

const initials = (name: string) =>
  name
    .replace(/^Dr\.?\s+/i, "")
    .split(/\s+/)
    .map((w) => w[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();

const weekdayColumns: VirtualColumn<Surgeon>[] = [0, 1, 2, 3, 4].map((wd) => ({
  key: `wd${wd}`,
  header: WEEKDAYS[wd],
  width: "6.5rem",
  className: "tabular-nums",
  render: (s) => {
    const d = s.days.find((x) => x.weekday === wd);
    return d ? (
      <span className="text-xs text-slate-700">
        {hm(d.start)}–{hm(d.end)}
      </span>
    ) : (
      <span className="text-xs text-slate-300">—</span>
    );
  },
}));

const columns: VirtualColumn<Surgeon>[] = [
  {
    key: "name",
    header: "Surgeon",
    width: "minmax(12rem,1.5fr)",
    render: (s) => (
      <span className="flex items-center gap-2.5">
        <Avatar text={initials(s.name)} size="sm" tone={s.active ? "brand" : "slate"} />
        <span className="min-w-0 truncate font-semibold text-slate-900">{s.name}</span>
        {!s.active && <Badge>Inactive</Badge>}
      </span>
    ),
  },
  ...weekdayColumns,
  {
    key: "leave",
    header: "Leave",
    width: "6rem",
    render: (s) =>
      s.leave.length ? (
        <span title={s.leave.map((l) => `${dayLabel(l.starts_on)} – ${dayLabel(l.ends_on)}: ${l.reason}`).join("\n")}>
          <Badge tone="warn">{s.leave.length} upcoming</Badge>
        </span>
      ) : (
        <span className="text-xs text-slate-300">—</span>
      ),
  },
  {
    key: "booked",
    header: "Booked",
    width: "5rem",
    className: "text-right tabular-nums",
    render: (s) => <span className="font-semibold text-slate-800">{s.booked}</span>,
  },
];

/** Surgeons of one specialty with their weekly theatre hours, upcoming leave and listed cases; a row opens it. */
export function SurgeonTable({
  surgeons,
  selectedId,
  onOpen,
}: {
  surgeons: Surgeon[];
  selectedId: number | null;
  onOpen: (surgeon: Surgeon) => void;
}) {
  return (
    <VirtualTable
      items={surgeons}
      height={Math.min(560, 36 + Math.max(surgeons.length, 3) * ROW)}
      estimateSize={ROW}
      getKey={(s) => s.id}
      onRowClick={onOpen}
      isSelected={(s) => s.id === selectedId}
      empty={<EmptyState icon={<Icons.UserCog className="h-5 w-5" />} title="No surgeons in this specialty" />}
      columns={columns}
    />
  );
}
