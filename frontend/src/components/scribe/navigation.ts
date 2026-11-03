import { Icons } from "@/components/icons";
import type { NavItem } from "@/components/shell/navigation";

export const SCRIBE_NAV: NavItem[] = [
  { href: "/scribe/session", label: "Live Session", icon: Icons.Mic },
  { href: "/scribe/board", label: "Board", icon: Icons.Pulse },
  { href: "/scribe/encounters", label: "Encounters", icon: Icons.File },
];

/** Shown under "Clinic" */
export const SCRIBE_CLINIC_NAV: NavItem[] = [{ href: "/scribe/metrics", label: "Pilot Metrics", icon: Icons.Chart }];
