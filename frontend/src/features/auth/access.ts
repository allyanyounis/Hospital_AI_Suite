/**
 * Who may open which page. The route -> permission map is derived from the feature registry (features/registry.ts),
 * where each feature declares its own routes; the signed-in layout enforces it and the sidebar uses it to hide links.
 * Permissions themselves come from the server (User.permissions).
 */

import { ROUTES } from "@/features/registry";
import type { Permission, RouteDef, User } from "./types";

function matches(pathname: string, prefix: string): boolean {
  return prefix === "/" ? pathname === "/" : pathname === prefix || pathname.startsWith(`${prefix}/`);
}

/** The route declaration for a path: the longest matching prefix, or undefined if no feature serves it. */
export function routeFor(pathname: string): RouteDef | undefined {
  return ROUTES.filter((r) => matches(pathname, r.path)).sort((a, b) => b.path.length - a.path.length)[0];
}

/** The permission a path needs: a Permission, null (any signed-in user), or undefined (not in the map). */
export function requiredPermission(pathname: string): Permission | null | undefined {
  return routeFor(pathname)?.permission;
}

export function hasPermission(user: User, permission: Permission | null | undefined): boolean {
  return permission == null || user.permissions.includes(permission);
}

export function canOpen(user: User, pathname: string): boolean {
  return hasPermission(user, requiredPermission(pathname));
}

/** Where a user lands after sign-in: the patient portal for patients, the overview for staff. */
export function homePath(user: User): string {
  return user.permissions.includes("portal.use") && !user.permissions.includes("dashboard.view") ? "/portal" : "/";
}
