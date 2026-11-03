/**
 * Auth feature: sign-in, the signed-in session (SessionProvider / useSession), access control (route map
 * derived from features/registry.ts, RouteGuard, can()) and the login page.
 * Public API of the module: import from "@/features/auth", never from its internal files.
 */

import { authApi } from "./api";

export { LoginView } from "./views/LoginView";
export { SessionProvider, useSession } from "./components/SessionProvider";
export { RouteGuard } from "./components/RouteGuard";
export { canOpen, hasPermission, homePath, requiredPermission, routeFor } from "./access";
export { NAV_GROUPS, ROLE_LABELS, STAFF_ROLES } from "./types";
export type * from "./types";

/** Change the signed-in user's password (the server re-issues the session cookie). */
export const changePassword = authApi.changePassword;
