import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  { path: "/", permission: "dashboard.view", nav: { group: "Overview", label: "Dashboard", icon: Icons.Grid, order: 0 } },
];
