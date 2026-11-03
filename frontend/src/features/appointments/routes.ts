import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  {
    path: "/appointments",
    permission: "appointments.view",
    nav: { group: "Patients", label: "Appointments", icon: Icons.CalendarClock, order: 1 },
  },
  // Old address of the appointments board; the page redirects to /appointments
  { path: "/reception/appointments", permission: "appointments.view", title: "Appointments" },
];
