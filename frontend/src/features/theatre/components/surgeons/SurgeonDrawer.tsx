"use client";

import { Drawer } from "@/shared/ui/overlays";
import { Badge } from "@/shared/ui/ui";
import type { Surgeon } from "../../types";
import { LeavePanel } from "./LeavePanel";
import { RosterEditor } from "./RosterEditor";

/** One surgeon: theatre days and leave. Editing needs theatre.roster; acting on affected cases needs theatre.manage. */
export function SurgeonDrawer({
  surgeon,
  canEdit,
  canManage,
  onClose,
}: {
  surgeon: Surgeon;
  canEdit: boolean;
  canManage: boolean;
  onClose: () => void;
}) {
  return (
    <Drawer
      title={surgeon.name}
      subtitle={
        <span className="flex flex-wrap items-center gap-2">
          {surgeon.specialty} · {surgeon.booked} case{surgeon.booked === 1 ? "" : "s"} booked
          {!surgeon.active && <Badge>Inactive</Badge>}
          {!canEdit && <Badge tone="info">Read only</Badge>}
        </span>
      }
      onClose={onClose}
    >
      <div className="space-y-6">
        <RosterEditor key={`roster-${surgeon.id}`} surgeon={surgeon} canEdit={canEdit} />
        <div className="border-t border-slate-100" />
        <LeavePanel key={`leave-${surgeon.id}`} surgeon={surgeon} canEdit={canEdit} canManage={canManage} />
      </div>
    </Drawer>
  );
}
