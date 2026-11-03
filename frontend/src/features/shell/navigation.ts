import { NAV_GROUPS, type NavGroupName, type User, hasPermission, routeFor } from "@/features/auth";
import { ROUTES } from "@/features/registry";
import type { IconComponent } from "@/shared/ui/icons";

/** A sidebar link, derived from a feature's route declaration (features/<name>/routes.ts). */
export type NavItem = { href: string; label: string; icon: IconComponent };
export type NavGroup = { title: NavGroupName; items: NavItem[] };

/** The navigation this user may use: every registered route with a nav entry they may open, grouped and ordered. */
export function navigationFor(user: User): NavGroup[] {
  return NAV_GROUPS.map((title) => ({
    title,
    items: ROUTES.filter((r) => r.nav?.group === title && hasPermission(user, r.permission))
      .sort((a, b) => a.nav!.order - b.nav!.order)
      .map((r) => ({ href: r.path, label: r.nav!.label, icon: r.nav!.icon })),
  })).filter((g) => g.items.length > 0);
}

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function pageTitle(pathname: string): string {
  const route = routeFor(pathname);
  return route?.nav?.label ?? route?.title ?? "Dashboard";
}
