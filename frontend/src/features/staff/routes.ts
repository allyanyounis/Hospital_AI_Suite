import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  { path: "/staff", permission: "staff.view", nav: { group: "Hospital", label: "Staff", icon: Icons.UserCog, order: 20 } },
];
