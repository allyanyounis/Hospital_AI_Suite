import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  { path: "/account", permission: null, nav: { group: "Me", label: "Account", icon: Icons.User, order: 10 } },
];
