import { Icons } from "@/components/icons";
import type { NavItem } from "@/components/shell/navigation";

export const RECEPTION_NAV: NavItem[] = [
  { href: "/reception/agent", label: "Voice Agent", icon: Icons.Bot },
  { href: "/reception/appointments", label: "Appointments", icon: Icons.CalendarClock },
];

/** Shown under "Clinic" */
export const RECEPTION_CLINIC_NAV: NavItem[] = [{ href: "/reception/monitoring", label: "Call Costs", icon: Icons.Activity }];
