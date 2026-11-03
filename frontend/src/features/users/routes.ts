import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  { path: "/admin/users", permission: "users.manage", nav: { group: "Hospital", label: "Users", icon: Icons.Users, order: 40 } },
];
