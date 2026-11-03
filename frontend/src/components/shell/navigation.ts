import { Icons, type IconComponent } from "@/components/icons";
import { RECEPTION_CLINIC_NAV, RECEPTION_NAV } from "@/components/reception/navigation";
import { SCRIBE_CLINIC_NAV, SCRIBE_NAV } from "@/components/scribe/navigation";

export type NavItem = { href: string; label: string; icon: IconComponent };
export type NavGroup = { title: string; items: NavItem[] };

/** The sidebar. Each module declares its own entries in components/<module>/navigation.ts. */
export const NAVIGATION: NavGroup[] = [
  { title: "Overview", items: [{ href: "/", label: "Dashboard", icon: Icons.Grid }] },
  { title: "AI Scribe", items: SCRIBE_NAV },
  { title: "AI Receptionist", items: RECEPTION_NAV },
  {
    title: "Clinic",
    items: [
      { href: "/schedule", label: "Scheduler", icon: Icons.Calendar },
      ...SCRIBE_CLINIC_NAV,
      ...RECEPTION_CLINIC_NAV,
      { href: "/account", label: "Account", icon: Icons.User },
    ],
  },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
