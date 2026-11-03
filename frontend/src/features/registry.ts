/**
 * The feature registry: every page the app serves, collected from each feature's routes.ts. The route -> permission
 * map (features/auth/access.ts) and the sidebar (features/shell/navigation.ts) are both derived from this list.
 *
 * Adding a feature: create src/features/<name>/ with a routes.ts, then add one line below. This is the only file
 * that imports another feature's internals, and only its routes.ts (plain data, no components), so it never
 * creates an import cycle.
 */

import type { RouteDef } from "@/features/auth";
import { routes as account } from "./account/routes";
import { routes as appointments } from "./appointments/routes";
import { routes as dashboard } from "./dashboard/routes";
import { routes as organization } from "./organization/routes";
import { routes as patients } from "./patients/routes";
import { routes as portal } from "./portal/routes";
import { routes as reception } from "./reception/routes";
import { routes as schedule } from "./schedule/routes";
import { routes as scribe } from "./scribe/routes";
import { routes as staff } from "./staff/routes";
import { routes as theatre } from "./theatre/routes";
import { routes as users } from "./users/routes";

export const FEATURES: Record<string, RouteDef[]> = {
  dashboard,
  patients,
  appointments,
  scribe,
  theatre,
  reception,
  schedule,
  staff,
  organization,
  users,
  portal,
  account,
};

export const ROUTES: RouteDef[] = Object.values(FEATURES).flat();
