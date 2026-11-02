import { Icons, type IconComponent } from "@/components/icons";

export type NavItem = { href: string; label: string; icon: IconComponent };
export type NavGroup = { title: string; items: NavItem[] };

export const NAVIGATION: NavGroup[] = [
  {
    title: "Overview",
    items: [{ href: "/", label: "Dashboard", icon: Icons.Grid }],
  },
  {
    title: "AI Scribe",
    items: [
      { href: "/scribe/session", label: "Live Session", icon: Icons.Mic },
      { href: "/scribe/board", label: "Board", icon: Icons.Pulse },
      { href: "/scribe/encounters", label: "Encounters", icon: Icons.File },
    ],
  },
  {
    title: "AI Receptionist",
    items: [
      { href: "/reception/agent", label: "Voice Agent", icon: Icons.Bot },
      { href: "/reception/appointments", label: "Appointments", icon: Icons.CalendarClock },
    ],
  },
  {
    title: "Clinic",
    items: [
      { href: "/schedule", label: "Scheduler", icon: Icons.Calendar },
      { href: "/scribe/metrics", label: "Pilot Metrics", icon: Icons.Chart },
      { href: "/reception/monitoring", label: "Call Costs", icon: Icons.Activity },
      { href: "/account", label: "Account", icon: Icons.User },
    ],
  },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function pageTitle(pathname: string): string {
  for (const group of NAVIGATION) {
    const item = group.items.find((i) => isActive(pathname, i.href));
    if (item) return item.label;
  }
  return "Dashboard";
}
