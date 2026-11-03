import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  {
    path: "/theatre",
    permission: "theatre.view",
    nav: { group: "Theatres", label: "Theatre board", icon: Icons.Scissors, order: 0 },
  },
  {
    path: "/theatre/book",
    permission: "theatre.manage",
    nav: { group: "Theatres", label: "Book a case", icon: Icons.CalendarClock, order: 1 },
  },
  {
    path: "/theatre/surgeons",
    permission: "theatre.view",
    nav: { group: "Theatres", label: "Surgeons & rosters", icon: Icons.UserCog, order: 2 },
  },
  {
    path: "/theatre/insights",
    permission: "theatre.insights",
    nav: { group: "Theatres", label: "Model check", icon: Icons.Gauge, order: 3 },
  },
  { path: "/theatre/cases", permission: "theatre.view", title: "Theatre case" },
];
