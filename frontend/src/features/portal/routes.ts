import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  {
    path: "/portal",
    permission: "portal.use",
    nav: { group: "Me", label: "My appointments", icon: Icons.CalendarClock, order: 0 },
  },
];
