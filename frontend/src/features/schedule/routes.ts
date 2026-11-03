import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  {
    path: "/schedule",
    permission: "schedule.view",
    nav: { group: "Hospital", label: "OPD Schedules", icon: Icons.Calendar, order: 10 },
  },
];
