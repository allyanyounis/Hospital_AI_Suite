import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  {
    path: "/admin/departments",
    permission: "organization.manage",
    nav: { group: "Hospital", label: "Departments", icon: Icons.Building, order: 30 },
  },
];
